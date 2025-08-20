import os
import sys
import json
import time
import hashlib
import subprocess
from pathlib import Path

import requests
import tweepy
from bs4 import BeautifulSoup

# Tente d'importer la librairie Gemini, mais ne bloque pas si elle n'est pas là
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# --- Configuration ---
SITE_URL = "https://horizon-libre.net"
ARTICLES_DIR = "article"

# --- Secrets & Clés API (lus depuis les variables d'environnement) ---
# Twitter API (X)
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")

# Gemini (optionnel)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_HORIZON")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

# Mémoire (optionnelle) via un proxy pour Netlify Blobs
BLOBS_PROXY_URL = os.environ.get("BLOBS_PROXY_URL")
AURORE_BLOBS_TOKEN = os.environ.get("AURORE_BLOBS_TOKEN")

def log(msg: str):
    """Affiche un message de log dans la console du workflow."""
    print(msg, flush=True)

# --- Mémoire (optionnelle) pour éviter les doublons ---
def _auth_headers():
    """Prépare les en-têtes d'authentification pour le service de mémoire."""
    return {"X-AURORE-TOKEN": AURORE_BLOBS_TOKEN} if AURORE_BLOBS_TOKEN else {}

def stable_key_for_path(path_rel: str) -> str:
    """Génère une clé unique et stable pour un chemin de fichier."""
    return hashlib.sha256(path_rel.strip().lower().encode("utf-8")).hexdigest()

def seen(key: str) -> bool:
    """Vérifie si une clé a déjà été enregistrée dans la mémoire."""
    if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN:
        return False
    try:
        url = f"{BLOBS_PROXY_URL.rstrip('/')}/{key}"
        r = requests.get(url, headers=_auth_headers(), timeout=5)
        if r.status_code == 200:
            return True
        if r.status_code == 404:
            return False
        log(f"[memoire] GET {url} -> {r.status_code}, on continue sans bloquer.")
        return False
    except Exception as e:
        log(f"[memoire] GET échec: {e}. On continue sans mémoire.")
        return False

def mark(key: str):
    """Marque une clé comme vue dans la mémoire."""
    if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN:
        return
    try:
        url = f"{BLOBS_PROXY_URL.rstrip('/')}/{key}"
        # Tente un PUT, puis un POST en fallback
        r = requests.put(url, headers=_auth_headers(), data=b"1", timeout=5)
        if r.status_code in (200, 201, 204):
            return
        r = requests.post(url, headers=_auth_headers(), data=b"1", timeout=5)
        if r.status_code not in (200, 201, 204):
            log(f"[memoire] Ecriture {url} -> {r.status_code} body: {r.text[:200]}")
    except Exception as e:
        log(f"[memoire] Ecriture échec: {e}")

# --- Sélection des articles ajoutés ---
def get_push_event():
    """Charge les données de l'événement GitHub (push) depuis le fichier JSON."""
    path = os.environ.get("GITHUB_EVENT_PATH")
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"Impossible de lire GITHUB_EVENT_PATH: {e}")
        return None

def git_added_paths(before: str, after: str):
    """Utilise 'git diff' pour trouver les fichiers HTML ajoutés dans le dossier 'article'."""
    try:
        cmd = [
            "git", "diff", "--diff-filter=A", "--name-only",
            before, after, "--", f"{ARTICLES_DIR}/*.html",
        ]
        out = subprocess.check_output(cmd, text=True, encoding="utf-8").strip()
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except subprocess.CalledProcessError as e:
        log(f"git diff erreur: {e}")
        return []
    except Exception as e:
        log(f"git diff exception: {e}")
        return []

def commits_added_paths(event: dict):
    """Méthode de fallback : parcourt les commits du push pour trouver les fichiers ajoutés."""
    added = set()
    try:
        for c in event.get("commits") or []:
            for p in c.get("added") or []:
                if p.startswith(f"{ARTICLES_DIR}/") and p.endswith(".html"):
                    added.add(p)
    except Exception as e:
        log(f"Lecture commits.added échouée: {e}")
    return sorted(list(added))

def find_new_articles():
    """Orchestre la détection des nouveaux articles."""
    event = get_push_event()
    if not event:
        log("Aucune donnée d'événement GitHub trouvée.")
        return []

    before = event.get("before")
    after = event.get("after")

    paths = []
    # Stratégie 1 (la plus fiable) : git diff entre les commits
    if before and after and before != "0000000000000000000000000000000000000000":
        log(f"Analyse des ajouts via git diff {before[:7]}..{after[:7]}")
        paths = git_added_paths(before, after)

    # Stratégie 2 (fallback) : analyse des commits dans le payload
    if not paths:
        log("Fallback: analyse des fichiers 'added' dans les commits.")
        paths = commits_added_paths(event)

    # Nettoyage et déduplication
    norm = [p for p in paths if p.startswith(f"{ARTICLES_DIR}/") and p.endswith(".html")]
    seen_set = set()
    ordered = []
    for p in norm:
        if p not in seen_set:
            seen_set.add(p)
            ordered.append(p)
    return ordered

