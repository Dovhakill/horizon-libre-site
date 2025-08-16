import os
from jinja2 import Environment, FileSystemLoader
from bs4 import BeautifulSoup
import shutil

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
        
        # On utilise la date de modification du fichier pour le tri
        date_mod = os.path.getmtime(file_path)

        return {
            "title": title,
            "filename": os.path.basename(file_path),
            "date": date_mod,
        }

def main():
    """Fonction principale du script de build."""
    print("Début de la construction du site...")

    # 1. Prépare le dossier de sortie
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR) # On nettoie l'ancien site
    os.makedirs(OUTPUT_DIR)
    
    # 2. Copie les articles existants dans le dossier de sortie
    if os.path.exists(ARTICLES_DIR):
        shutil.copytree(ARTICLES_DIR, os.path.join(OUTPUT_DIR, ARTICLES_DIR))
        print(f"Dossier '{ARTICLES_DIR}' copié.")

    # 3. Récupère les informations de tous les articles
    articles = []
    articles_path = os.path.join(OUTPUT_DIR, ARTICLES_DIR)
    if os.path.exists(articles_path):
        for filename in os.listdir(articles_path):
            if filename.endswith(".html"):
                details = get_article_details(os.path.join(articles_path, filename))
                articles.append(details)
    
    # 4. Trie les articles du plus récent au plus ancien
    articles.sort(key=lambda x: x['date'], reverse=True)
    print(f"{len(articles)} articles trouvés et triés.")

    # 5. Génère la nouvelle page d'accueil
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    template = env.get_template('index.html.j2')
    
    html_content = template.render(articles=articles)
    
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("Nouvelle page 'index.html' générée.")
    
    print("Construction du site terminée !")

if __name__ == "__main__":
    main()
