import os import sys import json import time import hashlib import subprocess import tempfile from pathlib import Path from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import requests import tweepy from bs4 import BeautifulSoup from PIL import Image

Tente d'importer Gemini (optionnel)
try: import google.generativeai as genai except Exception: genai = None

--- Configuration ---
SITE_URL = "https://horizon-libre.net" ARTICLES_DIR = "article"

--- Secrets & Clés API ---
X_API_KEY = os.environ.get("X_API_KEY") X_API_SECRET = os.environ.get("X_API_SECRET") X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN") X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET") GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_HORIZON") GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash") BLOBS_PROXY_URL = os.environ.get("BLOBS_PROXY_URL") AURORE_BLOBS_TOKEN = os.environ.get("AURORE_BLOBS_TOKEN")

def log(msg: str): print(msg, flush=True)

---------- Mémoire anti-doublon ----------
def _auth_headers(): return {"X-AURORE-TOKEN": AURORE_BLOBS_TOKEN} if AURORE_BLOBS_TOKEN else {}

def stable_key_for_path(path_rel: str) -> str: return hashlib.sha256(path_rel.strip().lower().encode("utf-8")).hexdigest()

def seen(key: str) -> bool: if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN: return False try: url = f"{BLOBS_PROXY_URL.rstrip('/')}/{key}" r = requests.get(url, headers=_auth_headers(), timeout=5) if r.status_code == 200: return True if r.status_code == 404: return False log(f"[memoire] GET {url} -> {r.status_code}, on continue.") return False except Exception as e: log(f"[memoire] GET échec: {e}. Continue sans mémoire.") return False

def mark(key: str): if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN: return try: url = f"{BLOBS_PROXY_URL.rstrip('/')}/{key}" r = requests.put(url, headers=_auth_headers(), data=b"1", timeout=5) if r.status_code in (200, 201, 204): return r = requests.post(url, headers=_auth_headers(), data=b"1", timeout=5) if r.status_code not in (200, 201, 204): log(f"[memoire] Ecriture {url} -> {r.status_code} body: {r.text[:200]}") except Exception as e: log(f"[memoire] Ecriture échec: {e}")

---------- Lecture de l'événement ----------
def get_event(): p = os.environ.get("GITHUB_EVENT_PATH") if not p or not os.path.isfile(p): return {} try: with open(p, "r", encoding="utf-8") as f: return json.load(f) except Exception as e: log(f"Impossible de lire GITHUB_EVENT_PATH: {e}") return {}

def git_added_paths(before: str, after: str): try: out = subprocess.check_output( ["git", "diff", "--diff-filter=A", "--name-only", before, after, "--", f"{ARTICLES_DIR}/*.html"], text=True ).strip() return [ln for ln in out.splitlines() if ln.strip()] except Exception as e: log(f"git diff exception: {e}") return []

def commits_added_paths(event: dict): added = set() try: for c in event.get("commits") or []: for p in c.get("added") or []: if p.startswith(f"{ARTICLES_DIR}/") and p.endswith(".html"): added.add(p) except Exception as e: log(f"Lecture commits.added échouée: {e}") return sorted(added)

def find_new_articles(): """ Détecte les nouveaux articles depuis repository_dispatch (client_payload.articles) ou, en fallback, depuis un push (git diff / commits.added). """ event = get_event() event_name = os.environ.get("GITHUB_EVENT_NAME", "")

if event_name == "repository_dispatch":
    if event.get("action") == "new-article-published":
        paths = event.get("client_payload", {}).get("articles", [])
        paths = [p for p in paths if p.startswith(f"{ARTICLES_DIR}/") and p.endswith(".html")]
        if paths:
            log(f"Articles détectés via repository_dispatch: {paths}")
            return paths

if event_name == "push":
    before, after = event.get("before"), event.get("after")
    paths = git_added_paths(before, after) if before and after else []
    if not paths:
        log("Fallback: analyse des fichiers 'added' dans les commits.")
        paths = commits_added_paths(event)
    paths = [p for p in paths if p.startswith(f"{ARTICLES_DIR}/") and p.endswith(".html")]
    if paths:
        log(f"Articles détectés via push: {paths}")
    return paths

