import os
import tweepy
import requests
import hashlib
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
# Accès à la mémoire
BLOBS_PROXY_URL = os.environ.get("BLOBS_PROXY_URL")
AURORE_BLOBS_TOKEN = os.environ.get("AURORE_BLOBS_TOKEN")


# --- FONCTIONS DE MÉMOIRE (copiées depuis Aurore) ---
def _auth_headers():
    return {"X-AURORE-TOKEN": AURORE_BLOBS_TOKEN}

def topic_key(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

def seen(key: str) -> bool:
    try:
        r = requests.get(f"{BLOBS_PROXY_URL}?key={key}", headers=_auth_headers(), timeout=15)
        if r.status_code == 404: return False
        r.raise_for_status()
        return True
    except requests.RequestException:
        return False

def mark(key: str):
    requests.post(BLOBS_PROXY_URL, headers=_auth_headers(), json={"key": key, "meta": {"tweeted": True}}, timeout=20).raise_for_status()


# --- Fonctions de Tweet (inchangées) ---
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
    prompt = f"""Rédige un tweet percutant pour l'article suivant : Titre: "{title}", Catégorie: "{category}", Lien: {url}. Le tweet doit avoir une accroche, 3-5 hashtags pertinents, et le lien. Ne dépasse pas 280 caractères."""
    response = model.generate_content(prompt)
    return response.text.strip()

def post_tweet(text):
    client = tweepy.Client(consumer_key=X_API_KEY, consumer_secret=X_API_SECRET, access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_TOKEN_SECRET)
    client.create_tweet(text=text)
    print(f"Tweet publié avec succès :\n{text}")

def main():
    print("Début du script d'auto-tweet...")
    latest_article_path = get_latest_article()
    if not latest_article_path:
        print("Aucun article trouvé. Arrêt.")
        return
        
    title, category = get_article_info(latest_article_path)
    
    # --- LOGIQUE DE MÉMOIRE AJOUTÉE ---
    key = topic_key(title) # On crée une clé unique pour le titre
    if seen(key):
        print(f"Article '{title}' a déjà été tweeté. Arrêt.")
        return
    # --- FIN DE LA LOGIQUE DE MÉMOIRE ---
    
    article_url = f"{SITE_URL}/{latest_article_path}"
    tweet_text = generate_tweet(title, article_url, category)
    post_tweet(tweet_text)
    
    # On marque l'article comme tweeté
    mark(key)
    print(f"Article '{title}' marqué comme tweeté.")
    
    print("Script d'auto-tweet terminé.")

if __name__ == "__main__":
    main()
