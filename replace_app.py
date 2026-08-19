import codecs
path = r'c:\Users\MCAN\Desktop\Masa Üstü Ana Klasör\Proje Dosyaları\Proje kod dosyaları\Rent A Car - Tur Takip\rent_a_car\app.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

start_str = "        if user.role_id in (11, 12, 13):"
end_str = "        if getattr(user, 'is_2fa_enabled', False):"

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx)

if start_idx != -1 and end_idx != -1:
    new_code = """        if user.company_id == 1:
            target_module = 'MASTER'
        elif user.company_id == 3:
            target_module = 'TOUR_TRACKING'
        else:
            target_module = 'RENT_A_CAR'

"""
    new_content = content[:start_idx] + new_code + content[end_idx:]
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(new_content)
    print("SUCCESS")
else:
    print("FAILED TO FIND INDICES")
