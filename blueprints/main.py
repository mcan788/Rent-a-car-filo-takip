import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, g, session, jsonify, current_app
from flask_login import login_required, current_user
from extensions import db, csrf
from models import Vehicle, Rental, Company, AuditLog, User
from utils.helpers import safe_int, safe_float, log_action
from utils.stats import (get_currency_totals, get_monthly_data, get_top_10_details, 
                         get_hasar_distribution, get_durum_distribution, get_arac_gelir, get_period_stats)
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@main_bp.route('/dashboard')
def dashboard():
    print(f"[DEBUG DASHBOARD] Hit /dashboard. Session: {dict(session)}", flush=True)
    if not current_user.is_authenticated:
        print("[DEBUG DASHBOARD] User is NOT authenticated! Redirecting to login...", flush=True)
        return redirect(url_for('auth.login'))
        
    print(f"[DEBUG DASHBOARD] User IS authenticated: {current_user.username}, Role ID: {current_user.role_id}", flush=True)

    # STRICT ROUTING BASED ON ROLE ID
    if current_user.company_id == 3:
        portal_url = os.getenv('PORTAL_URL', 'https://zyronova.com/')
        flash("Erişim Reddedildi. Tur Takip kullanıcıları sadece Tur Takip paneline giriş yapabilir.", "error")
        return redirect(portal_url.rstrip('/') + '/agency')

    # Log action
    log_action(current_user, 'login', 'Kullanıcı dashboarda giriş yaptı.')

    if current_user.is_master_user:
        # Master Dashboard Logic (SaaS Yönetim Paneli)
        if not current_user.get_permissions().get('master_dashboard', {}).get('all') and not current_user.is_manager:
            flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
            return redirect(url_for('main.profil'))
            
        companies = Company.query.all()
        now_local = datetime.now()
        thirty_days_later = now_local + timedelta(days=30)
        expiring_soon = Company.query.filter(
            Company.license_expires_at <= thirty_days_later,
            Company.license_expires_at >= now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        return render_template('master_dashboard.html', active_page='master_dashboard', companies=companies, expiring_soon=expiring_soon, now=now_local, perms=current_user.get_permissions())

    if not g.current_company: 
        return "Şirket bulunamadı", 404

    ts = g.tenant_session
    from sqlalchemy.orm import load_only
    vehicles = ts.query(Vehicle).filter_by(is_deleted=False).options(load_only(Vehicle.id)).all() if ts else []
    currency_totals = get_currency_totals()
    hasarli_count = ts.query(func.count(Rental.id)).filter(Rental.hasarDurumu != 'yok').scalar() or 0 if ts else 0
    kirada_count = ts.query(Rental.id).filter_by(alinistaKm=0).count() if ts else 0
    
    revenue = get_period_stats('toplamFiyat')
    cost = get_period_stats('toplamMaliyet')
    profit = get_period_stats('kar')

    return render_template('dashboard.html', active_page='dashboard',
                           vehicles=vehicles, currency_totals=currency_totals,
                           hasarli_count=hasarli_count, kirada_count=kirada_count,
                           revenue=revenue, cost=cost, profit=profit)

@main_bp.route('/ajax/dashboard/kpi')
@login_required
def api_dashboard_kpi():
    ts = g.tenant_session
    if not ts: return ""
    print(f"[DEBUG KPI] Company: {g.current_company.subdomain}, DB: {ts.bind.url}", flush=True)
    from sqlalchemy.orm import load_only
    vehicles = ts.query(Vehicle).filter_by(is_deleted=False).options(load_only(Vehicle.id)).all()
    currency_totals = get_currency_totals()
    hasarli_count = ts.query(func.count(Rental.id)).filter(Rental.hasarDurumu != 'yok').scalar() or 0
    kirada_count = ts.query(Rental.id).filter_by(alinistaKm=0).count()
    return render_template('partials/_dashboard_kpi.html', vehicles=vehicles, hasarli_count=hasarli_count, kirada_count=kirada_count, currency_totals=currency_totals)

@main_bp.route('/ajax/dashboard/periods')
@login_required
def api_dashboard_periods():
    ts = g.tenant_session
    if not ts: return ""
    revenue = get_period_stats('toplamFiyat')
    cost = get_period_stats('toplamMaliyet')
    profit = get_period_stats('kar')
    return render_template('partials/_dashboard_periods.html', revenue=revenue, cost=cost, profit=profit)

@main_bp.route('/ajax/dashboard/charts')
@login_required
def api_dashboard_charts():
    ts = g.tenant_session
    if not ts: return ""
    arac_gelir = get_arac_gelir()
    hasar_dist = get_hasar_distribution()
    durum_dist = get_durum_distribution()
    return render_template('partials/_dashboard_charts.html', arac_gelir=arac_gelir, hasar_dist=hasar_dist, durum_dist=durum_dist)

@main_bp.route('/ajax/dashboard/recent')
@login_required
def api_dashboard_recent():
    ts = g.tenant_session
    if not ts: return ""
    son_kiralamalar = ts.query(Rental).order_by(Rental.baslangicTarihi.desc()).limit(10).all()
    from utils.helpers import get_vehicle_by_plaka
    return render_template('partials/_dashboard_recent.html', son_kiralamalar=son_kiralamalar, get_vehicle_by_plaka=get_vehicle_by_plaka, HASAR_LABELS={'yok': 'Hasarsız', 'hafif': 'Hafif', 'orta': 'Orta', 'agir': 'Ağır'})

@main_bp.route('/ajax/dashboard/vehicles')
@login_required
def api_dashboard_vehicles():
    ts = g.tenant_session
    if not ts: return ""
    top_10_details = get_top_10_details()
    return render_template('_vehicle_tabs.html', top_10_details=top_10_details)

@main_bp.route('/profil', methods=['GET', 'POST'])
@login_required
def profil():
    if request.method == 'POST':
        current_user.name = request.form.get('name')
        current_user.surname = request.form.get('surname')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        db.session.commit()
        flash('Profil bilgileriniz güncellendi.', 'success')
        return redirect(url_for('main.profil'))
    
    # Personel listesini çek (Sadece Admin/Yönetici görebilir)
    users = []
    if current_user.is_manager or current_user.can_manage_personnel:
        users = User.query.filter_by(company_id=g.current_company.id, is_deleted=False).all()
        
    # Denetim Günlüğü (Son 100 işlem)
    logs = []
    if current_user.is_manager:
        logs = AuditLog.query.filter_by(company_id=g.current_company.id).order_by(AuditLog.timestamp.desc()).limit(100).all()

    return render_template('profil.html', 
                           active_page='profil', 
                           users=users, 
                           logs=logs,
                           is_admin=(current_user.is_manager or current_user.can_manage_personnel))

@main_bp.route('/personel/ekle', methods=['POST'])
@login_required
def personel_ekle():
    if not current_user.is_manager and not current_user.can_manage_personnel:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.profil'))
        
    username = request.form.get('username')
    password = request.form.get('password')
    name = request.form.get('name')
    role_id = int(request.form.get('role_id', 22))
    
    company_id = int(request.form.get('company_id', g.current_company.id))
    
    if current_user.company_id == 1 and company_id == 3:
        if not current_user.get_permissions().get('tur_takip_manage', {}).get('all') and not current_user.is_manager:
            flash('Tur Takip departmanına kullanıcı ekleme yetkiniz yok.', 'error')
            return redirect(url_for('main.profil'))
            
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
            print(f"[SSO SYNC HATA] Personel TurMasterDB'ye aktarılamadı: {e}", flush=True)
    
    log_action(current_user, 'personnel_add', f'Yeni personel eklendi: {username}')
    flash('Personel başarıyla eklendi.', 'success')
    return redirect(url_for('main.profil'))

@main_bp.route('/personel/sil/<id>', methods=['POST'])
@login_required
def personel_sil(id):
    if not current_user.is_manager and not current_user.can_manage_personnel:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.profil'))
        
    user = User.query.filter_by(id=id, company_id=g.current_company.id).first_or_404()
    if user.id == current_user.id:
        flash('Kendi hesabınızı silemezsiniz.', 'error')
        return redirect(url_for('main.profil'))
        
    user.is_deleted = True
    user.deleted_at = datetime.now()
    user.deleted_by_id = current_user.id
    db.session.commit()
    
    log_action(current_user, 'personnel_delete', f'Personel silindi: {user.username}')
    flash('Personel başarıyla silindi.', 'success')
    return redirect(url_for('main.profil'))

@main_bp.route('/personel/sifre_sifirla/<id>', methods=['POST'])
@login_required
def personel_sifre_sifirla(id):
    if not current_user.is_manager and not current_user.can_manage_personnel:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.profil'))
        
    user = User.query.filter_by(id=id, company_id=g.current_company.id).first_or_404()
    new_password = request.form.get('new_password')
    
    if not new_password:
        flash('Lütfen yeni bir şifre girin.', 'error')
        return redirect(url_for('main.profil'))
        
    user.set_password(new_password)
    user.needs_password_change = True
    db.session.commit()
    
    log_action(current_user, 'personnel_password_reset', f'Personel şifresi sıfırlandı: {user.username}')
    flash(f'{user.username} kullanıcısının şifresi başarıyla güncellendi.', 'success')
    return redirect(url_for('main.profil'))

@main_bp.route('/personel/yetki/<id>', methods=['POST'])
@login_required
def personel_yetki_guncelle(id):
    if not current_user.is_manager and not current_user.can_manage_personnel:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.profil'))
        
    user = User.query.filter_by(id=id, company_id=g.current_company.id).first_or_404()
    import json
    perms = {}
    if user.is_master_user:
        perms = {
            "master_dashboard": {"all": 'p_master_dashboard_all' in request.form, "actions": request.form.getlist('p_master_dashboard_actions')},
            "company_manage": {"all": 'p_company_manage_all' in request.form, "actions": request.form.getlist('p_company_manage_actions')},
            "security_manage": {"all": 'p_security_manage_all' in request.form, "actions": request.form.getlist('p_security_manage_actions')},
            "system_logs": {"all": 'p_system_logs_all' in request.form, "actions": request.form.getlist('p_system_logs_actions')},
            "system_settings": {"all": 'p_system_settings_all' in request.form, "actions": request.form.getlist('p_system_settings_actions')},
            "support_access": {"all": 'p_support_access_all' in request.form, "actions": request.form.getlist('p_support_access_actions')},
            "tur_takip_manage": {"all": 'p_tur_takip_manage_all' in request.form, "actions": []}
        }
    else:
        perms = {
            "dashboard": {"all": 'p_dash_all' in request.form, "cards": request.form.getlist('p_dash_cards')},
            "araclar": {"all": 'p_arac_all' in request.form, "actions": request.form.getlist('p_arac_actions')},
            "kiralamalar": {"all": 'p_kira_all' in request.form, "actions": request.form.getlist('p_kira_actions')},
            "ciro_analiz": {"all": 'p_ciro_analiz_all' in request.form},
            "rapor": {"all": 'p_rapor_all' in request.form},
            "servis": {"all": 'p_servis_all' in request.form},
            "excel": {"all": 'p_excel_all' in request.form},
            "logs": {"all": 'p_logs_all' in request.form},
            "ayarlar": {"all": 'p_ayarlar_all' in request.form}
        }
    user.permissions_json = json.dumps(perms)
    user.can_manage_personnel = 'can_manage_personnel' in request.form
    db.session.commit()
    
    log_action(current_user, 'personnel_perms_update', f'Personel yetkileri güncellendi: {user.username}')
    flash('Yetkiler başarıyla güncellendi.', 'success')
    return redirect(url_for('main.profil'))

@main_bp.route('/ciro_analiz')
@login_required
def ciro_analiz():
    if not current_user.get_permissions().get('ciro_analiz', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
        
    if not g.current_company: return redirect(url_for('main.dashboard'))
    
    ts = g.tenant_session
    if not ts:
        return redirect(url_for('main.dashboard'))
    
    currency_totals = get_currency_totals()
    monthly_data = get_monthly_data()
    top_10_details = get_top_10_details()
    return render_template('ciro_analiz.html',
        active_page='ciro_analiz',
        currency_totals=currency_totals,
        kiralama_sayisi=ts.query(Rental).count(),
        arac_sayisi=ts.query(Vehicle).count(),
        monthly_data=monthly_data,
        top_10_details=top_10_details
    )

@main_bp.route('/logs')
@login_required
def logs():
    is_master = current_user.is_master_user
    perm_key = 'system_logs' if is_master else 'logs'
    if not current_user.get_permissions().get(perm_key, {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
    if not g.current_company: return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    query = AuditLog.query.filter_by(company_id=g.current_company.id).order_by(AuditLog.timestamp.desc())
    total = query.count()
    pages = (total + per_page - 1) // per_page
    offset = (page - 1) * per_page
    logs = query.offset(offset).limit(per_page).all()
    has_prev = page > 1
    has_next = page < pages
    
    return render_template('logs.html', 
                           active_page='logs', 
                           logs=logs,
                           page=page,
                           pages=pages,
                           total=total,
                           has_prev=has_prev,
                           has_next=has_next)

@main_bp.route('/ayarlar')
@login_required
def ayarlar():
    if not current_user.get_permissions().get('ayarlar', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfa için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('ayarlar.html', active_page='ayarlar')

@main_bp.route('/ayarlar/kabis', methods=['POST'])
@login_required
def update_kabis_settings():
    if not current_user.get_permissions().get('ayarlar', {}).get('all') and not current_user.is_manager:
        flash('Yetkisiz erişim.', 'error')
        return redirect(url_for('main.dashboard'))
        
    company = g.current_company
    
    # Vergi No
    tax_no = request.form.get('tax_no')
    if tax_no is not None:
        tax_no = ''.join(c for c in tax_no if c.isdigit())
        if len(tax_no) > 20:
            flash('Vergi numarası çok uzun.', 'error')
            return redirect(url_for('main.ayarlar'))
        company.tax_no = tax_no
    
    # KABİS Web Servis Kimlik Bilgileri
    kabis_username = request.form.get('kabis_username', '').strip()
    kabis_password = request.form.get('kabis_password', '').strip()
    kabis_sirket_kodu = request.form.get('kabis_sirket_kodu', '').strip()
    
    if kabis_username:
        company.kabis_username = kabis_username
    if kabis_password:  # Boş bırakılırsa mevcut şifre korunur
        company.kabis_password = kabis_password
    if kabis_sirket_kodu:
        company.kabis_sirket_kodu = kabis_sirket_kodu
    
    db.session.commit()
    log_action(current_user, 'kabis_settings_update', 'KABİS entegrasyon ayarları güncellendi.')
    flash('KABİS Entegrasyon Ayarları başarıyla güncellendi.', 'success')
        
    return redirect(url_for('main.ayarlar'))

@main_bp.route('/ayarlar/sozlesme', methods=['POST'])
@login_required
def update_contract_template():
    if not current_user.get_permissions().get('ayarlar', {}).get('all') and not current_user.is_manager:
        flash('Yetkisiz erişim.', 'error')
        return redirect(url_for('main.dashboard'))
        
    template_text = request.form.get('contract_template')
    if template_text:
        g.current_company.contract_template = template_text.strip()
        db.session.commit()
        log_action(current_user, 'contract_template_update', 'Kiralama sözleşmesi şablonu güncellendi.')
        flash('Sözleşme şablonu başarıyla güncellendi.', 'success')
    else:
        flash('Lütfen boş bir şablon kaydetmeyin.', 'error')
        
    referrer = request.referrer
    if referrer and 'profil' in referrer:
        return redirect(url_for('main.profil') + '?tab=contract')
    return redirect(url_for('main.ayarlar'))

@main_bp.route('/ayarlar/banner', methods=['POST'])
@login_required
def upload_banner():
    if not current_user.get_permissions().get('ayarlar', {}).get('all') and not current_user.is_manager:
        flash('Yetkisiz erişim.', 'error')
        return redirect(url_for('main.dashboard'))
        
    file = request.files.get('banner')
    if file:
        from utils.helpers import allowed_file, is_allowed_image
        if not allowed_file(file.filename) or not is_allowed_image(file):
            flash('Geçersiz dosya. Sadece gerçek JPG ve PNG resimleri yüklenebilir.', 'error')
            return redirect(url_for('main.ayarlar'))
            
        # Boyut kontrolü (Maks 2MB)
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > 2 * 1024 * 1024:
            flash('Dosya boyutu çok büyük. Maksimum 2MB yükleyebilirsiniz.', 'error')
            return redirect(url_for('main.ayarlar'))

        from werkzeug.utils import secure_filename
        # Şirkete özel klasör oluştur
        upload_path = os.path.join(current_app.static_folder, 'uploads', str(g.current_company.id))
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
            
        file.save(os.path.join(upload_path, 'hero.jpg'))
        flash('Banner başarıyla güncellendi.', 'success')
        
    return redirect(url_for('main.ayarlar'))

@main_bp.route('/dismiss_alert', methods=['POST'])
@login_required
@csrf.exempt
def dismiss_alert():
    try:
        data = request.get_json()
        alert_type = data.get('alert_type')
        target_id = data.get('target_id')
        state_value = data.get('state_value')
        
        ts = g.tenant_session
        if ts:
            from models import DismissedAlert
            target_id_str = str(target_id)
            exists = ts.query(DismissedAlert).filter_by(
                user_id=current_user.username,
                alert_type=alert_type,
                target_id=target_id_str
            ).first()
            if not exists:
                d = DismissedAlert(
                    user_id=current_user.username,
                    alert_type=alert_type,
                    target_id=target_id_str,
                    state_value=state_value or 'dismissed'
                )
                ts.add(d)
                ts.commit()
                
        return jsonify({'status': 'ok'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        if g.tenant_session:
            g.tenant_session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@main_bp.route('/clear_all_alerts', methods=['POST'])
@login_required
@csrf.exempt
def clear_all_alerts():
    print("CLEAR ALL ALERTS ACCESSED")
    try:
        ts = g.tenant_session
        if ts:
            from models import Vehicle, Rental, DismissedAlert
            from datetime import datetime, timedelta
            
            # Helper function to add to DB if not exists
            def dismiss_in_db(a_type, t_id):
                t_id_str = str(t_id)
                exists = ts.query(DismissedAlert).filter_by(
                    user_id=current_user.username,
                    alert_type=a_type,
                    target_id=t_id_str
                ).first()
                if not exists:
                    d = DismissedAlert(
                        user_id=current_user.username,
                        alert_type=a_type,
                        target_id=t_id_str,
                        state_value='cleared'
                    )
                    ts.add(d)

            # 1. Maintenance
            m_alerts = ts.query(Vehicle).filter(
                Vehicle.guncelKm >= Vehicle.bakimYapildigiKm + 10000,
                Vehicle.is_deleted == False
            ).all()
            for v in m_alerts:
                dismiss_in_db('maintenance', v.id)
                
            # 2. Insurance
            alert_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
            ins_alerts = ts.query(Vehicle).filter(
                Vehicle.sigortaBitisTarihi <= alert_date,
                Vehicle.is_deleted == False
            ).all()
            for v in ins_alerts:
                dismiss_in_db('insurance', v.id)
                
            # 3. Inspection (Vize)
            insp_alerts = ts.query(Vehicle).filter(
                Vehicle.vizeBitisTarihi <= alert_date,
                Vehicle.is_deleted == False
            ).all()
            for v in insp_alerts:
                dismiss_in_db('inspection', v.id)
                
            # 4. Rental Expiration
            today = datetime.now().strftime('%Y-%m-%d')
            now_time = datetime.now().strftime('%H:%M')
            rentals = ts.query(Rental).filter(
                Rental.bitisTarihi <= today,
                Rental.alinistaKm == 0
            ).all()
            for r in rentals:
                if r.bitisTarihi < today or (r.bitisTarihi == today and (r.bitisSaati or '09:00') <= now_time):
                    dismiss_in_db('rental_expiration', r.id)
                    
            ts.commit()
            
        return jsonify({'status': 'success'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        if g.tenant_session:
            g.tenant_session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

@main_bp.route('/kvkk-aydinlatma-metni')
def kvkk_aydinlatma_metni():
    return render_template('kvkk.html')