return []
---------- Parsing article ----------
def parse_article_info(path_rel: str): p = Path(path_rel) title, category = None, None try: with open(p, "r", encoding="utf-8") as f: soup = BeautifulSoup(f.read(), "html.parser") if soup.title and soup.title.string: title = soup.title.string.strip().split("|")[0].strip() if not title: h1 = soup.find("h1") if h1 and h1.get_text(strip=True): title = h1.get_text(strip=True) meta_cat = soup.find("meta", attrs={"property": "article:section"}) or soup.find("meta", attrs={"name": "category"}) if meta_cat and meta_cat.get("content"): category = meta_cat["content"].strip() except Exception as e: log(f"Parse erreur sur {path_rel}: {e}") if not title: title = p.stem.replace("-", " ").strip().capitalize() return title, category

---------- Hashtags, URL, génération ----------
STOPWORDS_FR = { "le","la","les","un","une","des","de","du","d","et","en","à","au","aux","pour","par", "sur","avec","sans","dans","ce","cet","cette","ces","ou","mais","plus","moins" }

def build_hashtags(title: str, category: str | None) -> list[str]: tags = set() if category: c = category.strip().lower().replace(" ", "") if c: tags.add("#" + c.capitalize()) words = [w.strip(".,:;!?()[]«»"'").lower() for w in (title or "").split()] for w in words: if len(w) >= 4 and w.isalpha() and w not in STOPWORDS_FR: tags.add("#" + w.capitalize()) if len(tags) >= 5: break tags = ["#HorizonLibre"] + sorted(tags - {"#HorizonLibre"}) return tags[:2]

def append_utm(url: str) -> str: if not os.environ.get("ENABLE_UTM"): return url try: u = urlparse(url) q = dict(parse_qsl(u.query)) q.update({"utm_source": "twitter", "utm_medium": "social", "utm_campaign": "autotweet"}) new_u = u._replace(query=urlencode(q)) return urlunparse(new_u) except Exception: return url

def safe_trim_tweet(text: str, limit: int = 280) -> str: if len(text) <= limit: return text return (text[: limit - 1] + "…").rstrip()

def generate_tweet(title: str, url: str, category: str | None) -> str: url = append_utm(url) tags = build_hashtags(title, category) brand = "#HorizonLibre" hashtags = [brand] + ([t for t in tags if t != brand][:1])

if GEMINI_API_KEY and genai is not None:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            "Rédige un tweet concis en français (<= 260 caractères), informatif et neutre, "
            "qui donne envie de lire sans clickbait. Termine par l’URL exacte fournie. "
            "Inclure exactement ces hashtags à la fin du tweet: "
            f"{' '.join(hashtags)}. Pas d'emojis.\n\n"
            f"Titre: {title}\nCatégorie: {category or ''}\n"
        )
        resp = model.generate_content(prompt)
        text = (getattr(resp, "text", None) or "").strip()
        if not text:
            raise ValueError("Réponse vide")
        if url not in text:
            text = f"{text} {url}"
        return safe_trim_tweet(text)
    except Exception as e:
        log(f"Gemini erreur, fallback: {e}")

base = f"{title}"
text = f"{base} {url} {' '.join(hashtags)}"
return safe_trim_tweet(text)
---------- Image ----------
def resolve_local_path(article_rel: str, src: str) -> str | None: if src.startswith("http://") or src.startswith("https://"): return None root_rel = src.lstrip("/") candidates = [ Path(root_rel), Path(article_rel).parent / src, Path("public") / root_rel, Path("static") / root_rel, Path("assets") / root_rel, ] for cand in candidates: if cand.is_file(): return cand.as_posix() return None

def first_img_src_and_alt(soup: BeautifulSoup): og = soup.find("meta", attrs={"property": "og:image"}) if og and og.get("content"): return og["content"].strip(), None tw = soup.find("meta", attrs={"name": "twitter:image"}) if tw and tw.get("content"): return tw["content"].strip(), None link = soup.find("link", attrs={"rel": "image_src"}) if link and link.get("href"): return link["href"].strip(), None article = soup.find("article") or soup img = article.find("img") if img and img.get("src"): alt = img.get("alt") or None fig = img.find_parent("figure") if fig: cap = fig.find("figcaption") if cap and cap.get_text(strip=True): alt = alt or cap.get_text(strip=True) return img["src"].strip(), alt return None, None

def download_if_remote(url: str) -> str | None: try: r = requests.get(url, timeout=15) r.raise_for_status() suffix = os.path.splitext(urlparse(url).path)[1] or ".jpg" tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix) tmp.write(r.content) tmp.flush(); tmp.close() return tmp.name except Exception as e: log(f"Téléchargement image échoué: {e}") return None

