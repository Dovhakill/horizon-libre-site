import os
import shutil
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup
from datetime import datetime
import locale

# Définit la langue française pour les dates
locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')

# --- Configuration ---
ARTICLES_DIR = "article"
TEMPLATES_DIR = "templates"
OUTPUT_DIR = "public"

def get_article_details(file_path):
    """Extrait les métadonnées d'un fichier d'article HTML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        title_tag = soup.find('title')
        title = title_tag.text.split('|')[0].strip() if title_tag else "Titre manquant"
        
        time_tag = soup.find('time')
        date_iso = time_tag['datetime'] if time_tag else None
        
        date_obj = datetime.fromisoformat(date_iso.replace('Z', '+00:00')) if date_iso else datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # Formatte la date en français (ex: 17 août 2025)
        date_human = date_obj.strftime("%d %B %Y")

        image_tag = soup.select_one('figure img')
        image_url = image_tag['src'] if image_tag else "https://placehold.co/600x400/1E3A8A/FFFFFF?text=Aurore"
        
        return {
            "title": title,
            "filename": os.path.basename(file_path),
            "date_iso": date_iso,
            "date_human": date_human,
            "image_url": image_url,
        }

def main():
    """Fonction principale du script de build."""
    print("Début de la construction du site...")

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    
    if os.path.exists(ARTICLES_DIR):
        shutil.copytree(ARTICLES_DIR, os.path.join(OUTPUT_DIR, ARTICLES_DIR))
        print(f"Dossier '{ARTICLES_DIR}' copié.")

    articles = []
    articles_path = os.path.join(OUTPUT_DIR, ARTICLES_DIR)
    if os.path.exists(articles_path):
        for filename in os.listdir(articles_path):
            if filename.endswith(".html"):
                details = get_article_details(os.path.join(articles_path, filename))
                articles.append(details)
    
    articles.sort(key=lambda x: x['date_iso'], reverse=True)
    print(f"{len(articles)} articles trouvés et triés.")

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template('index.html.j2')
    
    html_content = template.render(articles=articles)
    
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Nouvelle page 'index.html' générée.")
    
    print("Construction du site terminée !")

if __name__ == "__main__":
    main()
