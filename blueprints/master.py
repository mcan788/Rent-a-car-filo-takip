import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, current_app
from flask_login import login_required, current_user
from extensions import db, create_tenant_database
from models import Company, User, Vehicle, Rental, AuditLog, SupportTicket, SupportTicketMessage
from utils.helpers import log_action
from datetime import datetime, timedelta, timezone
import secrets

BLOCKED_DOMAINS = [
    'mailinator.com', 'guerrillamail.com', '10minutemail.com', 'yopmail.com', 
    'temp-mail.org', 'trashmail.com', 'emailondeck.com', 'fakeinbox.com', 
    'maildrop.cc', 'tempemail.cc', 'throwaway.email', 'tempail.com', 
    'dispostable.com', 'sharklasers.com', 'grr.la', 'mailnesia.com', 
    'getnada.com', 'mohmal.com', 'tempinbox.com', 'mailtemp.com',
    'tempmail.net', 'temp-mail.io', 'dropmail.me', 'instaddr.com'
]

def is_temp_mail(email):
    if not email:
        return False
    parts = email.split('@')
    if len(parts) < 2:
        return False
    domain = parts[1].strip().lower()
    return domain in BLOCKED_DOMAINS



master_bp = Blueprint('master', __name__)

@master_bp.route('/master/company/detail/<int:id>')
@login_required
def master_company_detail(id):
    if current_user.company_id != 1:
        flash('Bu işlem için Süper Admin yetkisi gereklidir.', 'error')
        return redirect(url_for('main.dashboard'))
    if not current_user.get_permissions().get('company_manage', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
        
    company = db.session.get(Company, id)
    if not company:
        flash('Şirket bulunamadı.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Tenant DB'den istatistik çek
    vehicle_count = 0
    rental_count = 0
    try:
        from extensions import get_tenant_session
        ts = get_tenant_session(company.subdomain)
        vehicle_count = ts.query(Vehicle).count()
        rental_count = ts.query(Rental).count()
        ts.close()
    except Exception as e:
        print(f"[MASTER] Tenant DB erişim hatası ({company.subdomain}): {e}")
    
    manager = User.query.filter_by(company_id=company.id, role_id=21).first()
    
    return render_template('master_company_detail.html', 
        company=company, 
        vehicle_count=vehicle_count, 
        rental_count=rental_count,
        manager=manager)

@master_bp.route('/master/company/update/<int:id>', methods=['POST'])
@login_required
def master_company_update(id):
    if current_user.company_id != 1:
        flash('Bu işlem için Süper Admin yetkisi gereklidir.', 'error')
        return redirect(url_for('main.dashboard'))
    if not current_user.get_permissions().get('company_manage', {}).get('actions', {}).get('edit') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('master.master_company_detail', id=id))
        
    company = db.session.get(Company, id)
    if not company:
        flash('Şirket bulunamadı.', 'error')
        return redirect(url_for('main.dashboard'))
        
    email = request.form.get('email', '').strip()
    if email and is_temp_mail(email):
        flash('Geçici e-posta adresleri kullanılamaz. Lütfen kurumsal veya kişisel bir e-posta girin.', 'error')
        return redirect(url_for('master.master_company_detail', id=id))

    company.name = request.form.get('name')
    company.contact_phone = request.form.get('phone')
    company.contact_email = email
    company.is_active = 'is_active' in request.form
    company.tax_no = request.form.get('tax_no')
    
    price_str = request.form.get('license_price', '0')
    try:
        company.license_price = float(price_str)
    except ValueError:
        company.license_price = 0.0
        
    if not company.license_key:
        company.license_key = f"RNT-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    
    expires_str = request.form.get('license_expires_at')
    company.license_expires_at = datetime.strptime(expires_str, '%Y-%m-%d') if expires_str else None
        
    db.session.commit()
    log_action(current_user, 'master_company_update', f'Şirket güncellendi: {company.name}')
    flash(f'{company.name} bilgileri başarıyla güncellendi.', 'success')
    return redirect(url_for('master.master_company_detail', id=id))

@master_bp.route('/master/company/add', methods=['POST'])
@login_required
def master_company_add():
    if current_user.company_id != 1:
        flash('Bu işlem için Süper Admin yetkisi gereklidir.', 'error')
        return redirect(url_for('main.dashboard'))
    if not current_user.get_permissions().get('company_manage', {}).get('actions', {}).get('add') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
        
    name = request.form.get('name', '').strip()
    raw_subdomain = request.form.get('subdomain', '').strip()
    from utils.helpers import slugify_subdomain
    
    if not name:
        flash('Şirket ismi zorunludur.', 'error')
        return redirect(url_for('main.dashboard'))
        
    if not raw_subdomain:
        base_sub = slugify_subdomain(name)
        if not base_sub:
            base_sub = "sirket"
        subdomain = base_sub
        counter = 1
        while Company.query.filter_by(subdomain=subdomain).first():
            subdomain = f"{base_sub}{counter}"
            counter += 1
    else:
        subdomain = slugify_subdomain(raw_subdomain)
        if Company.query.filter_by(subdomain=subdomain).first():
            flash('Bu subdomain zaten kullanımda.', 'error')
            return redirect(url_for('main.dashboard'))

    phone = request.form.get('phone')
    email = request.form.get('email', '').strip()
    price_str = request.form.get('license_price', '0')
    expires = request.form.get('expires')
    tax_no = request.form.get('tax_no')
    
    if email and is_temp_mail(email):
        flash('Geçici e-posta adresleri kullanılamaz. Lütfen kurumsal veya kişisel bir e-posta girin.', 'error')
        return redirect(url_for('main.dashboard'))
        
    expires_dt = datetime.strptime(expires, '%Y-%m-%d') if expires else None
    
    try:
        price = float(price_str)
    except ValueError:
        price = 0.0

    license_key = f"RNT-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"

    # 1. Master DB'ye şirket kaydını ekle
    new_company = Company(
        name=name,
        subdomain=subdomain,
        contact_phone=phone,
        contact_email=email,
        license_key=license_key,
        license_price=price,
        license_expires_at=expires_dt,
        tax_no=tax_no
    )
    db.session.add(new_company)
    db.session.flush()
    
    # 2. Şirket için ayrı bir veritabanı oluştur
    try:
        db_name = create_tenant_database(subdomain)
        print(f"[MASTER] Tenant DB olusturuldu: {db_name}")
    except Exception as e:
        db.session.rollback()
        flash(f'Veritabanı oluşturulurken hata: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    
    # 3. Şirket yöneticisi hesabını oluştur
    admin_username = request.form.get('admin_username', '').strip()
    if not admin_username:
        admin_username = subdomain
        
    import string
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    admin_password = ''.join(secrets.choice(alphabet) for i in range(12))
    
    company_admin = User(
        company_id=new_company.id,
        username=admin_username,
        name=f"{name} Admin",
        role='yonetici',
        role_id=21,
        email=email,
        company_name=name,
        needs_password_change=True
    )
    company_admin.set_password(admin_password)
    db.session.add(company_admin)
    db.session.commit()
    
    log_action(current_user, 'master_company_add', f'Yeni şirket, veritabanı ve yönetici eklendi: {name} ({admin_username}) -> DB: {subdomain}')
    import json
    flash(json.dumps({
        'companyName': name,
        'subdomain': subdomain,
        'adminUser': admin_username,
        'adminPass': admin_password,
        'licenseKey': license_key
    }), 'modal_success')
    return redirect(url_for('main.dashboard'))

@master_bp.route('/master/security')
@login_required
def master_security():
    if current_user.company_id != 1:
        return "Yetkisiz Erişim", 403
    if not current_user.get_permissions().get('security_manage', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
        
    import psutil
    import time
    from sqlalchemy import text
    
    # CPU ve RAM (Sunucu Yükü)
    cpu_usage = psutil.cpu_percent(interval=0.1)
    memory_info = psutil.virtual_memory()
    ram_usage = memory_info.percent
    
    # DB Sağlığı (Basit bir ping süresi)
    try:
        start_time = time.time()
        db.session.execute(text('SELECT 1'))
        latency = (time.time() - start_time) * 1000  # ms cinsinden
        db_health = max(0, 100 - (latency / 10)) # Basit bir metrik: 1000ms gecikme = %0 sağlık
        if db_health > 100: db_health = 100
    except Exception as e:
        db_health = 0
        latency = 999
        
    db_health = round(db_health, 1)
    
    # Hatalı/Başarısız Giriş Denemeleri (Son 24 saat, AuditLog üzerinden)
    twenty_four_hours_ago = datetime.now() - timedelta(days=1)
    failed_logins = AuditLog.query.filter(
        AuditLog.action == 'failed_login',
        AuditLog.timestamp >= twenty_four_hours_ago
    ).count()

    stats = {
        'cpu_usage': cpu_usage,
        'ram_usage': ram_usage,
        'db_health': db_health,
        'db_latency': round(latency, 2),
        'failed_logins_24h': failed_logins,
        'total_memory_gb': round(memory_info.total / (1024**3), 1)
    }
        
    return render_template('master_security.html', active_page='master_security', now=datetime.now(), stats=stats)

@master_bp.route('/master/company/toggle/<id>', methods=['POST'])
@login_required
def master_company_toggle(id):
    if current_user.company_id != 1:
        return "Yetkisiz Erişim", 403
    if not current_user.get_permissions().get('company_manage', {}).get('actions', {}).get('suspend') and not current_user.is_manager:
        return "Yetkisiz Erişim", 403
    company = db.session.get(Company, int(id))
    if not company:
        return "Şirket bulunamadı", 404
    if company.id == 1:
        flash('Merkez şirket pasif yapılamaz.', 'error')
    else:
        company.is_active = not company.is_active
        db.session.commit()
        log_action(current_user, 'master_company_toggle', f'Şirket durumu değiştirildi: {company.name} (Aktif: {company.is_active})')
        flash(f'{company.name} durumu güncellendi.', 'success')
    return redirect(url_for('main.dashboard'))

@master_bp.route('/master/user/reset_password/<id>', methods=['POST'])
@login_required
def master_user_reset_password(id):
    if current_user.company_id != 1:
        return "Yetkisiz Erişim", 403
    if not current_user.get_permissions().get('security_manage', {}).get('all') and not current_user.is_manager:
        return "Yetkisiz Erişim", 403
        
    user = db.session.get(User, id)
    if not user:
        return "Kullanıcı bulunamadı", 404
    user.set_password('123456')
    user.needs_password_change = True
    db.session.commit()
    
    log_action(current_user, 'master_user_password_reset', f'Kullanıcı şifresi sıfırlandı: {user.username}')
    flash(f'{user.username} kullanıcısının şifresi başarıyla 123456 olarak sıfırlandı.', 'success')
    return redirect(url_for('main.dashboard'))

@master_bp.route('/master/company/delete/<int:id>', methods=['POST'])
@login_required
def master_company_delete(id):
    if current_user.company_id != 1:
        return "Yetkisiz Erişim", 403
    if not current_user.get_permissions().get('company_manage', {}).get('actions', {}).get('delete') and not current_user.is_manager:
        return "Yetkisiz Erişim", 403
        
    company = db.session.get(Company, id)
    if not company:
        flash('Şirket bulunamadı.', 'error')
        return redirect(url_for('main.dashboard'))
        
    if company.id == 1:
        flash('Merkez şirket silinemez.', 'error')
        return redirect(url_for('main.dashboard'))
        
    company_name = company.name
    subdomain = company.subdomain
    
    # Kritik sistem veritabanlarının silinmesini engelle
    if subdomain.lower() in ['master', 'zyronova_master', 'msdb', 'tempdb', 'model', 'www']:
        flash('Kritik sistem veritabanları silinemez!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # 1. Şirkete ait fiziksel veritabanını SQL Server'dan sil
    try:
        from sqlalchemy import create_engine, text
        import re
        # Subdomain güvenlik doğrulaması (SQL Injection önleme)
        if not re.match(r'^[a-zA-Z0-9_]+$', subdomain):
            flash('Geçersiz subdomain adı.', 'error')
            return redirect(url_for('main.dashboard'))
            
        master_url = current_app.config['SQLALCHEMY_DATABASE_URI']
        temp_engine = create_engine(master_url, isolation_level="AUTOCOMMIT")
        with temp_engine.connect() as conn:
            # Önce DB varlığını parametrik sorgu ile doğrula
            result = conn.execute(text("SELECT DB_ID(:db_name)"), {"db_name": subdomain})
            if result.scalar() is not None:
                # Whitelist'ten geçen subdomain ile güvenli DROP
                conn.execute(text(f"""
                    USE master;
                    ALTER DATABASE [{subdomain}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
                    DROP DATABASE [{subdomain}];
                """))
        temp_engine.dispose()
        print(f"[MASTER] Veritabani fiziksel olarak silindi: {subdomain}")
    except Exception as e:
        print(f"[MASTER] Veritabani silinirken hata: {e}")

    # 2. Şirkete ait tüm verileri temizle (AuditLog -> User -> Company)
    try:
        user_ids = [u.id for u in User.query.filter_by(company_id=id).all()]
        if user_ids:
            AuditLog.query.filter(AuditLog.user_id.in_(user_ids)).delete(synchronize_session=False)
        AuditLog.query.filter_by(company_id=id).delete(synchronize_session=False)
        User.query.filter_by(company_id=id).delete(synchronize_session=False)
        db.session.delete(company)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[MASTER] DB silme hatası: {e}")
        flash(f'Veritabanı kayıtları silinirken hata oluştu: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))
    
    log_action(current_user, 'master_company_delete', f'Şirket kalıcı olarak silindi: {company_name} (ID: {id})')
    flash(f'{company_name} şirketi ve bağlı tüm kullanıcılar başarıyla silindi.', 'success')
    return redirect(url_for('main.dashboard'))

@master_bp.route('/master/support')
@login_required
def master_support():
    if current_user.company_id != 1:
        return "Yetkisiz Erişim", 403
    if not current_user.get_permissions().get('support_access', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
        
    tickets = SupportTicket.query.order_by(SupportTicket.updated_at.desc()).all()
    return render_template('master_support.html', active_page='master_support', tickets=tickets)

@master_bp.route('/master/support/<ticket_id>/reply', methods=['POST'])
@login_required
def master_support_reply(ticket_id):
    if current_user.company_id != 1:
        return "Yetkisiz Erişim", 403
    if not current_user.get_permissions().get('support_access', {}).get('all') and not current_user.is_manager:
        return "Yetkisiz Erişim", 403
        
    ticket = SupportTicket.query.get_or_404(ticket_id)
    message = request.form.get('message')
    status = request.form.get('status')
    
    attachment_path = None
    if 'attachment' in request.files:
        from werkzeug.utils import secure_filename
        file = request.files['attachment']
        if file and file.filename:
            filename = secure_filename(f"master_{ticket.id}_{file.filename}")
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'support')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            attachment_path = f"/static/uploads/support/{filename}"
            
    if message:
        msg = SupportTicketMessage(
            id=str(uuid.uuid4()),
            ticket_id=ticket.id,
            sender_id=current_user.id,
            message=message,
            is_master=True,
            attachment_path=attachment_path
        )
        db.session.add(msg)
    
    if status:
        ticket.status = status
        
    ticket.updated_at = datetime.now()
    db.session.commit()
    flash('Yanıt başarıyla gönderildi.', 'success')
    return redirect(url_for('master.master_support'))

@master_bp.route('/master/support/<ticket_id>/delete', methods=['POST'])
@login_required
def master_support_delete(ticket_id):
    if current_user.company_id != 1:
        return "Yetkisiz Erişim", 403
    if not current_user.get_permissions().get('support_access', {}).get('all') and not current_user.is_manager:
        return "Yetkisiz Erişim", 403
        
    ticket = SupportTicket.query.get_or_404(ticket_id)
    # First delete all messages
    SupportTicketMessage.query.filter_by(ticket_id=ticket.id).delete()
    # Then delete the ticket
    db.session.delete(ticket)
    db.session.commit()
    
    flash('Destek talebi başarıyla silindi.', 'success')
    return redirect(url_for('master.master_support'))

@master_bp.route('/ai-settings', methods=['GET', 'POST'])
@login_required
def master_ai_settings():
    if current_user.company_id != 1:
        flash('Yetkisiz işlem!', 'danger')
        return redirect(url_for('main.dashboard'))
    if not current_user.get_permissions().get('system_settings', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
    
    import json
    import os
    import subprocess
    
    config_file_path = r'C:\SUNUCU_PAKETI\ai_config.json'
    
    # Varsayılan ayarlar
    default_config = {
        "rules": "1- KABİS entegrasyonu kodlarda olsa bile şu an pasif durumdadır. KABİS'ten HİÇBİR ŞEKİLDE bahsetme, listeye ekleme.\n2- Hasar takip sistemi kodlarda geniş görünse bile, müşteriye sadece şunları anlat: \"Araçta hasar var/yok durumu, açıklaması ve hasar türü (hafif, orta, ağır) kaydedilir.\"\n3- Lokasyon (enlem/boylam) verileri arka planda tutulsa bile bunları müşteriye \"araç lokasyonunu GPS ile canlı takip edebilirsiniz\" şeklinde YANLIŞ lanse etme.",
        "rules": "1- KABİS entegrasyonu kodlarda olsa bile şu an pasif durumdadır. KABİS'ten HİÇBİR ŞEKİLDE bahsetme, listeye ekleme.\n2- Hasar takip sistemi kodlarda geniş görünse bile, müşteriye sadece şunları anlat: \"Araçta hasar var/yok durumu, açıklaması ve hasar türü (hafif, orta, ağır) kaydedilir.\"\n3- Lokasyon (enlem/boylam) verileri arka planda tutulsa bile bunları müşteriye \"araç lokasyonunu GPS ile canlı takip edebilirsiniz\" şeklinde YANLIŞ lanse etme.",
        "model": "gemini-3.5-flash",
        "cron_interval": "0 */2 * * *",
        "openai_api_key": "",
        "anthropic_api_key": "",
        "is_active": True
    }
    
    # Eğer eski kurallar dosyası varsa ve json yoksa geçiş yap
    if not os.path.exists(config_file_path):
        legacy_rules_path = r'C:\SUNUCU_PAKETI\ai_custom_rules.txt'
        if os.path.exists(legacy_rules_path):
            with open(legacy_rules_path, 'r', encoding='utf-8') as f:
                default_config["rules"] = f.read()
        try:
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)
        except:
            pass

    # Mevcut configi oku
    current_config = default_config.copy()
    try:
        with open(config_file_path, 'r', encoding='utf-8') as f:
            current_config.update(json.load(f))
    except Exception:
        pass

    if request.method == 'POST':
        new_rules = request.form.get('ai_rules', '')
        new_model = request.form.get('ai_model', 'gemini-3.5-flash')
        new_interval = request.form.get('cron_interval', '0 */2 * * *')
        new_openai = request.form.get('openai_api_key', '')
        new_anthropic = request.form.get('anthropic_api_key', '')
        new_is_active = request.form.get('is_active') == 'true'
        
        old_interval = current_config.get("cron_interval", "0 */2 * * *")
        
        current_config["rules"] = new_rules
        current_config["model"] = new_model
        current_config["cron_interval"] = new_interval
        current_config["is_active"] = new_is_active
        
        # Sadece girildiyse güncelle (boş gönderilirse mevcut olan kalsın, şifre gizleme mantığı için)
        if new_openai.strip() != "":
            current_config["openai_api_key"] = new_openai.strip()
        if new_anthropic.strip() != "":
            current_config["anthropic_api_key"] = new_anthropic.strip()
            
        try:
            with open(config_file_path, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False, indent=4)
            flash('Yapay Zeka ayarları başarıyla güncellendi.', 'success')
            
            # Eğer cron değiştiyse PM2 servisini yeniden oluştur
            if new_interval != old_interval:
                subprocess.Popen(['pm2', 'delete', 'ai-scanner'], cwd=r'C:\SUNUCU_PAKETI', shell=True).wait()
                subprocess.Popen(['pm2', 'start', 'C:\\SUNUCU_PAKETI\\ai_feature_scanner.py', '--name', 'ai-scanner', '--interpreter', 'python', '--no-autorestart', '--cron', new_interval], cwd=r'C:\SUNUCU_PAKETI', shell=True).wait()
                flash('Otonom tarama süresi güncellendi.', 'success')
            else:
                # Sadece yeniden başlat (anında tarama için)
                subprocess.Popen(['pm2', 'restart', 'ai-scanner'], cwd=r'C:\SUNUCU_PAKETI', shell=True)
                
        except Exception as e:
            flash(f'Hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('master.master_ai_settings'))
        
    return render_template('master_ai_settings.html', active_page='master_ai_settings', config=current_config)

@master_bp.route('/master/hukuki-ispat', methods=['GET', 'POST'])
@login_required
def hukuki_ispat():
    if current_user.company_id != 1:
        flash('Bu işlem için Süper Admin yetkisi gereklidir.', 'error')
        return redirect(url_for('main.dashboard'))
    if not current_user.get_permissions().get('security_manage', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
    
    result_data = None
    searched = False
    
    if request.method == 'POST':
        searched = True
        tc_kimlik = request.form.get('tc_kimlik', '').strip()
        
        if tc_kimlik:
            from extensions import get_tenant_session
            from cryptography.fernet import Fernet
            import json
            import os
            
            key_str = os.getenv('ENCRYPTION_KEY')
            if key_str:
                fernet = Fernet(key_str.encode('utf-8'))
                
                # Tüm aktif bayileri TurMasterDB'den çekip ZYRONOVA_MASTER'a senkronize edelim ki aramada eksik çıkmasın
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
                            cursor.execute("SELECT AgencyName, Username, LicenseKey, LicensePrice, LicenseExpiryDate, OwnerEmail, IsActive FROM Agencies WITH (NOLOCK)")
                            agencies = cursor.fetchall()
                            
                            for row in agencies:
                                aname, ausername, akey, aprice, aexpiry, aemail, aactive = row
                                comp = Company.query.filter_by(subdomain=ausername).first()
                                if not comp:
                                    comp = Company(
                                        name=aname,
                                        subdomain=ausername,
                                        contact_email=aemail,
                                        license_key=akey,
                                        license_price=float(aprice or 0.0),
                                        license_expires_at=aexpiry,
                                        is_active=bool(aactive)
                                    )
                                    db.session.add(comp)
                            db.session.commit()
                except Exception as e:
                    print(f"Hukuki ispat DB sync hatası: {e}")
                    
                companies = Company.query.all()
                
                for comp in companies:
                    ts = None
                    try:
                        ts = get_tenant_session(comp.subdomain)
                        # Fetch rentals with biometric data
                        rentals = ts.query(Rental).filter(Rental.musteri_biyometrik_veri_sifreli != None).order_by(Rental.id.desc()).all()
                        for r in rentals:
                            # Arama kriterini esnetiyoruz (Çoklu arama ve boşluk toleransı)
                            tc_str = str(r.tcKimlik).strip() if r.tcKimlik else ""
                            plaka_str = str(r.plaka).strip().upper() if r.plaka else ""
                            isim_str = str(r.musteriAdi).strip().upper() if r.musteriAdi else ""
                            
                            search_val = tc_kimlik.upper()
                            
                            if (search_val in tc_str) or (search_val in plaka_str) or (search_val in isim_str):
                                try:
                                    cozulmus_veri = fernet.decrypt(r.musteri_biyometrik_veri_sifreli.encode('utf-8')).decode('utf-8')
                                    veri_json = json.loads(cozulmus_veri)
                                    
                                    # Use a master-specific route to view the contract securely
                                    sozlesme_url = url_for('master.master_sozlesme', company_id=comp.id, rental_id=r.id)

                                    result_data = {
                                        'company_name': comp.name,
                                        'rental_id': r.id,
                                        'plaka': r.plaka,
                                        'musteriAdi': r.musteriAdi,
                                        'imzaTarihi': r.imzaTarihi,
                                        'hash_val': r.musteri_biyometrik_hash,
                                        'sifreli_veri': r.musteri_biyometrik_veri_sifreli,
                                        'nokta_sayisi': len(veri_json),
                                        'ornek_noktalar': veri_json[:5],
                                        'sozlesme_url': sozlesme_url
                                    }
                                    break
                                except Exception as e:
                                    print(f"Hukuki ispat şifre çözme hatası: {e}")
                                    flash(f"Kayıt bulundu ancak kriptografik şifresi çözülemiyor: {e}", "warning")
                                    
                        if result_data:
                            break
                            
                        # DIAGNOSTIC: If not found in biometric rentals, check if it exists AT ALL without biometric data
                        if not result_data:
                            all_rentals = ts.query(Rental).order_by(Rental.id.desc()).all()
                            for r in all_rentals:
                                tc_str = str(r.tcKimlik).strip() if r.tcKimlik else ""
                                plaka_str = str(r.plaka).strip().upper() if r.plaka else ""
                                isim_str = str(r.musteriAdi).strip().upper() if r.musteriAdi else ""
                                search_val = tc_kimlik.upper()
                                
                                if (search_val in tc_str) or (search_val in plaka_str) or (search_val in isim_str):
                                    if not r.musteri_biyometrik_veri_sifreli:
                                        flash(f"'{comp.name}' şirketinde kayıt bulundu! Ancak 'musteri_biyometrik_veri_sifreli' alanı BOŞ kaydedilmiş. Lütfen bu kiralamanın imza loglarını kontrol edin.", "error")
                                    break
                    except Exception as e:
                        print(f"Tenant db error in hukuki ispat for {comp.subdomain}: {e}")
                    finally:
                        try:
                            if ts:
                                ts.close()
                        except:
                            pass
                    
                    if result_data:
                        break

    return render_template('master_hukuki_ispat.html', active_page='master_hukuki_ispat', result_data=result_data, searched=searched)

@master_bp.route('/master/sozlesme/<int:company_id>/<string:rental_id>')
@login_required
def master_sozlesme(company_id, rental_id):
    if current_user.company_id != 1:
        flash('Bu işlem için Süper Admin yetkisi gereklidir.', 'error')
        return redirect(url_for('main.dashboard'))
    if not current_user.get_permissions().get('company_manage', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
        
    company = Company.query.get_or_404(company_id)
    
    from extensions import get_tenant_session
    ts = None
    try:
        ts = get_tenant_session(company.subdomain)
        rental = ts.query(Rental).filter_by(id=rental_id).first()
        if not rental:
            flash('Kiralama kaydı bulunamadı.', 'error')
            return redirect(url_for('master.hukuki_ispat'))
            
        return render_template('sozlesme.html', rental=rental, company=company)
    except Exception as e:
        flash(f'Hata: {e}', 'error')
        return redirect(url_for('master.hukuki_ispat'))
    finally:
        if ts:
            try:
                ts.close()
            except:
                pass
