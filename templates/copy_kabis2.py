import re
import os

ayarlar_path = r'C:\SUNUCU_PAKETI\RentACar_Sistem\templates\ayarlar.html'
profil_path = r'C:\SUNUCU_PAKETI\RentACar_Sistem\templates\profil.html'

with open(ayarlar_path, 'r', encoding='utf-8') as f:
    ayarlar_html = f.read()

# Extract KABIS block
match = re.search(r'<!-- KABİS Entegrasyon Ayarları -->(.*?)<!-- Sözleşme Şablonu Ayarları -->', ayarlar_html, re.DOTALL)
if match:
    kabis_code = match.group(0).replace('<!-- Sözleşme Şablonu Ayarları -->', '')
    print("Found KABIS code.")

    with open(profil_path, 'r', encoding='utf-8') as f:
        profil_html = f.read()
    
    # Use simple string replacement to avoid regex escape issues
    replace_target = '</form>\n        </div>\n\n        <div class="section-card">'
    # wait, the spacing might differ, let's use regex to find the split point, then string manipulation
    
    split_match = re.search(r'</form>\s*</div>\s*<div class="section-card">', profil_html)
    if split_match:
        idx = split_match.start()
        new_html = profil_html[:idx] + '</form>\n        </div>\n\n' + kabis_code + '\n\n        <div class="section-card">' + profil_html[split_match.end():]
        
        with open(profil_path, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print("Updated profil.html successfully.")
    else:
        print("Could not find the insertion point in profil.html")
else:
    print("KABIS block not found in ayarlar.html")
