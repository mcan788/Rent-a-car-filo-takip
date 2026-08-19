import codecs
path = r'c:\Users\MCAN\Desktop\Masa Üstü Ana Klasör\Proje Dosyaları\Proje kod dosyaları\Rent A Car - Tur Takip\rent_a_car\blueprints\main.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

start_str = "    if current_user.role_id in (31, 32):"
end_str = "        # Master Dashboard Logic (SaaS Yönetim Paneli)"

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx)

if start_idx != -1 and end_idx != -1:
    new_code = """    if current_user.company_id == 3:
        portal_url = os.getenv('PORTAL_URL', 'http://localhost:3000/')
        flash("Erişim Reddedildi. Tur Takip kullanıcıları sadece Tur Takip paneline giriş yapabilir.", "error")
        return redirect(portal_url.rstrip('/') + '/agency')

    # Log action
    log_action(current_user, 'login', 'Kullanıcı dashboarda giriş yaptı.')

    if current_user.company_id == 1:
"""
    new_content = content[:start_idx] + new_code + content[end_idx:]
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(new_content)
    print("SUCCESS")
else:
    print("FAILED TO FIND INDICES")
