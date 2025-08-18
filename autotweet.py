import os
import tweepy
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
# MODIFICATION : On cherche dans le dossier source, pas le dossier de build
ARTICLES_DIR = "article" 

def get_latest_article():
    """Trouve le dernier article modifié dans le dossier."""
    articles = list(Path(ARTICLES_DIR).glob("*.html"))
    if not articles:
        return None
    latest_article = max(articles, key=lambda p: p.stat().st_mtime)
    return latest_article

def get_article_info(path):
    """Extrait le titre et la catégorie d'un fichier article."""
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = soup.find('title').text.split('|')[0].strip()
        category_tag = soup.find('meta', attrs={'name': 'category'})
        category = category_tag['content'] if category_tag else 'Actualité'
        return title, category

def generate_tweet(title, url, category):
    """Génère un tweet intelligent avec Gemini."""
    print(f"Génération du tweet pour : {title}")
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
    """Poste le texte sur X (Twitter)."""
    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        client.create_tweet(text=text)
        print(f"Tweet publié avec succès :\n{text}")
    except Exception as e:
        print(f"ERREUR lors de la publication du tweet : {e}")
        # On lève l'erreur pour que le workflow GitHub soit marqué comme échoué
        raise e

def main():
    """Fonction principale du script."""
    print("Début du script d'auto-tweet...")
    
    latest_article_path = get_latest_article()
    if not latest_article_path:
        print("Aucun article trouvé dans le dossier source. Arrêt.")
        return
        
    title, category = get_article_info(latest_article_path)
    article_url = f"{SITE_URL}/{latest_article_path}" # Le chemin est déjà correct
    
    tweet_text = generate_tweet(title, article_url, category)
    post_tweet(tweet_text)
    
    print("Script d'auto-tweet terminé.")

if __name__ == "__main__":
    main()
