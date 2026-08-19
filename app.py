import os
import re
import time
from flask import Flask, render_template, request, redirect, url_for, g, current_app, session, flash
from flask_login import current_user, logout_user
from extensions import db, login_manager, init_extensions, csrf, get_tenant_session
from flask_migrate import Migrate
from utils.helpers import get_real_ip
from config import Config
from models import Company, User, Vehicle, Rental, AuditLog
from datetime import datetime, timedelta
import threading
from logging_config import setup_logging
import logging

# Initialize JSON logging
setup_logging()
logger = logging.getLogger(__name__)

_migration_lock = threading.Lock()
_migrated_tenants = set()

class ForceHTTPSMiddleware(object):
    def __init__(self, app):
        self.app = app
    def __call__(self, environ, start_response):
        # Yerel gelistirme ortaminda (localhost/127.0.0.1) HTTPS zorlamasini devre disi birak
        host = environ.get('HTTP_HOST', '')
        if 'localhost' not in host and '127.0.0.1' not in host:
            environ['wsgi.url_scheme'] = 'https'
            
        # IIS ARR proxy sends client IP in X-Real-Ip (HTTP_X_REAL_IP).
        # Map it to HTTP_X_FORWARDED_FOR so Werkzeug's ProxyFix middleware can parse it.
        if 'HTTP_X_REAL_IP' in environ:
            environ['HTTP_X_FORWARDED_FOR'] = environ['HTTP_X_REAL_IP']
        return self.app(environ, start_response)

