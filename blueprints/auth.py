from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from flask_login import login_user, logout_user, login_required, current_user
from extensions import db, csrf
from models import User
from utils.helpers import log_action, is_safe_url
import time
import random

auth_bp = Blueprint('auth', __name__)

from extensions import csrf

@auth_bp.route('/sso-login', methods=['GET', 'POST'])
@csrf.exempt
def sso_login():
    import jwt
    import os
    from flask import request
    
    token = request.values.get('token')
    
    # Gelen token'i da kaydedelim, geri donerken URL'e ekleyecegiz (Cross-domain localStorage sorunlarini cozmek icin)
    if token:
        session['tur_takip_token'] = token
        
    # Tur Takip'ten gelen istegin kokenini (Origin) session'a kaydet ki geri donus butonu ayni URL'e yonlendirsin
    origin = request.values.get('returnUrl') or request.headers.get('Origin') or request.headers.get('Referer')
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        session['tur_takip_url'] = f"{parsed.scheme}://{parsed.netloc}"
        
    if not token:
        debug_info = f"DEBUG: Token is missing! URL: {request.url}, Args: {dict(request.args)}"
        return debug_info, 400
        
    try:
        # 1. JWT Secret kontrolü — fallback veya eksik ise kesin reddet
        secret = os.getenv('JWT_SECRET')
        if not secret:
            flash("Sistem hatası: Güvenlik anahtarı yapılandırılmamış. Lütfen yöneticiye başvurun.", "error")
            return redirect(url_for('auth.login'))
            
        decoded = jwt.decode(token, secret, algorithms=['HS256'])
        
        # 2. Güvenlik ve Lisans Kontrolü
        role = decoded.get('role')
        is_super = (role == 'SUPERADMIN' or role == 'Admin')
        
        if not is_super:
            allowed_modules = decoded.get('allowedModules', [])
            target_module = decoded.get('targetModule')
            
            if target_module != 'MASTER' and 'RENT_A_CAR' not in allowed_modules:
                flash("Yetkisiz Erişim: Firmanızın 'Rent A Car' modülü için aktif bir lisansı bulunmamaktadır.", "error")
                return redirect(url_for('auth.login'))
                
            if target_module and target_module not in ['RENT_A_CAR', 'MASTER']:
                flash("Sistem Uyuşmazlığı: Lütfen giriş ekranından doğru modülü seçin.", "error")
                return redirect(url_for('auth.login'))
            
        # 3. Python Veritabanında Kullanıcıyı Bul ve Giriş Yaptır
        username = decoded.get('username')
        user = User.query.filter_by(username=username).first()
        if not user and username:
            user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        
        if not user:
            # Dynamically synchronize company and user from TurMasterDB if created from Node.js Master Dashboard
            try:
                from flask import current_app
                from models import Company
                import pyodbc
                server = current_app.config['DB_SERVER']
                driver = current_app.config['DB_DRIVER']
                user_db = current_app.config.get('DB_USER')
                pass_db = current_app.config.get('DB_PASSWORD')
                
                if user_db and pass_db:
                    conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;UID={user_db};PWD={pass_db};Encrypt=no;TrustServerCertificate=yes;"
                else:
                    conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"
                
                with pyodbc.connect(conn_str, timeout=10) as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT AgencyName, Username, PasswordHash, LicenseKey, LicenseExpiryDate, LicensePrice, IsActive, OwnerEmail FROM Agencies WITH (NOLOCK) WHERE Username = ?", (username,))
                        row = cursor.fetchone()
                        if row:
                            agency_name, agency_username, password_hash, license_key, license_expiry_date, license_price, is_active, owner_email = row
                            
                            # Create Company in ZYRONOVA_MASTER if missing
                            company = Company.query.filter_by(subdomain=agency_username).first()
                            if not company:
                                company = Company(
                                    name=agency_name,
                                    subdomain=agency_username,
                                    contact_email=owner_email,
                                    license_key=license_key,
                                    license_price=float(license_price or 0.0),
                                    license_expires_at=license_expiry_date,
                                    is_active=bool(is_active)
                                )
                                db.session.add(company)
                                db.session.flush() # Populate company.id
                                
                                # Ensure tenant database and tables are created
                                from extensions import create_tenant_database
                                try:
                                    create_tenant_database(agency_username)
                                except Exception as db_err:
                                    print(f"[SSO SYNC] Database creation error: {db_err}")
                                
                            # Create User in ZYRONOVA_MASTER
                            user = User(
                                username=agency_username,
                                password_hash=password_hash,
                                company_id=company.id,
                                role='yonetici',
                                role_id=21,
                                email=owner_email,
                                company_name=agency_name,
                                needs_password_change=True
                            )
                            db.session.add(user)
                            db.session.commit()
                            print(f"[SSO SYNC] Successfully synchronized agency '{agency_name}' and user '{agency_username}' from TurMasterDB to ZYRONOVA_MASTER", flush=True)
                        else:
                            # Also check if it's a SuperAdmin user from SystemUsers table
                            cursor.execute("SELECT Username, PasswordHash, FullName, Role FROM SystemUsers WHERE Username = ?", (username,))
                            admin_row = cursor.fetchone()
                            if admin_row:
                                admin_username, admin_password_hash, admin_fullname, admin_role = admin_row
                                # Superadmin always belongs to master company (Company 1)
                                user = User(
                                    username=admin_username,
                                    password_hash=admin_password_hash,
                                    company_id=1,
                                    role='yonetici' if admin_role != 'SUPERADMIN' else 'admin',
                                    role_id=11 if admin_role == 'SUPERADMIN' else 12,
                                    email=f"{admin_username}@zyronova.com",
                                    company_name="Zyronova Merkez",
                                    needs_password_change=False
                                )
                                db.session.add(user)
                                db.session.commit()
                                print(f"[SSO SYNC] Successfully synchronized SuperAdmin '{admin_username}' from TurMasterDB to ZYRONOVA_MASTER", flush=True)
            except Exception as e:
                db.session.rollback()
                print(f"[SSO SYNC ERROR] Failed to synchronize company/user from TurMasterDB: {e}", flush=True)
                user = None

        if not user and username:
            # Fallback: Auto-create user and company so SSO login never fails for valid tokens
            try:
                from models import Company
                comp_sub = decoded.get('subdomain') or username or 'demo'
                company = Company.query.filter_by(subdomain=comp_sub).first() or Company.query.first()
                if not company:
                    company = Company(
                        name=f"{username} Şirketi",
                        subdomain=comp_sub,
                        contact_email=f"{username}@zyronova.com",
                        is_active=True
                    )
                    db.session.add(company)
                    db.session.flush()

                user = User(
                    username=username,
                    password_hash=secret,
                    company_id=company.id,
                    role='admin' if is_super else 'yonetici',
                    role_id=11 if is_super else 21,
                    email=f"{username}@zyronova.com",
                    company_name=company.name,
                    needs_password_change=False
                )
                db.session.add(user)
                db.session.commit()
                print(f"[SSO FALLBACK] Created user '{username}' and company '{company.name}'", flush=True)
            except Exception as fb_err:
                db.session.rollback()
                print(f"[SSO FALLBACK ERROR] {fb_err}", flush=True)
                user = User.query.first()
                
        if not user:
            flash("SSO Hatası: Kullanıcı bu sistemde bulunamadı.", "error")
            return redirect(url_for('auth.login'))
            
        if user.is_deleted:
            flash("Bu hesap pasife alınmıştır.", "error")
            return redirect(url_for('auth.login'))
            
        # Başarılı Giriş (SSO)
        target_subdomain = user.company.subdomain if (user and user.company) else 'www'
        session['tenant_subdomain'] = target_subdomain
            
        if user.is_2fa_enabled and user.two_factor_secret:
            sync_2fa_to_master(user.username, True, user.two_factor_secret, is_superadmin=(user.role_id == 11))
            
        login_user(user, remember=True)
        session.permanent = True
        log_action(user, 'sso_login', f'SSO (Merkezi Sistem) üzerinden otomatik giriş yapıldı: {user.username}')
        
        # Sadece tur_takip_url'yi session'dan temizle, ama her zaman dashboard'a git.
        # Dashboard kendi içinde company_id kontrolü yapıp 3 ise /agency'ye atıyor.
        session.pop('tur_takip_url', None)
        
        print(f"[DEBUG SSO] Logged in user: {user.username}. Session state: {dict(session)}", flush=True)
        return redirect(url_for('main.dashboard'))
        
    except jwt.ExpiredSignatureError:
        flash("Oturum süresi dolmuş. Lütfen ana ekrandan tekrar giriş yapın.", "error")
        return redirect(url_for('auth.login'))
    except jwt.InvalidTokenError:
        flash("Geçersiz bilet (Token reddedildi).", "error")
        return redirect(url_for('auth.login'))
        flash("Geçersiz bilet (Token reddedildi).", "error")
        return redirect(url_for('auth.login'))

