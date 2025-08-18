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

ARTICLES_DIR = "article"
TEMPLATES_DIR = "templates"import os
import shutil
import json
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
STATIC_ASSETS = ["img", "robots.txt", "sitemap.xml", "ads.txt"]
SIMPLE_PAGES = ["a-propos", "contact", "mentions-legales", "politique-confidentialite", "charte-verification"]
CATEGORIES = ["politique", "culture", "technologie", "international"]

def get_article_details(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = (soup.find('title').text.split('|')[0].strip() if soup.find('title') else "Titre manquant")
        time_tag = soup.find('time')
        date_iso = (time_tag['datetime'] if time_tag else datetime.now().isoformat())
        dek_tag = soup.select_one('p.dek')
        description = dek_tag.text if dek_tag else ""
        category_tag = soup.find('meta', attrs={'name': 'category'})
        category = (category_tag['content'].lower() if category_tag and category_tag.get('content') else "international")
        return {"title": title, "filename": os.path.basename(file_path), "date_iso": date_iso, "description": description, "category": category}

def main():
    print("Début de la construction du site...")
    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    for asset in STATIC_ASSETS:
        source_path = os.path.join('.', asset)
        if os.path.exists(source_path):
            dest_path = os.path.join(OUTPUT_DIR, asset)
            (shutil.copytree(source_path, dest_path) if os.path.isdir(source_path) else shutil.copy2(source_path, dest_path))

    all_articles = []
    if os.path.exists(ARTICLES_DIR):
        dest_articles_dir = os.path.join(OUTPUT_DIR, ARTICLES_DIR)
        os.makedirs(dest_articles_dir, exist_ok=True)
        for filename in os.listdir(ARTICLES_DIR):
            if filename.endswith(".html"):
                shutil.copy2(os.path.join(ARTICLES_DIR, filename), dest_articles_dir)
                details = get_article_details(os.path.join(ARTICLES_DIR, filename))
                all_articles.append(details)
    all_articles.sort(key=lambda x: x['date_iso'], reverse=True)
    
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    context = {"current_year": datetime.now().year, "site_name": "L'Horizon Libre"}

    # ... (génération de l'accueil, des catégories, et des pages simples ne change pas)

    # --- NOUVELLE SECTION : GÉNÉRATION DE L'INDEX DE RECHERCHE ---
    print("Génération de l'index de recherche...")
    search_index = []
    for article in all_articles:
        search_index.append({
            "title": article['title'],
            "url": f"{ARTICLES_DIR}/{article['filename']}",
            "description": article.get('description', '')
        })
    with open(os.path.join(OUTPUT_DIR, 'search-index.json'), 'w', encoding='utf-8') as f:
        json.dump(search_index, f, ensure_ascii=False)
    print("Fichier 'search-index.json' créé.")

    print("Construction terminée !")

if __name__ == "__main__":
    main()
OUTPUT_DIR = "public"
STATIC_ASSETS = ["img", "politique.html", "culture.html", "technologie.html", "a-propos.html", "contact.html"]

def get_article_details(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
        title = (soup.find('title').text.split('|')[0].strip() if soup.find('title') else "Titre manquant")
        time_tag = soup.find('time')
        date_iso = (time_tag['datetime'] if time_tag else datetime.now().isoformat())
        date_obj = datetime.fromisoformat(date_iso.replace('Z', '+00:00'))
        date_human = date_obj.strftime("%d %B %Y")
        image_tag = soup.select_one('article figure img')
        image_url = (image_tag['src'] if image_tag else "https://placehold.co/600x400/1E3A8A/FFFFFF?text=Aurore")
        return {"title": title, "filename": os.path.basename(file_path), "date_iso": date_iso, "date_human": date_human, "image_url": image_url}

def main():
    print("Début de la construction du site...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    for asset in STATIC_ASSETS:
        source_path = os.path.join('.', asset)
        if os.path.exists(source_path):
            dest_path = os.path.join(OUTPUT_DIR, asset)
            (shutil.copytree(source_path, dest_path) if os.path.isdir(source_path) else shutil.copy2(source_path, dest_path))
            print(f"Asset '{asset}' copié.")

    all_articles = []
    source_articles_dir = ARTICLES_DIR
    if os.path.exists(source_articles_dir):
        dest_articles_dir = os.path.join(OUTPUT_DIR, ARTICLES_DIR)
        os.makedirs(dest_articles_dir, exist_ok=True)
        for filename in os.listdir(source_articles_dir):
            if filename.endswith(".html"):
                shutil.copy2(os.path.join(source_articles_dir, filename), dest_articles_dir)
                details = get_article_details(os.path.join(source_articles_dir, filename))
                all_articles.append(details)

    all_articles.sort(key=lambda x: x['date_iso'], reverse=True)
    print(f"{len(all_articles)} articles trouvés au total.")
    
    # --- LOGIQUE DE PAGINATION ---
    articles_for_homepage = all_articles[:9]
    print(f"Affichage des {len(articles_for_homepage)} articles les plus récents sur la page d'accueil.")
    
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template('index.html.j2')
    html_content = template.render(articles=articles_for_homepage)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Page 'index.html' générée.")
    print("Construction du site terminée !")

if __name__ == "__main__":
    main()