def prepare_image_for_twitter(path: str) -> str | None: try: im = Image.open(path) if im.mode not in ("RGB", "L"): im = im.convert("RGB") max_side = 4096 if max(im.size) > max_side: im.thumbnail((max_side, max_side), Image.LANCZOS) out = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") out.close() quality = 90 for _ in range(5): im.save(out.name, format="JPEG", quality=quality, optimize=True, progressive=True) if os.path.getsize(out.name) <= 4_800_000 or quality <= 70: break quality -= 5 return out.name except Exception as e: log(f"Préparation image échouée: {e}") return None

def find_article_image(article_rel: str) -> tuple[str | None, str | None]: try: with open(article_rel, "r", encoding="utf-8") as f: soup = BeautifulSoup(f.read(), "html.parser") src, alt = first_img_src_and_alt(soup) if not src: return None, None local = resolve_local_path(article_rel, src) if local: prepared = prepare_image_for_twitter(local) return prepared, alt url_abs = src if src.startswith("http") else urljoin(SITE_URL + "/", src.lstrip("/")) downloaded = download_if_remote(url_abs) if not downloaded: return None, None prepared = prepare_image_for_twitter(downloaded) return prepared, alt except Exception as e: log(f"find_article_image erreur: {e}") return None, None

---------- Twitter (X) ----------
def twitter_client(): missing = [k for k, v in { "X_API_KEY": X_API_KEY, "X_API_SECRET": X_API_SECRET, "X_ACCESS_TOKEN": X_ACCESS_TOKEN, "X_ACCESS_TOKEN_SECRET": X_ACCESS_TOKEN_SECRET, }.items() if not v] if missing: raise RuntimeError(f"Clés Twitter manquantes: {', '.join(missing)}") auth = tweepy.OAuth1UserHandler( X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET ) api = tweepy.API(auth) try: api.verify_credentials() except Exception as e: log(f"Avertissement: verify_credentials a échoué: {e}") return api

def post_tweet(api, text: str, media_path: str | None = None, alt_text: str | None = None): if media_path: media = api.media_upload(filename=media_path) try: if alt_text: api.create_media_metadata(media.media_id, alt_text=alt_text[:1000]) except Exception as e: log(f"Alt text non défini: {e}") return api.update_status(status=text, media_ids=[media.media_id]) else: return api.update_status(status=text)

---------- Main ----------
def main(): log("Début du script d'auto-tweet…") added_paths = find_new_articles() if not added_paths: log("Aucun nouvel article détecté. Fin.") return

try:
    api = twitter_client()
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

    img_path, img_alt = find_article_image(rel_posix)
    tweet_text = generate_tweet(title, url, category)
    try:
        resp = post_tweet(api, tweet_text, media_path=img_path, alt_text=(img_alt or title))
        nb_success += 1
        log(f"Tweet publié pour {rel_posix}: id={getattr(resp, 'id', None)}")
        mark(key)
        time.sleep(2)
    except Exception as e:
        log(f"Erreur de publication pour {rel_posix}: {e}")

log(f"Terminé. Tweets publiés: {nb_success}/{len(added_paths)}")
if name == "main": main()
