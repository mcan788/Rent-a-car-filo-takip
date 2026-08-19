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
    
    # We want to insert kabis_code into the "Ayarlar" tab in profil.html
    # The tab has `<div id="profile-tab-settings" class="profile-tab-content">`
    # and inside it:
    # `<div style="display: grid; grid-template-columns: 1fr 350px; gap: 2rem;">`
    # Let's insert it right after the closing `</div>` of that grid.
    # We need to find `</div>\n    </div>\n    {% endif %}\n  </main>`
    # Wait, the grid ends, then the tab content ends, then `{% endif %}` then `</main>`.

    # Let's just find the `Sistem Bilgisi` section end in the settings tab
    # `<div class="section-card"> ... <h3>Sistem Bilgisi</h3> ... </div>`
    
    # Actually, a better place is right inside the settings tab.
    # Let's find: `</form>\n        </div>\n\n        <div class="section-card">\n          <div class="section-title">`
    # We can insert the KABIS code as a new section card right after the banner form ends, before the Sistem Bilgisi card.
    
    # Better yet, just find the `<!-- TAB: SETTINGS -->` block and insert it inside the left column.
    
    replace_target = r'</form>\s*</div>\s*<div class="section-card">'
    
    new_html = re.sub(
        replace_target,
        f'</form>\n        </div>\n\n        {kabis_code}\n\n        <div class="section-card">',
        profil_html,
        count=1
    )
    
    if new_html != profil_html:
        with open(profil_path, 'w', encoding='utf-8') as f:
            f.write(new_html)
        print("Updated profil.html successfully.")
    else:
        print("Could not find the insertion point in profil.html")
else:
    print("KABIS block not found in ayarlar.html")
