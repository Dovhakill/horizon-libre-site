import os
import shutil
import json
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup
from datetime import datetime
import locale

# --- CONFIGURATION ---
# On définit le chemin de base du projet pour que les chemins soient toujours corrects
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARTICLES_DIR = os.path.join(BASE_DIR, "article")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "public")

STATIC_ASSETS = ["img", "robots.txt", "sitemap.xml", "ads.txt"]
# ... (les autres listes comme SIMPLE_PAGES, CATEGORIES ne changent pas)

def get_article_details(file_path):
    # ... (cette fonction ne change pas)
    # ... (copie-colle la dernière version de cette fonction)

def main():
    print("Début de la construction du site...")
    if os.path.exists(OUTPUT_DIR): shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # Copie les assets statiques en utilisant le chemin de base
    for asset in STATIC_ASSETS:
        source_path = os.path.join(BASE_DIR, asset)
        if os.path.exists(source_path):
            dest_path = os.path.join(OUTPUT_DIR, asset)
            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
    
    # Le reste de la fonction ne change pas, mais utilisera les chemins corrects
    all_articles = []
    if os.path.exists(ARTICLES_DIR):
        dest_articles_dir = os.path.join(OUTPUT_DIR, "article")
        os.makedirs(dest_articles_dir, exist_ok=True)
        for filename in os.listdir(ARTICLES_DIR):
            if filename.endswith(".html"):
                shutil.copy2(os.path.join(ARTICLES_DIR, filename), dest_articles_dir)
                details = get_article_details(os.path.join(ARTICLES_DIR, filename))
                all_articles.append(details)

    all_articles.sort(key=lambda x: x['date_iso'], reverse=True)
    
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    context = {"current_year": datetime.now().year, "site_name": "L'Horizon Libre"}
    
    # Génération de la page d'accueil
    template = env.get_template('index.html.j2')
    html_content = template.render(articles=all_articles[:9], **context)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # ... (génération des autres pages)
    
    print("Construction terminée !")

if __name__ == "__main__":
    main()
