import codecs
path = r'c:\Users\MCAN\Desktop\Masa Üstü Ana Klasör\Proje Dosyaları\Proje kod dosyaları\Rent A Car - Tur Takip\rent_a_car\blueprints\main.py'
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

import re

# We want to replace the code inside personel_ekle from `if User.query.filter_by(username=username).first():`
# up to `except Exception as e:` block.

start_str = "    if User.query.filter_by(username=username).first():"
end_str = "        except Exception as e:\n            print(f\"[SSO SYNC HATA] Personel TurMasterDB'ye aktarılamadı: {e}\", flush=True)"

start_idx = content.find(start_str)
end_idx = content.find(end_idx_str := "print(f\"[SSO SYNC HATA] Personel TurMasterDB'ye aktarılamadı: {e}\", flush=True)", start_idx)

if start_idx != -1 and end_idx != -1:
    end_idx += len(end_idx_str)
    
    new_code = """    company_id = int(request.form.get('company_id', g.current_company.id))
    
    if User.query.filter_by(username=username).first():
        flash('Bu kullanıcı adı zaten alınmış.', 'error')
        return redirect(url_for('main.profil'))
        
    new_user = User(
        username=username,
        name=name,
        role_id=role_id,
        role='super_admin' if role_id == 11 else 'admin' if role_id == 12 else 'yonetici' if role_id in (21, 31) else 'personel',
        company_id=company_id,
        company_name="Master" if company_id == 1 else "Rent A Car" if company_id == 2 else "Tur Takip"
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    # Master veya Tur Takip personeli ekleniyorsa SSO için TurMasterDB'ye senkronize et
    if company_id in (1, 3):
        try:
            from flask import current_app
            import pyodbc
            server = current_app.config.get('DB_SERVER')
            driver = current_app.config.get('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
            user_db = current_app.config.get('DB_USER')
            pass_db = current_app.config.get('DB_PASS')

            if server:
                if user_db and pass_db:
                    conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;UID={user_db};PWD={pass_db};Encrypt=no;TrustServerCertificate=yes;"
                else:
                    conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"

                with pyodbc.connect(conn_str, timeout=5) as conn:
                    with conn.cursor() as cursor:
                        if company_id == 1:
                            sys_role = 'SUPERADMIN' if role_id == 11 else 'ADMIN'
                        else:
                            sys_role = 'TOUR_TRACKING_ADMIN' if role_id == 31 else 'TOUR_TRACKING_PERSONNEL'
                        
                        cursor.execute("SELECT Username FROM SystemUsers WHERE Username = ?", (username,))
                        if not cursor.fetchone():
                            cursor.execute(
                                "INSERT INTO SystemUsers (Username, PasswordHash, FullName, Role) VALUES (?, ?, ?, ?)",
                                (username, new_user.password_hash, name, sys_role)
                            )
                            conn.commit()
                            print(f"[SSO SYNC] Yeni personel '{username}' merkezi TurMasterDB.SystemUsers tablosuna ({sys_role}) kopyalandı.", flush=True)
        except Exception as e:
            print(f"[SSO SYNC HATA] Personel TurMasterDB'ye aktarılamadı: {e}", flush=True)"""
    
    new_content = content[:start_idx] + new_code + content[end_idx:]
    with codecs.open(path, 'w', 'utf-8') as f:
        f.write(new_content)
    print("SUCCESS")
else:
    print("FAILED TO FIND INDICES", start_idx, end_idx)
