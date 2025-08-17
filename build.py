import os
import shutil
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup
from datetime import datetime
import locale
import os
import shutil
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup
from datetime import datetime
import locale

try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')

# --- Configuration ---
ARTICLES_DIR = "article"
TEMPLATES_DIR = "templates"
OUTPUT_DIR = "public"
# Liste des fichiers et dossiers à copier directement
STATIC_ASSETS = ["img", "politique.html", "culture.html", "technologie.html", "a-propos.html", "contact.html", "mentions-legales.html", "politique-confidentialite.html", "charte-verification.html"]

def get_article_details(file_path):
    # ... (cette fonction ne change pas) ...
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title_tag = soup.find('title')
        title = title_tag.text.split('|')[0].strip() if title_tag else "Titre manquant"
        time_tag = soup.find('time')
        date_iso = time_tag['datetime'] if time_tag else datetime.now().isoformat()
        date_obj = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
        date_human = date_obj.strftime("%d %B %Y")
        image_tag = soup.select_one('figure img')
        image_url = image_tag['src'] if image_tag else "https://placehold.co/600x400/1E3A8A/FFFFFF?text=Aurore"
        return {
            "title": title, "filename": os.path.basename(file_path),
            "date_iso": date_iso, "date_human": date_human, "image_url": image_url,
        }

def main():
    print("Début de la construction du site...")

    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)
    
    # --- SECTION AMÉLIORÉE ---
    # On copie tous les assets statiques (dossier img, pages HTML, etc.)
    for asset in STATIC_ASSETS:
        source_path = os.path.join('.', asset)
        dest_path = os.path.join(OUTPUT_DIR, asset)
        if os.path.exists(source_path):
            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
            print(f"Asset '{asset}' copié.")
    # --- FIN DE LA SECTION ---

    articles = []
    if os.path.exists(ARTICLES_DIR):
        for filename in os.listdir(ARTICLES_DIR):
            if filename.endswith(".html"):
                details = get_article_details(os.path.join(ARTICLES_DIR, filename))
                articles.append(details)
    
    articles.sort(key=lambda x: x['date_iso'], reverse=True)
    print(f"{len(articles)} articles trouvés et triés.")

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template('index.html.j2')
    
    html_content = template.render(articles=articles)
    
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Nouvelle page 'index.html' générée.")
    
    # On copie aussi les fichiers articles dans public/article
    articles_output_dir = os.path.join(OUTPUT_DIR, ARTICLES_DIR)
    if not os.path.exists(articles_output_dir):
        os.makedirs(articles_output_dir)
    if os.path.exists(ARTICLES_DIR):
        for article in articles:
             shutil.copy2(os.path.join(ARTICLES_DIR, article['filename']), articles_output_dir)

    print("Construction du site terminée !")

if __name__ == "__main__":
    main()
# Essaye de définir la langue française pour les dates
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    print("ATTENTION: Locale fr_FR.UTF-8 non trouvée, les dates pourraient être en anglais.")
    locale.setlocale(locale.LC_TIME, '')

# --- Configuration ---
ARTICLES_DIR = "article"
TEMPLATES_DIR = "templates"
OUTPUT_DIR = "public" # C'est le dossier que Netlify publiera

def get_article_details(file_path):
    """Extrait les métadonnées d'un fichier d'article HTML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        
        title_tag = soup.find('title')
        title = title_tag.text.split('|')[0].strip() if title_tag else "Titre manquant"
        
        time_tag = soup.find('time')
        date_iso = time_tag['datetime'] if time_tag else datetime.now().isoformat()
        
        date_obj = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
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
    os.makedirs(os.path.join(OUTPUT_DIR, ARTICLES_DIR))
    
    # Copie les articles existants un par un
    if os.path.exists(ARTICLES_DIR):
        for item in os.listdir(ARTICLES_DIR):
            s = os.path.join(ARTICLES_DIR, item)
            d = os.path.join(OUTPUT_DIR, ARTICLES_DIR, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, symlinks=True, ignore=None)
            else:
                shutil.copy2(s, d)
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