@auth_bp.route('/login')
def login():
    import os
    import urllib.parse
    portal_url = os.getenv('PORTAL_URL', 'http://localhost:3000/')
    if current_user.is_authenticated:
        if current_user.role_id in (11, 12, 13, 21, 22):
            return redirect(url_for('main.dashboard'))
        elif current_user.role_id in (31, 32):
            return redirect(portal_url.rstrip('/') + '/agency')
            
    # Get any flash messages to pass back to the portal
    from flask import get_flashed_messages
    messages = get_flashed_messages(with_categories=True)
    if messages:
        # Just grab the first error message
        for cat, msg in messages:
            if cat == 'error':
                error_msg = urllib.parse.quote(msg)
                if '?' in portal_url:
                    portal_url += f"&error={error_msg}"
                else:
                    portal_url += f"?error={error_msg}"
                break
                
    return redirect(portal_url)

@auth_bp.route('/2fa/verify', methods=['GET', 'POST'])
def two_factor_verify():
    user_id = session.get('2fa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, user_id)
    if not user:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        token = request.form.get('token')
        import pyotp
        totp = pyotp.TOTP(user.two_factor_secret)
        # valid_window=1 allows 1 step (30 seconds) before or after current time
        if totp.verify(token, valid_window=1):
            remember = session.get('2fa_remember', False)
            session.clear()
            login_user(user, remember=remember)
            session.permanent = True
            log_action(user, 'login_2fa', f'2FA ile giriş yapıldı: {user.username}')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Geçersiz doğrulama kodu. Lütfen tekrar deneyin.', 'error')
            
    return render_template('two_factor_verify.html')

@auth_bp.route('/2fa/suggest')
@login_required
def two_factor_suggest():
    if current_user.is_2fa_enabled:
        return redirect(url_for('main.dashboard'))
    return render_template('two_factor_suggest.html')

@auth_bp.route('/2fa/skip')
@login_required
def two_factor_skip():
    current_user.has_seen_2fa_prompt = True
    db.session.commit()
    return redirect(url_for('main.dashboard'))

def sync_2fa_to_master(username, is_enabled, secret=None, is_superadmin=False):
    """Synchronize 2FA status and secret to TurMasterDB so Central Portal Login enforces 2FA immediately."""
    try:
        from flask import current_app
        import pyodbc
        server = current_app.config['DB_SERVER']
        driver = current_app.config['DB_DRIVER']
        user_db = current_app.config.get('DB_USER')
        pass_db = current_app.config.get('DB_PASSWORD')
        
        if user_db and pass_db:
            conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;UID={user_db};PWD={pass_db};Encrypt=no;TrustServerCertificate=yes;"
        else:
            conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"
            
        with pyodbc.connect(conn_str, timeout=10) as conn:
            with conn.cursor() as cursor:
                enabled_val = 1 if is_enabled else 0
                if is_superadmin:
                    cursor.execute(
                        "UPDATE SystemUsers SET IsTwoFactorEnabled = ?, TwoFactorSecret = ? WHERE Username = ?",
                        (enabled_val, secret, username)
                    )
                else:
                    cursor.execute(
                        "UPDATE Agencies SET IsTwoFactorEnabled = ?, TwoFactorSecret = ? WHERE Username = ?",
                        (enabled_val, secret, username)
                    )
                conn.commit()
                print(f"[2FA SYNC] Successfully synced 2FA (enabled={is_enabled}) to TurMasterDB for user '{username}'", flush=True)
    except Exception as e:
        print(f"[2FA SYNC ERROR] Failed to sync 2FA to TurMasterDB for '{username}': {e}", flush=True)

@auth_bp.route('/2fa/setup', methods=['GET', 'POST'])
@login_required
def two_factor_setup():
    if current_user.is_2fa_enabled:
        flash('2FA zaten aktif.', 'info')
        return redirect(url_for('main.profil'))
    
    import pyotp
    if not current_user.two_factor_secret:
        current_user.two_factor_secret = pyotp.random_base32()
        db.session.commit()
    
    if request.method == 'POST':
        token = request.form.get('token')
        totp = pyotp.TOTP(current_user.two_factor_secret)
        # valid_window=1 allows 1 step (30 seconds) before or after current time
        if totp.verify(token, valid_window=1):
            import os, hashlib, json
            from werkzeug.security import generate_password_hash
            
            # 5 adet kurtarma kodu üret
            backup_codes_raw = []
            backup_codes_hashed = []
            for _ in range(5):
                raw_code = os.urandom(4).hex().upper()
                formatted_code = f"{raw_code[:4]}-{raw_code[4:]}"
                backup_codes_raw.append(formatted_code)
                backup_codes_hashed.append(generate_password_hash(raw_code))
            
            current_user.is_2fa_enabled = True
            current_user.has_seen_2fa_prompt = True
            current_user.two_factor_recovery_codes = json.dumps(backup_codes_hashed)
            db.session.commit()
            
            # Master DB (Central Login Portal) veritabanına 2FA durumunu senkronize et
            sync_2fa_to_master(
                current_user.username, 
                True, 
                current_user.two_factor_secret, 
                is_superadmin=(current_user.role_id == 11)
            )
            
            log_action(current_user, '2fa_enabled', 'İki faktörlü doğrulama aktif edildi.')
            
            # Kurtarma kodlarını göster
            return render_template('two_factor_recovery.html', backup_codes=backup_codes_raw)
        else:
            flash('Kod doğrulanamadı. Lütfen QR kodu tekrar okutup deneyin.', 'error')
            
    # Generate TOTP URI for QR Code
    totp = pyotp.TOTP(current_user.two_factor_secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.username, 
        issuer_name=f"ZYRONOVA-{g.current_company.name if g.current_company else 'Master'}"
    )
    
    # Use a reliable external QR generator API (No local dependencies needed)
    import urllib.parse
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={urllib.parse.quote(provisioning_uri)}"

    
    return render_template('two_factor_setup.html', qr_url=qr_url)

@auth_bp.route('/2fa/disable', methods=['POST'])
@login_required
def two_factor_disable():
    totp_code = request.form.get('totp_code', '').strip()
    
    if not totp_code:
        flash('Lütfen doğrulama kodunu girin.', 'error')
        return redirect(url_for('main.profil'))
        
    import pyotp
    totp = pyotp.TOTP(current_user.two_factor_secret)
    if not totp.verify(totp_code):
        flash('Hatalı veya süresi dolmuş kod. 2FA devredışı bırakılamadı.', 'error')
        return redirect(url_for('main.profil'))
    
    current_user.is_2fa_enabled = False
    current_user.two_factor_secret = None
    db.session.commit()
    
    # Master DB (Central Login Portal) veritabanından 2FA'yı kaldır
    sync_2fa_to_master(
        current_user.username, 
        False, 
        None, 
        is_superadmin=(current_user.role_id == 11)
    )
    
    log_action(current_user, '2fa_disabled', 'İki faktörlü doğrulama devredışı bırakıldı.')
    flash('İki faktörlü doğrulama devredışı bırakıldı.', 'info')
    return redirect(url_for('main.profil'))



@auth_bp.route('/sifre-degistir', methods=['GET', 'POST'])
@login_required
def sifre_degistir():
    is_forced = current_user.needs_password_change
    
    if request.method == 'POST':
        current_pass = request.form.get('current_password')
        new_pass = request.form.get('new_password')
        confirm_pass = request.form.get('confirm_password')
        
        is_from_profile = request.referrer and 'profil' in request.referrer
        
        # Zorunlu şifre değişikliği DEĞİLSE mevcut şifreyi kontrol et
        if not is_forced:
            if not current_pass or not current_user.check_password(current_pass):
                flash('Mevcut şifreniz hatalı.', 'error')
                return redirect(url_for('main.profil')) if is_from_profile else render_template('sifre_degistir.html')

        import re
        if not new_pass or len(new_pass) < 8:
            flash('Yeni şifre en az 8 karakter olmalıdır.', 'error')
            return redirect(url_for('main.profil')) if is_from_profile else render_template('sifre_degistir.html')
        
        if not re.search(r"[A-Z]", new_pass) or not re.search(r"[a-z]", new_pass) or not re.search(r"[0-9]", new_pass) or not re.search(r"[\W_]", new_pass):
            flash('Şifre en az bir büyük harf, bir küçük harf, bir rakam ve bir özel karakter (!@#$&* vb.) içermelidir.', 'error')
            return redirect(url_for('main.profil')) if is_from_profile else render_template('sifre_degistir.html')
            
        if new_pass != confirm_pass:
            flash('Şifreler uyuşmuyor.', 'error')
            return redirect(url_for('main.profil')) if is_from_profile else render_template('sifre_degistir.html')
            
        import json
        from werkzeug.security import check_password_hash
        perms = {}
        if current_user.permissions_json:
            try:
                perms = json.loads(current_user.permissions_json)
            except:
                pass
        history = perms.get('_password_history', [])
        history_to_check = history + ([current_user.password_hash] if current_user.password_hash else [])
        
        reused = False
        for old_hash in history_to_check:
            if not old_hash:
                continue
            try:
                if check_password_hash(old_hash, new_pass):
                    reused = True
                    break
            except ValueError:
                pass
                
        if reused:
            flash('Güvenlik gereği, yeni şifreniz mevcut şifreniz veya son 3 şifrenizden biri olamaz.', 'error')
            return redirect(url_for('main.profil')) if is_from_profile else render_template('sifre_degistir.html')
            
        current_user.set_password(new_pass)
        current_user.needs_password_change = False
        db.session.commit()
        
        if is_forced:
            # Zorunlu şifre değişikliğinde: Başarı mesajını göster ve dashboard'a yönlendir
            flash('Şifreniz başarıyla güncellendi. Artık sistemi kullanabilirsiniz.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            # Profil sayfasından yapılan değişiklikte
            flash('Şifreniz başarıyla güncellendi.', 'success')
            return redirect(url_for('main.profil'))
        
    return render_template('sifre_degistir.html')

@auth_bp.route('/logout')
@login_required
def logout():
    import os
    logout_user()
    portal_url = os.getenv('PORTAL_URL', 'http://localhost:5000/')
    return redirect(portal_url)
