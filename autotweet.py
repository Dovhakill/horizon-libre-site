import os
import tweepy
import requests
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
TEMP_IMAGE_PATH = "temp_article_image.jpg"

def get_latest_article():
    """Trouve le dernier article modifié dans le dossier."""
    articles = list(Path(ARTICLES_DIR).glob("*.html"))
    if not articles:
        return None
    return max(articles, key=lambda p: p.stat().st_mtime)

def get_article_info(path):
    """Extrait le titre, la catégorie et l'URL de l'image d'un fichier article."""
    with open(path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = soup.find('title').text.split('|')[0].strip()
        category_tag = soup.find('meta', attrs={'name': 'category'})
        category = category_tag['content'] if category_tag else 'Actualité'
        image_tag = soup.select_one('article figure img')
        image_url = image_tag['src'] if image_tag else None
        return title, category, image_url

def generate_tweet(title, url, category):
    """Génère un tweet intelligent avec Gemini."""
    print(f"Génération du tweet pour : {title}")
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""Rédige un tweet percutant pour l'article suivant. Le tweet doit avoir une accroche (1-2 phrases), 3-5 hashtags pertinents, et le lien. Ne pas dépasser 280 caractères. Titre: "{title}", Catégorie: "{category}", Lien: {url}"""
    response = model.generate_content(prompt)
    return response.text.strip()

def post_tweet(text, image_path=None):
    """Poste le texte et optionnellement une image sur X (Twitter)."""
    try:
        # Authentification pour l'API v1.1 (pour l'upload de média)
        auth = tweepy.OAuth1UserHandler(X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET)
        api_v1 = tweepy.API(auth)
        
        # Authentification pour l'API v2 (pour poster le tweet)
        client_v2 = tweepy.Client(
            consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        
        media_ids = []
        if image_path:
            print(f"Téléversement de l'image {image_path} sur Twitter...")
            media = api_v1.media_upload(filename=image_path)
            media_ids.append(media.media_id)
            print("Image téléversée avec succès.")

        client_v2.create_tweet(text=text, media_ids=media_ids if media_ids else None)
        print(f"Tweet publié avec succès :\n{text}")

    except Exception as e:
        print(f"ERREUR lors de la publication du tweet : {e}")
        raise e

def main():
    """Fonction principale du script."""
    print("Début du script d'auto-tweet...")
    
    latest_article_path = get_latest_article()
    if not latest_article_path:
        print("Aucun article trouvé. Arrêt.")
        return
        
    title, category, image_url = get_article_info(latest_article_path)
    article_url = f"{SITE_URL}/{latest_article_path}"
    
    tweet_text = generate_tweet(title, article_url, category)
    
    image_to_post = None
    if image_url and 'placehold.co' not in image_url:
        try:
            print(f"Téléchargement de l'image depuis : {image_url}")
            response = requests.get(image_url, stream=True)
            response.raise_for_status()
            with open(TEMP_IMAGE_PATH, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print("Image téléchargée.")
            image_to_post = TEMP_IMAGE_PATH
        except Exception as e:
            print(f"ATTENTION : Impossible de télécharger l'image : {e}")
            
    post_tweet(tweet_text, image_path=image_to_post)
    
    if os.path.exists(TEMP_IMAGE_PATH):
        os.remove(TEMP_IMAGE_PATH)
        print("Image temporaire supprimée.")
    
    print("Script d'auto-tweet terminé.")

if __name__ == "__main__":
    main()
