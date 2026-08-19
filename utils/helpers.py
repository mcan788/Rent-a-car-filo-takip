import urllib.request
import xml.etree.ElementTree as ET
import threading
from datetime import datetime
from flask import current_app, request
from extensions import db
from models import AuditLog
from urllib.parse import urlparse, urljoin
import re
import unicodedata

def slugify_subdomain(text):
    if not text:
        return ""
    # Convert Turkish characters to their ASCII equivalents
    text = text.replace('ı', 'i').replace('İ', 'I')
    text = text.replace('ğ', 'g').replace('Ğ', 'G')
    text = text.replace('ü', 'u').replace('Ü', 'U')
    text = text.replace('ş', 's').replace('Ş', 'S')
    text = text.replace('ö', 'o').replace('Ö', 'O')
    text = text.replace('ç', 'c').replace('Ç', 'C')
    # Normalize and keep only alphanumeric characters
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_allowed_image(file_stream):
    """Dosyanın gerçek bir resim olup olmadığını magic bytes ile kontrol eder (imghdr deprecated)."""
    header = file_stream.read(16)
    file_stream.seek(0)
    # JPEG: FF D8 FF
    if header[:3] == b'\xff\xd8\xff':
        return True
    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if header[:8] == b'\x89PNG\r\n\x1a\n':
        return True
    return False

_cached_rates = None
_last_fetch = None
_rates_lock = threading.Lock()

def safe_float(val):
    if not val: return 0.0
    try:
        s = str(val).strip()
        # If string contains both dot and comma
        if '.' in s and ',' in s:
            if s.rfind('.') > s.rfind(','):
                s = s.replace(',', '')
            else:
                s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            parts = s.split(',')
            # If comma acts as decimal point (e.g., 1500,50)
            if len(parts) == 2 and len(parts[1]) <= 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        elif '.' in s:
            parts = s.split('.')
            # If dot is thousands separator rather than decimal (e.g., 1.500)
            if len(parts) == 2 and len(parts[1]) > 2:
                s = s.replace('.', '')
        return float(s)
    except:
        return 0.0

def safe_int(val):
    if not val: return 0
    try:
        return int(round(safe_float(val)))
    except:
        return 0

def get_tcmb_rates():
    global _cached_rates, _last_fetch
    now = datetime.now()
    # Thread-safe cache check
    with _rates_lock:
        if _cached_rates and _last_fetch and (now - _last_fetch).total_seconds() < 3600:
            return _cached_rates
    
    try:
        url = current_app.config.get('TCMB_XML_URL', "https://www.tcmb.gov.tr/kurlar/today.xml")
        response = urllib.request.urlopen(url, timeout=5)
        xml_data = response.read()
        root = ET.fromstring(xml_data)
        
        rates = {}
        for currency in root.findall('Currency'):
            code = currency.get('CurrencyCode')
            if code in ['USD', 'EUR']:
                buying = currency.find('ForexBuying').text
                selling = currency.find('ForexSelling').text
                rates[code] = {
                    'buying': float(buying) if buying else 0,
                    'selling': float(selling) if selling else 0
                }
        
        with _rates_lock:
            _cached_rates = rates
            _last_fetch = now
        return rates
    except Exception as e:
        print(f"TCMB Kur çekme hatası: {e}")
        return _cached_rates or {'USD': {'buying': 0, 'selling': 0}, 'EUR': {'buying': 0, 'selling': 0}}

def format_currency(value, currency='₺'):
    try:
        v = float(value)
        if currency == '₺':
            return f"₺{v:,.0f}".replace(",", ".")
        elif currency == '$':
            return f"${v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        elif currency == '€':
            return f"€{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{currency}{v:,.0f}".replace(",", ".")
    except:
        return f"{currency}0"

def format_km(value):
    try:
        return f"{int(value):,} km".replace(",", ".")
    except:
        return "0 km"

def format_date(date_str):
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return d.strftime('%d.%m.%Y')
    except:
        return date_str or '-'

def format_number(value):
    try:
        return f"{int(value):,}".replace(",", ".")
    except:
        return "0"

def get_real_ip():
    """IIS/ARR proxy arkasından gerçek istemci IP adresini alır.
    Öncelik sırası: X-Forwarded-For > X-Real-IP > remote_addr
    """
    # X-Forwarded-For birden fazla IP içerebilir (client, proxy1, proxy2...)
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        # İlk IP her zaman gerçek istemci IP'sidir
        real_ip = forwarded_for.split(',')[0].strip()
        if real_ip and real_ip != '127.0.0.1':
            return real_ip
    
    # X-Real-IP (IIS ARR tarafından set edilir)
    real_ip_header = request.headers.get('X-Real-IP', '')
    if real_ip_header and real_ip_header != '127.0.0.1':
        return real_ip_header.strip()
    
    # Son çare: doğrudan bağlantı IP'si
    return request.remote_addr

def log_action(user, action, details=None):
    from flask import g
    cid = g.current_company.id if g.current_company else user.company_id
    
    log = AuditLog(
        company_id=cid,
        user_id=user.id,
        action=action,
        details=details,
        ip_address=get_real_ip()
    )
    db.session.add(log)
    db.session.commit()

def get_vehicle_by_plaka(plaka):
    from flask import g
    from models import Vehicle
    ts = g.get('tenant_session')
    if ts:
        return ts.query(Vehicle).filter_by(plaka=plaka).first()
    return None