def create_app(config_class=Config):
    from werkzeug.middleware.proxy_fix import ProxyFix
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app.wsgi_app = ForceHTTPSMiddleware(app.wsgi_app)
    app.config.from_object(config_class)
    
    # Session Security
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30)
    )

    # Initialize Extensions
    init_extensions(app)
    
    # Initialize Flask-Migrate
    migrate = Migrate(app, db)
    
    # Enable Brotli & Gzip Compression
    try:
        from flask_compress import Compress
        compress = Compress()
        app.config['COMPRESS_ALGORITHM'] = ['br', 'gzip', 'deflate']
        app.config['COMPRESS_LEVEL'] = 6
        compress.init_app(app)
    except ImportError:
        pass

    # Auto-Migrations: Eksik sütunları otomatik ekle (Güvenli - sadece yoksa ekler)
    with app.app_context():
        try:
            from sqlalchemy import text, inspect
            insp = inspect(db.engine)
            if insp.has_table('users'):
                cols = [c['name'] for c in insp.get_columns('users')]
                if 'two_factor_recovery_codes' not in cols:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE users ADD two_factor_recovery_codes NVARCHAR(MAX) NULL"))
                        conn.commit()
                    print("[AUTO-MIGRATION] users.two_factor_recovery_codes sütunu eklendi.", flush=True)
        except Exception as mig_err:
            print(f"[AUTO-MIGRATION] Sütun kontrolü: {mig_err}", flush=True)

    # Register Jinja Filters
    from utils.helpers import format_currency, format_km, format_date, format_number
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['km'] = format_km
    app.jinja_env.filters['fdate'] = format_date
    app.jinja_env.filters['fnum'] = format_number

    # Register Blueprints
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.fleet import fleet_bp
    from blueprints.master import master_bp
    from blueprints.reports import reports_bp
    from blueprints.support import support_bp
    from blueprints.public import public_bp
    from blueprints.ai import ai_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(fleet_bp)
    app.register_blueprint(master_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(support_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(ai_bp)

    # Pre-compiled IP regex (module-level for performance)
    _IP_REGEX = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')

    @app.before_request
    def handle_tenant():
        print(f"[DEBUG REQUEST] {request.method} {request.url} | Args: {dict(request.args)}", flush=True)
        g.start_time = time.perf_counter()
        if request.path.startswith('/static') or request.path.startswith('/py-api'):
            return
            
        host = request.headers.get('X-Forwarded-Host', request.host).split(':')[0]
        # print(f"[DEBUG] [handle_tenant] Incoming request for path: {request.path}, host: {host}", flush=True)
        parts = host.split('.')
        
        g.is_master = False
        g.current_company = None
        g.tenant_session = None
        
        # IP adreslerini (127.0.0.1 gibi) subdomain olarak algılamamak için kontrol
        if _IP_REGEX.match(host):
            subdomain = None
        elif len(parts) > 2:
            subdomain = parts[0]
        elif len(parts) == 2 and parts[1] == 'localhost':
            subdomain = parts[0]
        else:
            subdomain = None
            
        # Single-domain SSO Login Token parse
        if (not subdomain or subdomain == 'www') and request.path.endswith('/sso-login') and 'token' in request.args:
            try:
                import jwt
                token = request.args.get('token')
                secret = os.getenv('JWT_SECRET')
                if not secret:
                    raise Exception("JWT_SECRET is not configured!")
                decoded = jwt.decode(token, secret, algorithms=['HS256'])
                print(f"[SSO DEBUG] Decoded token: {decoded}", flush=True)
                
                if 'targetModule' in decoded and decoded['targetModule'] == 'MASTER':
                    subdomain = 'master'
                elif 'role_id' in decoded and decoded['role_id'] in [11, 12, 13]:
                    subdomain = 'master'
                elif 'role' in decoded and decoded['role'] in ['SUPERADMIN', 'Admin', 'SUPER_ADMIN']:
                    subdomain = 'master'
                elif 'subdomain' in decoded and decoded['subdomain']:
                    subdomain = decoded['subdomain']
                elif 'username' in decoded:
                    subdomain = decoded['username']
            except Exception as e:
                print(f"[SSO Parse Error] {e}")
                
        # Handle Session-stored subdomain for single-domain architecture
        if not subdomain or subdomain == 'www':
            # Emniyet kemeri: session kontrolü
            subdomain = session.get('tenant_subdomain')
            # print(f"[DEBUG SESSION] Path: {request.path}, session dict: {dict(session)}", flush=True)
        
        # Save to session if found from token
        if subdomain and request.path.endswith('/sso-login'):
            session['tenant_subdomain'] = subdomain
        
        # Master/Merkez Tespiti ve Ana Domain Kısıtlaması
        master_subdomains = ['sa', 'master', 'admin', 'www']
        
        # Master Panel'e 'sa' subdomaini, localhost veya ana domainler üzerinden izin ver
        if (subdomain in master_subdomains) or (not subdomain and host in ['localhost', '127.0.0.1', 'zyronova.com', 'zyronova.com.tr']):
            g.is_master = True
            g.current_company = db.session.get(Company, 1)  # ID 1 her zaman Master şirkettir
        else:
            # Müşteri (Tenant) Tespiti
            g.current_company = Company.query.filter_by(subdomain=subdomain).first()
            # print(f"[DEBUG] [handle_tenant] Resolved subdomain: {subdomain}, g.current_company: {g.current_company}", flush=True)
            
        if not g.current_company:
            # GÜVENLİK/FİX: Yeni acente açıldığında henüz senkronize olmamışsa, 
            # /login veya ana sayfa sayfalarına izin verelim ki portal üzerinden sso-login tetiklenebilsin.
            allowed_paths = ['/', '/login', '/sso-login', '/favicon.ico']
            if any(request.path.endswith(p) for p in allowed_paths) or request.path == '/':
                pass # Let the auth handlers process it or redirect to portal
            else:
                return f"Geçersiz Şirket Adresi: {subdomain}", 404
        
        if not g.is_master and g.current_company:
            # Lisans bitiş tarihini kontrol et ve bittiyse otomatik askıya al
            if (g.current_company.is_active 
                    and g.current_company.license_expires_at
                    and g.current_company.license_expires_at.date() < datetime.now().date()):
                g.current_company.is_active = False
                auto_log = AuditLog(
                    company_id=g.current_company.id,
                    action="license_expired_auto_suspend",
                    details=f"Lisans süresi ({g.current_company.license_expires_at.strftime('%d.%m.%Y')}) dolduğu için şirket otomatik olarak askıya alındı.",
                    ip_address=get_real_ip()
                )
                db.session.add(auto_log)
                db.session.commit()

            # Şirket askıdaysa premium 403 sayfasını döndür
            if g.current_company and not g.current_company.is_active:
                html_response = f"""
                <!DOCTYPE html>
                <html lang="tr">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Hesap Askıya Alındı | Zyronova</title>
                    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&display=swap" rel="stylesheet">
                    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
                    <style>
                        :root {{
                            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                            --accent-red: #ef4444;
                            --text-main: #f8fafc;
                            --text-sub: #94a3b8;
                        }}
                        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
                        body {{
                            font-family: 'Outfit', sans-serif;
                            background: var(--bg-gradient);
                            min-height: 100vh;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            padding: 1.5rem;
                            color: var(--text-main);
                            overflow: hidden;
                            position: relative;
                        }}
                        body::before {{
                            content: '';
                            position: absolute;
                            width: 400px; height: 400px;
                            background: radial-gradient(circle, rgba(239, 68, 68, 0.15) 0%, transparent 70%);
                            top: -10%; left: -10%; z-index: 1;
                        }}
                        body::after {{
                            content: '';
                            position: absolute;
                            width: 400px; height: 400px;
                            background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
                            bottom: -10%; right: -10%; z-index: 1;
                        }}
                        .container {{
                            background: rgba(30, 41, 59, 0.7);
                            backdrop-filter: blur(16px);
                            border: 1px solid rgba(255, 255, 255, 0.1);
                            border-radius: 32px;
                            padding: 3rem 2.5rem;
                            max-width: 500px;
                            width: 100%;
                            text-align: center;
                            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                            z-index: 10;
                            animation: floatUp 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
                        }}
                        @keyframes floatUp {{
                            from {{ opacity: 0; transform: translateY(30px); }}
                            to {{ opacity: 1; transform: translateY(0); }}
                        }}
                        .icon-wrapper {{
                            width: 88px; height: 88px;
                            background: rgba(239, 68, 68, 0.15);
                            border: 1px solid rgba(239, 68, 68, 0.3);
                            color: var(--accent-red);
                            border-radius: 28px;
                            display: flex; align-items: center; justify-content: center;
                            font-size: 2.75rem;
                            margin: 0 auto 2rem;
                            animation: pulseRed 2s infinite;
                        }}
                        @keyframes pulseRed {{
                            0% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }}
                            70% {{ box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }}
                            100% {{ box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }}
                        }}
                        h1 {{ font-size: 1.85rem; font-weight: 800; margin-bottom: 0.75rem; letter-spacing: -0.02em; }}
                        p {{ color: var(--text-sub); font-size: 0.95rem; line-height: 1.6; margin-bottom: 2rem; }}
                        .info-card {{
                            background: rgba(15, 23, 42, 0.4);
                            border: 1px solid rgba(255, 255, 255, 0.05);
                            border-radius: 20px; padding: 1.25rem;
                            margin-bottom: 2rem; text-align: left;
                        }}
                        .info-item {{ display: flex; justify-content: space-between; margin-bottom: 0.75rem; font-size: 0.85rem; }}
                        .info-item:last-child {{ margin-bottom: 0; }}
                        .info-label {{ color: var(--text-sub); font-weight: 500; }}
                        .info-value {{ color: var(--text-main); font-weight: 700; }}
                        .btn-support {{
                            display: inline-flex; align-items: center; justify-content: center;
                            gap: 0.5rem; width: 100%;
                            background: var(--accent-red); color: white;
                            padding: 1rem; border-radius: 16px; font-weight: 700;
                            text-decoration: none; transition: all 0.3s;
                            box-shadow: 0 10px 20px rgba(239, 68, 68, 0.25);
                        }}
                        .btn-support:hover {{ background: #dc2626; transform: translateY(-2px); box-shadow: 0 12px 24px rgba(239, 68, 68, 0.35); }}
                        .footer-brand {{ margin-top: 2rem; font-size: 0.75rem; color: var(--text-sub); font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon-wrapper"><i class="fas fa-lock"></i></div>
                        <h1>Hesap Askıya Alındı</h1>
                        <p>Bu şirkete ait lisans süresi dolduğundan veya hesap dondurulduğundan dolayı Zyronova hesabınız askıya alınmıştır. Hizmete devam edebilmek için lütfen sistem yöneticiniz ile iletişime geçin.</p>
                        <div class="info-card">
                            <div class="info-item">
                                <span class="info-label">Şirket Adı</span>
                                <span class="info-value">{g.current_company.name}</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Alt Alan Adı</span>
                                <span class="info-value">{g.current_company.subdomain}.localhost</span>
                            </div>
                            <div class="info-item">
                                <span class="info-label">Lisans Durumu</span>
                                <span class="info-value" style="color: var(--accent-red);">Askıda / Pasif</span>
                            </div>
                        </div>
                        <a href="mailto:info@zyronova.com?subject=Lisans Yenileme Talebi - {g.current_company.name}" class="btn-support">
                            <i class="fas fa-paper-plane"></i> Destek &amp; Lisans Yenileme
                        </a>
                        <div class="footer-brand"><i class="fas fa-shield-halved"></i> Zyronova Security System</div>
                    </div>
                </body>
                </html>
                """
                return html_response, 403

        # Tenant session oluştur
        if g.current_company:
            try:
                g.tenant_session = get_tenant_session(g.current_company.subdomain)
            except Exception as e:
                print(f"[TENANT] Session oluşturulamadı: {e}")
                g.tenant_session = None

        # Şifre değişikliği zorunluluğu
        if current_user.is_authenticated:
            # Multi-tenant cross-access önleme
            if not g.is_master and not current_user.is_master_user and g.current_company and current_user.company_id != g.current_company.id:
                logout_user()
                flash('Güvenlik nedeniyle oturumunuz kapatıldı. Lütfen kendi şirket panelinizden giriş yapın.', 'warning')
                return redirect(url_for('auth.login'))

            if current_user.needs_password_change:
                allowed_endpoints = ['auth.sifre_degistir', 'auth.logout', 'static']
                if request.endpoint and request.endpoint not in allowed_endpoints:
                    return redirect(url_for('auth.sifre_degistir'))

    @app.teardown_appcontext
    def teardown_tenant_session(exception=None):
        """Her request sonrası tenant session'ı temizle."""
        from extensions import close_all_tenant_sessions
        close_all_tenant_sessions()

    @app.context_processor
    def inject_helpers():
        from utils.helpers import get_tcmb_rates, get_vehicle_by_plaka
        
        vehicle_count = 0
        maintenance_alerts = []
        insurance_alerts = []
        inspection_alerts = []
        rental_expiration_alerts = []
        
        # Optimizasyon: API/JSON isteklerinde ağır alert sorgularını atla
        is_api_request = request.path.startswith('/api/') or request.is_json
        
        ts = g.get('tenant_session')
        if ts and g.current_company and not is_api_request:
            try:
                from sqlalchemy.orm import load_only
                vehicle_count = ts.query(Vehicle).filter_by(is_deleted=False).count()
                
                dismissed = {}
                if current_user.is_authenticated:
                    from models import DismissedAlert
                    db_dismissed = ts.query(DismissedAlert).filter_by(user_id=current_user.username).all()
                    for d in db_dismissed:
                        if d.alert_type not in dismissed:
                            dismissed[d.alert_type] = []
                        if d.target_id.isdigit():
                            dismissed[d.alert_type].append(int(d.target_id))
                        else:
                            dismissed[d.alert_type].append(d.target_id)

                maintenance_alerts = [
                    v for v in ts.query(Vehicle).filter(
                        Vehicle.guncelKm >= Vehicle.bakimYapildigiKm + 10000,
                        Vehicle.is_deleted == False
                    ).options(load_only(Vehicle.id, Vehicle.plaka, Vehicle.marka, Vehicle.model, Vehicle.guncelKm, Vehicle.bakimYapildigiKm)).all()
                    if v.id not in dismissed.get('maintenance', [])
                ]
                
                alert_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
                insurance_alerts = [
                    v for v in ts.query(Vehicle).filter(
                        Vehicle.sigortaBitisTarihi <= alert_date,
                        Vehicle.is_deleted == False
                    ).options(load_only(Vehicle.id, Vehicle.plaka, Vehicle.marka, Vehicle.model, Vehicle.sigortaBitisTarihi)).all()
                    if v.id not in dismissed.get('insurance', [])
                ]
                
                inspection_alerts = [
                    v for v in ts.query(Vehicle).filter(
                        Vehicle.vizeBitisTarihi <= alert_date,
                        Vehicle.is_deleted == False
                    ).options(load_only(Vehicle.id, Vehicle.plaka, Vehicle.marka, Vehicle.model, Vehicle.vizeBitisTarihi)).all()
                    if v.id not in dismissed.get('inspection', [])
                ]
                
                today = datetime.now().strftime('%Y-%m-%d')
                now_time = datetime.now().strftime('%H:%M')
                rental_expiration_alerts = [
                    r for r in ts.query(Rental).filter(
                        Rental.bitisTarihi <= today,
                        Rental.alinistaKm == 0
                    ).all()
                    if (r.bitisTarihi < today or (r.bitisTarihi == today and (r.bitisSaati or '09:00') <= now_time))
                    and r.id not in dismissed.get('rental_expiration', [])
                ]
            except Exception as e:
                print(f"[CONTEXT] Alert query hatası: {e}")
                
        support_tickets_count = 0
        if g.is_master:
            try:
                from models import SupportTicket
                support_tickets_count = db.session.query(SupportTicket).filter(SupportTicket.status == 'Açık').count()
            except Exception as e:
                pass
        
        # Akıllı Lisans Bildirim Sistemi
        license_warning = None
        if g.current_company and not g.is_master and g.current_company.license_expires_at:
            try:
                today_date = datetime.now().date()
                expiry_date = g.current_company.license_expires_at.date()
                days_remaining = (expiry_date - today_date).days
                
                if days_remaining == 14:
                    license_warning = {
                        'level': 'warning',
                        'message': "Sistem Bilgilendirmesi: Lisans sürenizin bitmesine 14 gün kalmıştır. Sistemi kesintisiz kullanmaya devam etmek için lütfen en kısa sürede lisansınızı yenileyiniz."
                    }
                elif 4 <= days_remaining <= 7:
                    license_warning = {
                        'level': 'warning',
                        'message': f"Dikkat: Lisans sürenizin bitmesine son {days_remaining} gün kalmıştır. Kesintisiz hizmet almaya devam edebilmek için lütfen lisansınızı yenileyiniz."
                    }
                elif 1 <= days_remaining <= 3:
                    license_warning = {
                        'level': 'danger',
                        'message': f"ACİL UYARI: Lisans sürenizin bitmesine son {days_remaining} gün kaldı! Lisans yenilenmediği takdirde sisteminiz otomatik olarak askıya alınacaktır."
                    }
            except Exception as le_err:
                print(f"[LICENSE WARNING] Hata: {le_err}")

        # Performance Telemetry
        latency_ms = 0.0
        if hasattr(g, 'start_time'):
            latency_ms = round((time.perf_counter() - g.start_time) * 1000, 1)

        return dict(
            get_vehicle_by_plaka=get_vehicle_by_plaka,
            currency_rates=get_tcmb_rates(),
            HASAR_LABELS={'yok': 'Hasarsız', 'var': 'Hasar Var', 'hafif': 'Hafif Hasarlı', 'orta': 'Orta Hasarlı', 'agir': 'Ağır Hasarlı'},
            DURUM_LABELS={'bosta': 'Boşta', 'kirada': 'Kirada', 'bakimda': 'Bakımda', 'pasif': 'Pasif'},
            now=datetime.now(),
            vehicle_count=vehicle_count,
            HERO_IMAGE=url_for('static', filename=f'uploads/{g.current_company.id}/hero.jpg', v=int(datetime.now().timestamp())) if g.current_company and os.path.exists(os.path.join(current_app.static_folder, 'uploads', str(g.current_company.id), 'hero.jpg')) else url_for('static', filename='images/hero_banner.webp'),
            maintenance_alerts=maintenance_alerts,
            insurance_alerts=insurance_alerts,
            inspection_alerts=inspection_alerts,
            rental_expiration_alerts=rental_expiration_alerts,
            license_warning=license_warning,
            latency_ms=latency_ms,
            support_tickets_count=support_tickets_count
        )

    @app.before_request
    def handle_options_preflight():
        if request.method == 'OPTIONS':
            response = current_app.make_default_options_response()
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
            return response

    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "connect-src 'self' https://cdn.jsdelivr.net https://*.tile.openstreetmap.org https://nominatim.openstreetmap.org https://photon.komoot.io https://geocode.arcgis.com; "
            "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: https://www.gstatic.com https://api.qrserver.com https://*.tile.openstreetmap.org https://*.google.com http://*.google.com https://server.arcgisonline.com;"
        )
        # PWA files: NEVER cache (manifest & service worker must always be fresh)
        if request.path in ('/static/manifest.json', '/static/sw.js'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        # Static assets: cache for 1 year (versioned via ?v= query param)
        elif request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        # Dashboard API partials: short cache (30s) to reduce repeated re-fetches
        elif '/api/dashboard/' in request.path:
            response.headers['Cache-Control'] = 'public, max-age=30'
        # HTML pages: no-cache
        elif response.content_type and 'text/html' in response.content_type:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response

    @app.route('/api/diagnostics/master')
    def api_diagnostics_master():
        companies = [{"id": c.id, "name": c.name, "subdomain": c.subdomain} for c in Company.query.all()]
        users = [{"id": u.id, "username": u.username, "company_id": u.company_id, "role": u.role} for u in User.query.all()]
        db_names = []
        try:
            res = db.session.execute(db.text("SELECT name FROM sys.databases")).fetchall()
            db_names = [r[0] for r in res]
        except Exception as e:
            db_names = [str(e)]
        return {"companies": companies, "users": users, "databases": db_names}

    @app.route('/api/diagnostics/reseed')
    def api_diagnostics_reseed():
        try:
            import reseed_data
            reseed_data.clear_data()
            reseed_data.seed_data()
            from utils.stats import StatsCache
            StatsCache.invalidate('WWW')
            return "SUCCESS"
        except Exception as e:
            import traceback
            return f"ERROR: {e}\n{traceback.format_exc()}", 500

    reseed_flag = os.path.join(os.path.dirname(__file__), 'reseed_pending.txt')
    if os.path.exists(reseed_flag):
        try:
            import reseed_data
            print("[AUTO-RESEED] Flag file found! Running reseed...")
            reseed_data.clear_data()
            reseed_data.seed_data()
            from utils.stats import StatsCache
            StatsCache.invalidate('WWW')
            os.remove(reseed_flag)
            print("[AUTO-RESEED] Successfully reseeded database and removed flag.")
        except Exception as reseed_err:
            print(f"[AUTO-RESEED] [ERROR] Failed to run auto-reseed: {reseed_err}")

    login_template = os.path.join(os.path.dirname(__file__), 'templates', 'login.html')
    if os.path.exists(login_template):
        try:
            os.remove(login_template)
            print("[CLEANUP] Deleted templates/login.html successfully.")
        except Exception as e:
            print(f"[CLEANUP] Failed to delete templates/login.html: {e}")

    # Start the Automated Security Daemon (File Integrity Monitoring)
    try:
        from utils.security_daemon import init_security_daemon
        init_security_daemon(app)
    except Exception as sd_err:
        print(f"[SECURITY DAEMON] [ERROR] Failed to start Security Daemon: {sd_err}")

    # Start the Automated Notifications Daemon (Overdue returns and Vehicle Expirations)
    try:
        from utils.notifications_daemon import init_notifications_daemon
        init_notifications_daemon(app)
    except Exception as nd_err:
        print(f"[NOTIFICATIONS DAEMON] [ERROR] Failed to start Notifications Daemon: {nd_err}")

    @app.route('/api/auth/login', methods=['GET', 'POST'])
    @csrf.exempt
    def api_auth_login():
        from flask import request, jsonify
        from models import User
        import jwt, os

        if request.method == 'POST':
            if not request.is_json:
                return jsonify({'error': 'Geçersiz istek formatı. Lütfen JSON gönderin.'}), 400
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.args.get('username')
            password = request.args.get('password')

        if not username or not password:
            return jsonify({'error': 'Geçersiz parametreler.'}), 400

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Geçersiz kullanıcı adı veya şifre.'}), 401

        if hasattr(user, 'company') and user.company and not user.company.is_active:
            return jsonify({'error': 'Hesabınız askıya alınmıştır.'}), 403

        secret = os.getenv('JWT_SECRET')
        if not secret:
            return jsonify({'error': 'Sunucu güvenlik yapılandırması eksik.'}), 500
        
        company_subdomain = user.company.subdomain if user.company else user.username
        
        if user.company_id == 1:
            target_module = 'MASTER'
        elif user.company_id == 3:
            target_module = 'TOUR_TRACKING'
        else:
            target_module = 'RENT_A_CAR'

        if getattr(user, 'is_2fa_enabled', False):
            temp_token = jwt.encode({
                'userId': user.id,
                'agencyId': user.company_id,
                'username': user.username,
                'subdomain': company_subdomain,
                'role': user.role or 'yonetici',
                'role_id': user.role_id,
                'require2FA': True,
                'type': target_module
            }, secret, algorithm='HS256')
            
            return jsonify({
                'require2FA': True,
                'tempToken': temp_token,
                'targetModule': target_module
            })

        token = jwt.encode({
            'agencyId': user.company_id,
            'username': user.username,
            'subdomain': company_subdomain,
            'role': user.role or 'yonetici',
            'role_id': user.role_id,
            'allowedModules': [target_module],
            'targetModule': target_module
        }, secret, algorithm='HS256')

        return jsonify({
            'success': True,
            'role': user.role or 'yonetici',
            'role_id': user.role_id,
            'targetModule': target_module,
            'token': token,
            'subdomain': company_subdomain,
            'username': user.username,
            'fullName': user.company_name or user.username,
            'agencyName': user.company_name or user.username,
            'mustChangePassword': user.needs_password_change
        })

    return app


@login_manager.user_loader
def load_user(user_id):
    user = db.session.get(User, user_id)
    if user and user.is_deleted:
        return None
    return user


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

