import os
import tweepy
import requests
import hashlib
import google.generativeai as genai
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime

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
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

def seen(key: str) -> bool:
    if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN: return False
    try:
        full_key = f"tweeted_{key}"
        r = requests.get(f"{BLOBS_PROXY_URL}?key={full_key}", headers=_auth_headers(), timeout=15)
        if r.status_code == 404: return False
        r.raise_for_status()
        return True
    except requests.RequestException: return False

def mark(key: str):
    if not BLOBS_PROXY_URL or not AURORE_BLOBS_TOKEN: return
    full_key = f"tweeted_{key}"
    requests.post(
        BLOBS_PROXY_URL, 
        headers=_auth_headers(), 
        json={"key": full_key, "meta": {"tweeted_at": datetime.now().isoformat()}}, 
        timeout=20
    ).raise_for_status()

# --- Fonctions de Contenu et Tweet ---
def get_latest_article():
    articles = list(Path(ARTICLES_DIR).glob("*.html"))
    if not articles: return None
    return max(articles, key=lambda p: p.stat().st_mtime)

def get_article_info(path):
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = soup.find('title').text.split('|')[0].strip()
        category_tag = soup.find('meta', attrs={'name': 'category'})
        category = category_tag['content'] if category_tag else 'Actualité'
        return title, category

def generate_tweet(title, url, category):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""Rédige un tweet percutant pour l'article suivant : Titre: "{title}", Catégorie: "{category}", Lien: {url}. Inclus 3-5 hashtags pertinents. Ne dépasse pas 280 caractères."""
    response = model.generate_content(prompt)
    return response.text.strip()

def post_tweet(text):
    client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_TOKEN_SECRET)
    client.create_tweet(text=text)
    print(f"Tweet publié avec succès :\n{text}")

# --- Fonction Principale ---
def main():
    print("Début du script d'auto-tweet...")
    latest_article_path = get_latest_article()
    if not latest_article_path:
        print("Aucun article trouvé. Arrêt.")
        return
        
    title, category = get_article_info(latest_article_path)
    key = topic_key(title)
    
    if seen(key):
        print(f"Article '{title}' a déjà été tweeté. Arrêt.")
        return
    
    article_url = f"{SITE_URL}/{latest_article_path}"
    tweet_text = generate_tweet(title, article_url, category)
    
    try:
        post_tweet(tweet_text)
        mark(key)
        print(f"Article '{title}' marqué comme tweeté.")
    except Exception as e:
        print(f"Échec du tweet pour l'article '{title}'. Il ne sera pas marqué. Erreur: {e}")

    print("Script d'auto-tweet terminé.")

if __name__ == "__main__":
    main()
