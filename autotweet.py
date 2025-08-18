import os
import tweepy
import frontmatter
import google.generativeai as genai
from pathlib import Path

# --- Configuration ---
# On récupère les clés depuis les secrets GitHub
X_API_KEY = os.environ.get("X_API_KEY")
X_API_SECRET = os.environ.get("X_API_SECRET")
X_ACCESS_TOKEN = os.environ.get("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.environ.get("X_ACCESS_TOKEN_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") # On a aussi besoin de Gemini
SITE_URL = "https://horizon-libre.net"
ARTICLES_DIR = "article"

def get_latest_article():
    """Trouve le dernier article modifié dans le dossier."""
    articles = Path(ARTICLES_DIR).glob("*.html")
    latest_article = max(articles, key=lambda p: p.stat().st_mtime)
    return latest_article

def generate_tweet(title, url, category):
    """Génère un tweet intelligent avec Gemini."""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""
    Agis comme un community manager expert pour le média "L'Horizon Libre".
    Rédige un tweet percutant et professionnel pour l'article suivant.

    Le tweet doit :
    1.  Avoir une accroche intrigante (2 phrases maximum).
    2.  Inclure entre 3 et 5 hashtags pertinents et populaires.
    3.  Terminer par le lien vers l'article.
    4.  Ne pas dépasser 280 caractères au total.

    Titre de l'article : "{title}"
    Catégorie : "{category}"
    Lien : {url}

    Rédige uniquement le texte du tweet, sans rien d'autre.
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

def post_tweet(text):
    """Poste le texte sur X (Twitter)."""
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET
    )
    client.create_tweet(text=text)
    print(f"Tweet publié avec succès :\n{text}")

def main():
    """Fonction principale du script d'auto-tweet."""
    print("Début du script d'auto-tweet...")
    
    latest_article_path = get_latest_article()
    print(f"Dernier article trouvé : {latest_article_path}")
    
    with open(latest_article_path, 'r', encoding='utf-8') as f:
        # On lit les métadonnées de l'article
        # Pour que cela fonctionne, on devra apprendre à Aurore à ajouter des métadonnées
        # au début de ses fichiers. Pour l'instant, on simule.
        # Remplaçons cette partie par une extraction simple du titre pour le moment.
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = soup.find('title').text.split('|')[0].strip()
        category_tag = soup.find('meta', attrs={'name': 'category'})
        category = category_tag['content'] if category_tag else 'Actualité'

    article_url = f"{SITE_URL}/{latest_article_path}"
    
    tweet_text = generate_tweet(title, article_url, category)
    
    post_tweet(tweet_text)
    print("Script d'auto-tweet terminé.")

if __name__ == "__main__":
    main()
