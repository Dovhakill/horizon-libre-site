import os
import shutil
import json
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup
from datetime import datetime
import locale

try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    print("ATTENTION: Locale fr_FR.UTF-8 non trouvée.")
    locale.setlocale(locale.LC_TIME, '')

# --- Configuration ---
ARTICLES_DIR = "article"
TEMPLATES_DIR = "templates"
OUTPUT_DIR = "public"
STATIC_ASSETS = [
    "img", "robots.txt", "sitemap.xml", "ads.txt"
]
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
        image_tag = soup.select_one('article figure img')
        image_url = (image_tag['src'] if image_tag else "https://placehold.co/600x400/1E3A8A/FFFFFF?text=Aurore")
        return {"title": title, "filename": os.path.basename(file_path), "date_iso": date_iso, "description": description, "category": category, "image_url": image_url}

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

    index_template = env.get_template('index.html.j2')
    index_html = index_template.render(articles=all_articles[:9], **context)
    with open(os.path.join(OUTPUT_DIR