# --- Parsing de l'article ---
def parse_article_info(path_rel: str):
    """Extrait le titre et la catégorie d'un fichier HTML."""
    p = Path(path_rel)
    title = None
    category = None
    try:
        with open(p, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        # Tente de trouver le titre dans la balise <title>
        if soup.title and soup.title.string:
            title_raw = soup.title.string.strip()
            title = title_raw.split("|")[0].strip()

        # Sinon, tente avec la balise <h1>
        if not title:
            h1 = soup.find("h1")
            if h1 and h1.get_text(strip=True):
                title = h1.get_text(strip=True)

        # Tente de trouver la catégorie dans les balises <meta>
        meta_cat = soup.find("meta", attrs={"property": "article:section"})
        if meta_cat and meta_cat.get("content"):
            category = meta_cat["content"].strip()
        else:
            meta_cat = soup.find("meta", attrs={"name": "category"})
            if meta_cat and meta_cat.get("content"):
                category = meta_cat["content"].strip()
    except Exception as e:
        log(f"Parse erreur sur {path_rel}: {e}")

    # Fallback pour le titre si tout a échoué
    if not title:
        title = p.stem.replace("-", " ").strip().capitalize()

    return title, category

# --- Génération du contenu du tweet ---
def safe_trim_tweet(text: str, limit: int = 280) -> str:
    """S'assure que le texte ne dépasse pas la limite de caractères de Twitter."""
    if len(text) <= limit:
        return text
    return (text[: limit - 1] + "…").rstrip()

def generate_tweet(title: str, url: str, category: str | None) -> str:
    """Génère le texte du tweet, en utilisant Gemini si disponible."""
    # Fallback si Gemini n'est pas configuré
    if not GEMINI_API_KEY or genai is None:
        return safe_trim_tweet(f"{title}\n\n{url} #HorizonLibre")

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            "Rédige un tweet concis en français (<= 260 caractères), informatif et neutre, "
            "sur l'article suivant. Inclure l'URL telle quelle à la fin. "
            "Pas d'emojis, pas de clickbait, 1 hashtag pertinent max.\n\n"
            f"Titre: {title}\nCatégorie: {category or ''}\nURL: {url}\n"
        )
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        if not text:
            raise ValueError("Réponse Gemini vide")
        if url not in text:
            text = f"{text} {url}"
        return safe_trim_tweet(text)
    except Exception as e:
        log(f"Gemini erreur, fallback: {e}")
        return safe_trim_tweet(f"{title}\n\n{url} #HorizonLibre")

# --- Publication sur Twitter (X) ---
def twitter_client():
    """Initialise et retourne un client API pour Twitter."""
    missing = [k for k, v in {
        "X_API_KEY": X_API_KEY, "X_API_SECRET": X_API_SECRET,
        "X_ACCESS_TOKEN": X_ACCESS_TOKEN, "X_ACCESS_TOKEN_SECRET": X_ACCESS_TOKEN_SECRET,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Clés Twitter manquantes: {', '.join(missing)}")

    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET
    )
    return client

def post_tweet(client, text: str):
    """Poste le tweet en utilisant le client v2."""
    return client.create_tweet(text=text)

# --- Fonction principale ---
def main():
    log("Début du script d'auto-tweet…")
    added_paths = find_new_articles()
    if not added_paths:
        log("Aucun nouvel article ajouté dans ce push. Fin.")
        return

    log(f"Articles ajoutés détectés: {added_paths}")

    try:
        client = twitter_client()
    except Exception as e:
        log(f"Erreur d'initialisation Twitter: {e}")
        sys.exit(1)

    nb_success = 0
    for rel_path in added_paths:
        rel_posix = Path(rel_path).as_posix()
        url = f"{SITE_URL}/{rel_posix.lstrip('/')}"
        title, category = parse_article_info(rel_posix)

        key = stable_key_for_path(rel_posix)
        if seen(key):
            log(f"Déjà tweeté (mémoire): {rel_posix} — on passe.")
            continue

        tweet_text = generate_tweet(title, url, category)
        try:
            resp = post_tweet(client, tweet_text)
            nb_success += 1
            tweet_id = resp.data.get('id') if resp.data else 'N/A'
            log(f"Tweet publié pour {rel_posix}: id={tweet_id}")
            mark(key)
            time.sleep(2)  # Petite pause pour ne pas surcharger l'API
        except Exception as e:
            log(f"Erreur de publication pour {rel_posix}: {e}")

    log(f"Terminé. Tweets publiés: {nb_success}/{len(added_paths)}")

if __name__ == "__main__":
    main()
