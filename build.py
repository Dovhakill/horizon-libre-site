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
TEMPLATES_DIR = "templates"
OUTPUT_DIR = "public"
STATIC_ASSETS = ["img"]
SIMPLE_PAGES = ["a-propos", "contact", "mentions-legales", "politique-confidentialite", "charte-verification"]
CATEGORIES = ["politique", "culture", "technologie", "international"]

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
        category_tag = soup.find('meta', attrs={'name': 'keywords'})
        category = "International"
        if category_tag and category_tag.get('content'):
            first_keyword = category_tag['content'].split(',')[0].strip().lower()
            if first_keyword in CATEGORIES:
                category = first_keyword
        return {"title": title, "filename": os.path.basename(file_path), "date_iso": date_iso, "date_human": date_human, "image_url": image_url, "category": category}

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
    
    context = {
        "current_year": datetime.now().year,
        "site_name": "L'Horizon Libre"
    }

    articles_for_homepage = all_articles[:9]
    index_template = env.get_template('index.html.j2')
    index_html = index_template.render(articles=articles_for_homepage, **context)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print("Page d'accueil générée.")

    articles_by_category = {cat: [] for cat in CATEGORIES}
    for article in all_articles:
        if article['category'] in articles_by_category:
            articles_by_category[article['category']].append(article)
    category_template = env.get_template("category.html.j2")
    for category, articles_list in articles_by_category.items():
        html_content = category_template.render(category_name=category, articles=articles_list, **context)
        with open(os.path.join(OUTPUT_DIR, f'{category}.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)
    print(f"- Pages catégories générées.")

    for page_name in SIMPLE_PAGES:
        try:
            template = env.get_template(f"{page_name}.html.j2")
            html_content = template.render(**context)
            with open(os.path.join(OUTPUT_DIR, f'{page_name}.html'), 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"- Page simple '{page_name}.html' créée.")
        except Exception as e:
            print(f"ATTENTION: Template pour '{page_name}' manquant.")

    print("Construction du site terminée !")

if __name__ == "__main__":
    main()
