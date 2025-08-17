# Dans la fonction main() de build.py

def main():
    # ... (le début de la fonction ne change pas)

    # On définit les variables globales à passer à tous les templates
    context = {
        "current_year": datetime.now().year,
        "site_name": "L'Horizon Libre"
        # Ajoute ici d'autres variables globales si besoin
    }

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    
    # Génère la page d'accueil en passant le contexte
    template_index = env.get_template('index.html.j2')
    # On ajoute **context
    html_content_index = template_index.render(articles=articles_for_homepage, **context)
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content_index)
    print("Page 'index.html' générée.")
    
    # ... (les autres boucles de génération doivent aussi recevoir **context)
    # Exemple pour les pages de catégories
    for category, articles_list in articles_by_category.items():
        # On ajoute **context
        html_content = category_template.render(category_name=category, articles=articles_list, **context)
        with open(os.path.join(OUTPUT_DIR, f'{category}.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)

    # Exemple pour les pages simples
    for page_name in SIMPLE_PAGES:
        template = env.get_template(f"{page_name}.html.j2")
        # On ajoute **context
        html_content = template.render(**context)
        with open(os.path.join(OUTPUT_DIR, f'{page_name}.html'), 'w', encoding='utf-8') as f:
            f.write(html_content)

    print("Construction du site terminée !")

# ... (le reste du fichier ne change pas)
