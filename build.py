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
STATIC_ASSETS = ["img", "robots.txt", "sitemap.xml"]
# On liste les templates des pages statiques à générer
STATIC_PAGES = ["a-propos", "contact", "culture", "mentions-legales", "politique-confidentialite", "charte-verification", "politique", "technologie"]

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
    articles_for_homepage = all_articles[:9]
    
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    
    # --- SECTION AJOUTÉE : GÉNÉRATION DES PAGES STATIQUES ---
    print("Génération des pages statiques...")
    for page_name in STATIC_PAGES:
        try:
            template = env.get_template(f"{page_name}.html.j2")
            html_content = template.render()
            with open(os.path.join(OUTPUT_DIR, f'{page_name}.html'), 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"- Page '{page_name}.html' créée.")
        except Exception:
            print(f"ATTENTION: Le template pour la page '{page_name}.html.j2' n'a pas été trouvé, la page ne sera pas créée.")
    
    # Génération de la page d'accueil
    template_index = env.get_template('index.html.j2')
    html_content_index = template_index.render(articles=articles_for_homepage)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content_index)
    print("Page 'index.html' générée.")
    print("Construction du site terminée !")

if __name__ == "__main__":
    main()
