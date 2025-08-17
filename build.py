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
STATIC_ASSETS = ["img", "robots.txt", "sitemap.xml"] # On enlève les pages HTML d'ici
STATIC_PAGES = ["a-propos", "contact", "culture", "mentions-legales", "politique-confidentialite", "charte-verification", "politique", "technologie"]

def get_article_details(file_path):
    # ... (cette fonction ne change pas) ...
    # ... (copie la version de la réponse précédente)

def main():
    print("Début de la construction du site...")
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    for asset in STATIC_ASSETS:
        # ... (cette boucle ne change pas) ...
    
    # ... (la récupération des articles ne change pas) ...
    
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    
    # --- NOUVELLE SECTION : GÉNÉRATION DES PAGES STATIQUES ---
    print("Génération des pages statiques...")
    for page_name in STATIC_PAGES:
        try:
            template = env.get_template(f"{page_name}.html.j2")
            html_content = template.render() # On peut passer des variables ici si besoin
            with open(os.path.join(OUTPUT_DIR, f'{page_name}.html'), 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"- Page '{page_name}.html' créée.")
        except Exception as e:
            print(f"ATTENTION: Le template pour la page '{page_name}' n'a pas été trouvé. {e}")
    # --- FIN DE LA NOUVELLE SECTION ---
    
    # Génération de la page d'accueil (ne change pas)
    print("Génération de la page d'accueil...")
    template_index = env.get_template('index.html.j2')
    html_content_index = template_index.render(articles=articles_for_homepage)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content_index)
    print("Page 'index.html' générée.")
    
    print("Construction du site terminée !")

if __name__ == "__main__":
    main()
