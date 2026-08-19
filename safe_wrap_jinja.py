import os

templates_dir = r"C:\SUNUCU_PAKETI\RentACar_Sistem\templates"

def safe_wrap(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if '<table' not in content:
        return False
        
    # Replace <table with <div class="table-responsive"><table
    # Notice we use 'class=' instead of 'className=' because this is Jinja2 (HTML), not React (JSX)
    new_content = content.replace('<table', '<div class="table-responsive">\n<table')
    new_content = new_content.replace('</table>', '</table>\n</div>')
    
    # Fix duplicates if any
    new_content = new_content.replace('<div class="table-responsive">\n<div class="table-responsive">\n', '<div class="table-responsive">\n')
    new_content = new_content.replace('\n</div>\n</div>', '\n</div>')
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

for root, _, files in os.walk(templates_dir):
    for filename in files:
        if filename.endswith(".html"):
            filepath = os.path.join(root, filename)
            if safe_wrap(filepath):
                print(f"Safely Wrapped {filename}")
