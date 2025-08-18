import os
import tweepy
import requests
import hashlib
import json
import google.generativeai as genai
from pathlib import Path
from bs4 import BeautifulSoup

# --- Configuration ---
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY_HORIZON")
SITE_URL = "https://horizon-libre.net"
ARTICLES_DIR = "article"
BLOBS_PROXY_URL = os.environ.get("BLOBS_PROXY_URL")
AURORE_BLOBS_TOKEN = os.environ.get("AURORE_BLOBS_TOKEN")

# --- Fonctions de Mémoire ---
def _auth_headers():
    return {"X-AURORE-TOKEN": AURORE_BLOBS_TOKEN}

def topic_key(text: str) -> str:
    """Crée une clé unique et stable pour un article."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

def seen(key: str) -> bool:
    """Vérifie si une clé a déjà été marquée comme tweetée."""
    if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN:
        print("ATTENTION: Variables de mémoire non configurées. Déduplication désactivée.")
        return False
    try:
        # On ajoute un préfixe pour ne pas mélanger avec les clés de génération d'articles
        full_key = f"tweeted_{key}"
        r = requests.get(f"{BLOBS_PROXY_URL}?key={full_key}", headers=_auth_headers(), timeout=15)
        if r.status_code == 404:
            return False
        r.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"ATTENTION: Impossible de contacter la mémoire: {e}. On continue par sécurité.")
        return False

def mark(key: str):
    """Marque une clé comme tweetée dans la mémoire."""
    if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN:
        return
    full_key = f"tweeted_{key}"
    print(f"Marquage de la clé '{full_key}' comme tweetée.")
    requests.post(
        BLOBS_PROXY_URL, 
        headers=_auth_headers(), 
        json={"key": full_key, "meta": {"tweeted_at": datetime.now().isoformat()}}, 
        timeout=20
    ).raise_for_status()

# --- Fonctions de Contenu ---
def get_added_articles():
    """Utilise Git pour trouver les fichiers articles ajoutés dans le dernier commit."""
    try:
        # Cette commande Git liste les fichiers du dernier commit sur la branche actuelle
        files_changed = os.popen('git diff --name-only HEAD~1 HEAD').read().splitlines()
        added_articles = [
            Path(f) for f in files_changed 
            if f.startswith(ARTICLES_DIR + '/') and f.endswith(".html")
        ]
        print(f"Fichiers articles trouvés dans le dernier commit : {added_articles}")
        return added_articles
    except Exception as e:
        print(f"ERREUR: Impossible de lire l'historique Git. {e}")
        return []

def get_article_info(path):
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = soup.find('title').text.split('|')[0].strip()
        category_tag = soup.find('meta', attrs={'name': 'category'})
        category = category_tag['content'] if category_tag else 'Actualité'
        return title, category

# --- Fonctions Twitter ---
def generate_tweet(title, url, category):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""
    Agis comme un community manager expert pour le média "L'Horizon Libre".
    Rédige un tweet percutant et professionnel pour l'article suivant.

    Le tweet doit :
    1. Avoir une accroche intrigante (1-2 phrases).
    2. Inclure 3 à 5 hashtags pertinents et populaires en français.
    3. Conclure avec le lien vers l'article.
    4. Ne pas dépasser 280 caractères.

    Titre de l'article : "{title}"
    Catégorie : "{category}"
    Lien : {url}

    Rédige uniquement le texte du tweet, sans introduction ni conclusion.
    """
    response = model.generate_content(prompt)
    return response.text.strip()

def post_tweet(text):
    client = tweepy.Client(
        consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_TOKEN_SECRET
    )
    client.create_tweet(text=text)
    print(f"Tweet publié avec succès :\n{text}")

# --- Fonction Principale ---
def main():
    from datetime import datetime
    print("Début du script d'auto-tweet...")
    
    new_articles = get_added_articles()
    
    if not new_articles:
        print("Aucun nouvel article ajouté dans ce commit. Arrêt.")
        return
        
    for article_path in new_articles:
        try:
            title, category = get_article_info(article_path)
            
            key = topic_key(str(article_path))
            
            if seen(key):
                print(f"Article '{title}' a déjà été tweeté. On ignore.")
                continue
            
            article_url = f"{SITE_URL}/{article_path}"
            tweet_text = generate_tweet(title
