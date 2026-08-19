import re

profil_path = r'C:\SUNUCU_PAKETI\RentACar_Sistem\templates\profil.html'

with open(profil_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Currently it looks like:
# <div style="display: grid; grid-template-columns: 1fr 350px; gap: 2rem;">
#   <div class="section-card"> ... Banner ... </div>
#   <div class="settings-card"> ... KABIS ... </div>
#   <div class="section-card"> ... System Info ... </div>
# </div>

# Let's extract the 3 cards.
# First, change <div class="settings-card"> to <div class="section-card"> for consistency
html = html.replace('<div class="settings-card">', '<div class="section-card">')

# We want to put System Info back into the grid with Banner, and put KABIS below the grid.
# The KABIS block starts with:
#   <!-- KABİS Entegrasyon Ayarları -->
#   <div class="section-card">
#   <div class="settings-header">
#   ...
#   </form>
#   </div>
#
# Let's extract KABIS entirely.
match = re.search(r'\s*<!-- KABİS Entegrasyon Ayarları -->.*?(?<=</form>)\s*</div>', html, re.DOTALL)
if match:
    kabis_code = match.group(0)
    html = html.replace(kabis_code, '') # Remove it from inside the grid
    
    # Now find where the grid ends.
    # The grid is: `<div style="display: grid; grid-template-columns: 1fr 350px; gap: 2rem;">`
    # and it ends with `</div>` right before `</div>\n    {% endif %}\n  </main>\n</div>`
    # Wait, System Info is inside the grid!
    
    # Find `<!-- TAB: SETTINGS -->` and the `</div>` that closes its grid.
    # We can just insert kabis_code after the `Sistem Bilgisi` section card ends.
    # Sistem Bilgisi ends with:
    #             <div style="font-weight: 700; color: #1e40af;">Türkiye / İstanbul</div>
    #           </div>
    #         </div>
    #       </div>
    #     </div>
    # Let's find `<div style="font-weight: 700; color: #1e40af;">Türkiye / İstanbul</div>\n            </div>\n          </div>\n        </div>\n      </div>`
    
    insert_point = re.search(r'<div style="font-weight: 700; color: #1e40af;">Türkiye / İstanbul</div>\s*</div>\s*</div>\s*</div>\s*</div>', html)
    if insert_point:
        # The last </div> closes `profile-tab-settings`
        # The second to last </div> closes the `display: grid`
        # We want to insert KABIS right after the `display: grid` </div>
        
        # Let's just do:
        parts = html.split('<!-- TAB: SETTINGS -->')
        settings_tab = parts[1]
        
        # Inside settings_tab, the grid is `<div style="display: grid; grid-template-columns: 1fr 350px; gap: 2rem;">`
        # Change it to have margin-bottom
        settings_tab = settings_tab.replace('gap: 2rem;">', 'gap: 2rem; margin-bottom: 2rem;">')
        
        # We need to find the `</div>` that closes this grid. It's right after the `Sistem Bilgisi` card.
        # Sistem Bilgisi card ends:
        #   </div>
        # </div>
        # </div> <!-- This closes grid -->
        # </div> <!-- This closes profile-tab-settings -->
        
        # Let's insert kabis_code before the LAST `</div>` of settings_tab (before `{% endif %}`)
        
        # Actually, let's just do a simple replace on the known end of Sistem Bilgisi.
        target = 'Türkiye / İstanbul</div>\n            </div>\n          </div>\n        </div>\n      </div>'
        replacement = 'Türkiye / İstanbul</div>\n            </div>\n          </div>\n        </div>\n\n' + kabis_code + '\n      </div>'
        
        if target in html:
            html = html.replace(target, replacement)
            with open(profil_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print("Successfully reorganized profil.html layout.")
        else:
            print("Could not find the target end string.")
    else:
        print("Could not find insert point.")
else:
    print("Could not find KABIS block to extract.")

