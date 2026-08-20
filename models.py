import uuid
import os
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from cryptography.fernet import Fernet
import logging
from dotenv import load_dotenv
import json

load_dotenv()
_ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'fallback-zyronova-aes-key-32bytes!')

_fernet_cipher = Fernet(_ENCRYPTION_KEY.encode('utf-8'))

def encrypt_pii(text):
    if not text: return text
    try:
        return _fernet_cipher.encrypt(str(text).encode('utf-8')).decode('utf-8')
    except Exception as e:
        logging.error(f"Error encrypting PII: {e}")
        return text

def decrypt_pii(ciphertext):
    if not ciphertext: return ciphertext
    # Check if it starts with standard Fernet token
    if isinstance(ciphertext, str) and ciphertext.startswith('gAAAAAB'):
        try:
            return _fernet_cipher.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
        except Exception as e:
            logging.error(f"Error decrypting PII: {e}")
            return ciphertext
    return ciphertext

# ============================================================
# MASTER DATABASE MODELS (Flask-SQLAlchemy - db.Model)
# These tables live in ZYRONOVA_MASTER
# ============================================================

class Company(db.Model):
    __tablename__ = 'companies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subdomain = db.Column(db.String(50), unique=True, nullable=False)
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(100))
    logo_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    license_key = db.Column(db.String(100), unique=True)
    license_price = db.Column(db.Float, default=0.0)
    license_expires_at = db.Column(db.DateTime)
    tax_no = db.Column(db.String(20), nullable=True)
    kabis_username = db.Column(db.String(100), nullable=True)        # EGM KABİS Web Servis Kullanıcı Adı
    kabis_password = db.Column(db.String(255), nullable=True)        # EGM KABİS Web Servis Şifresi (plain - EGM SOAP gerektirir)
    kabis_sirket_kodu = db.Column(db.String(50), nullable=True)      # EGM Şirket Kodu
    contract_template = db.Column(db.UnicodeText, nullable=True, default="""1. TARAFLAR VE SÖZLEŞME KONUSU
Bu sözleşme, bir tarafta aracı kiraya veren (aşağıda KİRALAYAN olarak anılacaktır) ile diğer tarafta aracı kiralayan (aşağıda KİRACI olarak anılacaktır) arasında akdedilmiştir. Sözleşmenin konusu, belirtilen şartlar dahilinde aracın kiralanmasıdır.

2. ARACIN TESLİMİ VE KULLANIMI
Kiracı, aracı karayolları trafik kanunlarına, genel ahlaka ve kiralama şartlarına uygun olarak kullanacaktır. Araç, kiralama sözleşmesinde ismi belirtilmeyen üçüncü kişiler tarafından kullanılamaz. Aracın kullanımı sırasında oluşabilecek her türlü hukuki, cezai ve mali sorumluluk kiracıya aittir.

3. KİRA SÜRESİ VE İADE
Kiracı, aracı sözleşmede belirtilen yer ve tarihte eksiksiz ve hasarsız teslim etmekle yükümlüdür. Gecikme durumunda ek ücret yansıtılacaktır.

4. SİGORTA VE HASAR DURUMU
Araç kasko ve sigorta kapsamında olup, kural ihlalleri, alkollü kullanım veya yetkisiz sürücü kullanımı gibi durumlarda sigorta geçersiz kalacak ve tüm hasar maliyeti kiracıdan tahsil edilecektir.

5. UYUŞMAZLIKLARIN ÇÖZÜMÜ
Bu sözleşmeden doğan her türlü uyuşmazlığın çözümünde, kiralayan şirketin merkezinin bulunduğu yerdeki Mahkemeler ve İcra Daireleri yetkilidir.""")
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships (only to other master tables)
    users = db.relationship('User', backref='company', lazy=True, primaryjoin="Company.id == User.company_id", cascade="all, delete-orphan")
    audit_logs = db.relationship('AuditLog', backref='company', lazy=True, primaryjoin="Company.id == AuditLog.company_id", cascade="all, delete-orphan")

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), default=1, index=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(50))
    surname = db.Column(db.String(50))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    company_name = db.Column(db.String(100))
    license_expires = db.Column(db.String(20))
    role = db.Column(db.String(20), default='admin')
    role_id = db.Column(db.Integer, default=22)
    can_view_reports = db.Column(db.Boolean, default=True)
    can_view_analysis = db.Column(db.Boolean, default=True)
    can_view_excel = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    phone_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(10))
    needs_password_change = db.Column(db.Boolean, default=True)
    can_manage_personnel = db.Column(db.Boolean, default=False)
    permissions_json = db.Column(db.Text)
    
    # 2FA Fields
    two_factor_secret = db.Column(db.String(32))
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    has_seen_2fa_prompt = db.Column(db.Boolean, default=False)
    two_factor_recovery_codes = db.Column(db.Text)
    
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime)
    deleted_by_id = db.Column(db.String(50), db.ForeignKey('users.id', use_alter=True, name='fk_user_deleted_by'))
    
    # Relationships
    deleted_by_user = db.relationship('User', remote_side=[id], backref='deleted_users', foreign_keys=[deleted_by_id])

    # === Rol Sabitleri (Role Constants) ===
    ROLE_M1_SUPER_ADMIN = 11  # Master - Süper Admin
    ROLE_M2_ADMIN = 12        # Master - Admin
    ROLE_M3_PERSONEL = 13     # Master - Personel
    ROLE_R1_YONETICI = 21     # Rent A Car - Yönetici
    ROLE_R2_PERSONEL = 22     # Rent A Car - Personel
    ROLE_T1_YONETICI = 31     # Tur Takip - Yönetici
    ROLE_T2_PERSONEL = 32     # Tur Takip - Personel

    MASTER_ROLES = {11, 12, 13}
    RENTACAR_ROLES = {21, 22}
    TURTAKIP_ROLES = {31, 32}
    MANAGER_ROLES = {11, 12, 21, 31}  # Yönetici seviyesindeki roller

    @property
    def is_super_admin(self):
        return self.role_id in (1, 11)

    @property
    def is_manager(self):
        """Yönetici seviyesinde mi? (M1, M2, R1, T1)"""
        return self.role_id in (1, 11, 12, 21, 31)

    @property
    def is_master_user(self):
        """Master panel kullanıcısı mı? (M1, M2, M3)"""
        return self.role_id in (1, 11, 12, 13)

    @property
    def is_rentacar_user(self):
        """Rent A Car panel kullanıcısı mı? (R1, R2)"""
        return self.role_id in (21, 22)

    @property
    def is_turtakip_user(self):
        """Tur Takip panel kullanıcısı mı? (T1, T2)"""
        return self.role_id in (31, 32)

    @property
    def role_code(self):
        """Rol kodunu döndürür (M1, M2, R1, R2, T1, T2 vb.)"""
        codes = {1: 'M1', 11: 'M1', 12: 'M2', 13: 'M3', 21: 'R1', 22: 'R2', 31: 'T1', 32: 'T2'}
        return codes.get(self.role_id, 'R2')

    @property
    def role_display_name(self):
        """Rolün kullanıcı dostu adını döndürür"""
        names = {
            1: 'Süper Admin', 11: 'Süper Admin', 12: 'Admin', 13: 'Personel',
            21: 'Yönetici', 22: 'Personel',
            31: 'Yönetici', 32: 'Personel'
        }
        return names.get(self.role_id, 'Personel')

    @property
    def role_panel_name(self):
        """Rolün ait olduğu panel adını döndürür"""
        if self.role_id in (1, 11, 12, 13):
            return 'Master Panel'
        elif self.role_id in (21, 22):
            return 'Rent A Car'
        elif self.role_id in (31, 32):
            return 'Tur Takip'
        return 'Bilinmiyor'

    def set_password(self, password):
        import bcrypt
        new_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        import json
        perms = {}
        if self.permissions_json:
            try:
                perms = json.loads(self.permissions_json)
            except:
                pass
        history = perms.get('_password_history', [])
        if self.password_hash:
            history.insert(0, self.password_hash)
        history = history[:3]
        perms['_password_history'] = history
        self.permissions_json = json.dumps(perms)
        self.password_hash = new_hash

    def check_password(self, password):
        if self.password_hash.startswith('$2a$') or self.password_hash.startswith('$2b$'):
            try:
                import bcrypt
                return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
            except ImportError:
                print("[WARNING] bcrypt package is missing. Cannot verify bcrypt password hash.", flush=True)
                return False
        return check_password_hash(self.password_hash, password)

    def get_permissions(self):
        # Eğer Master şirket personeli ise (Company 1) farklı bir yetki seti döner
        if self.company_id == 1:
            defaults = {
                "master_dashboard": {"all": True},
                "dashboard": {"all": True, "cards": ["stats", "revenue", "rentals", "vehicles"]},
                "company_manage": {"all": True, "actions": {"add": True, "edit": True, "suspend": True, "delete": True}},
                "security_manage": {"all": True},
                "system_logs": {"all": True},
                "system_settings": {"all": True},
                "support_access": {"all": True},
                "tur_takip_manage": {"all": True},
                # Fleet keys required by base.html (disabled for master users)
                "araclar": {"all": False},
                "kiralamalar": {"all": False},
                "ciro_analiz": {"all": False},
                "rapor": {"all": False},
                "servis": {"all": False},
                "excel": {"all": False},
                "logs": {"all": False},
                "ayarlar": {"all": False},
            }
        else:
            defaults = {
                "dashboard": {"all": True, "cards": ["stats", "revenue", "rentals", "vehicles"]},
                "araclar": {"all": True, "actions": {"add": True, "edit": True, "delete": True}},
                "kiralamalar": {"all": True, "actions": {"add": True, "edit": True, "delete": True, "extend": True}},
                "ciro_analiz": {"all": True},
                "rapor": {"all": True},
                "servis": {"all": True},
                "excel": {"all": True},
                "logs": {"all": True},
                "ayarlar": {"all": True}
            }
            
        if not self.permissions_json:
            return defaults

        try:
            perms = json.loads(self.permissions_json)
            for k, v in defaults.items():
                if k not in perms:
                    perms[k] = v
            return perms
        except:
            return defaults

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'))
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'))
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs', lazy=True)

class SupportTicket(db.Model):
    __tablename__ = 'support_tickets'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False, index=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), default='Genel Destek')
    priority = db.Column(db.String(20), default='Normal')
    status = db.Column(db.String(20), default='Açık') # Açık, Yanıtlandı, Kapalı
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    company = db.relationship('Company', backref='support_tickets')
    user = db.relationship('User', backref='support_tickets')
    messages = db.relationship('SupportTicketMessage', backref='ticket', cascade="all, delete-orphan", order_by="SupportTicketMessage.created_at.asc()")

class SupportTicketMessage(db.Model):
    __tablename__ = 'support_ticket_messages'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = db.Column(db.String(50), db.ForeignKey('support_tickets.id'), nullable=False, index=True)
    sender_id = db.Column(db.String(50), db.ForeignKey('users.id'), nullable=True) # None means system or super admin
    is_master = db.Column(db.Boolean, default=False) # True if sent by Super Admin
    message = db.Column(db.Text, nullable=False)
    attachment_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    sender = db.relationship('User', backref='support_messages')


# ============================================================
# TENANT DATABASE MODELS (Plain SQLAlchemy - TenantBase)
# These tables live in {SUBDOMAIN} databases
# ============================================================

TenantBase = declarative_base()

class Vehicle(TenantBase):
    __tablename__ = 'vehicles'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    plaka = db.Column(db.String(20), unique=True, nullable=False, index=True)
    marka = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    yil = db.Column(db.Integer)
    renk = db.Column(db.String(30))
    is_active = db.Column(db.Boolean, default=True)
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    is_in_maintenance = db.Column(db.Boolean, default=False)
    bakim_yeri = db.Column(db.String(100), default='')
    bakim_nedeni = db.Column(db.Text, default='')
    bakim_gonderen = db.Column(db.String(100), default='')
    bakim_gidis_km = db.Column(db.Integer, default=0)
    bakim_gidis_tarihi = db.Column(db.String(20), default='')
    guncelKm = db.Column(db.Integer, default=0)
    bakimYapildigiKm = db.Column(db.Integer, default=0)
    alisKm = db.Column(db.Integer, default=0)
    sigortaBitisTarihi = db.Column(db.String(20))
    vizeBitisTarihi = db.Column(db.String(20))
    sigortaMaliyeti = db.Column(db.Float, default=0.0)
    vizeMaliyeti = db.Column(db.Float, default=0.0)
    gunlukUcret = db.Column(db.Float, default=0.0)

    @property
    def durum(self):
        if not self.is_active:
            return 'pasif'
        if self.is_in_maintenance:
            return 'bakimda'
        # Check for active rental - uses tenant session
        from flask import g
        if hasattr(g, 'tenant_session'):
            active_rental = g.tenant_session.query(Rental).filter_by(plaka=self.plaka, alinistaKm=0).first()
            if active_rental:
                return 'kirada'
        return 'bosta'

    def to_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = getattr(self, c.name)
        d['durum'] = self.durum
        return d

class Rental(TenantBase):
    __tablename__ = 'rentals'
    __table_args__ = (
        db.Index('idx_rental_plaka_baslangic', 'plaka', 'baslangicTarihi'),
        db.Index('idx_rental_plaka_bitis', 'plaka', 'bitisTarihi')
    )
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    arac_id = db.Column(db.String(50))
    plaka = db.Column(db.String(20), nullable=False, index=True)
    marka = db.Column(db.String(50))
    model = db.Column(db.String(50))
    isim = db.Column(db.String(50))
    soyisim = db.Column(db.String(50))
    musteriAdi = db.Column(db.String(100))
    _tcKimlik = db.Column('tcKimlik', db.String(255))
    uyruk = db.Column(db.String(100), default='TC')
    dogumYeri = db.Column(db.String(100))
    kurumAdi = db.Column(db.String(100))
    personelAdi = db.Column(db.String(50))
    surucuAdSoyad = db.Column(db.String(100))
    _ehliyetNo = db.Column('ehliyetNo', db.String(255))

    @hybrid_property
    def tcKimlik(self):
        return decrypt_pii(self._tcKimlik)

    @tcKimlik.setter
    def tcKimlik(self, value):
        self._tcKimlik = encrypt_pii(value)

    @hybrid_property
    def ehliyetNo(self):
        return decrypt_pii(self._ehliyetNo)

    @ehliyetNo.setter
    def ehliyetNo(self, value):
        self._ehliyetNo = encrypt_pii(value)
    ehliyetVerilisTarihi = db.Column(db.String(20))
    ehliyetGecerlilikTarihi = db.Column(db.String(20))
    baslangicTarihi = db.Column(db.String(20), index=True)
    baslangicSaati = db.Column(db.String(10), default='09:00')
    bitisTarihi = db.Column(db.String(20), index=True)
    bitisSaati = db.Column(db.String(10), default='09:00')
    kiralamaSuresi = db.Column(db.Integer, default=0)
    verilisteKm = db.Column(db.Integer, default=0)
    alinistaKm = db.Column(db.Integer, default=0)
    kullanilanKm = db.Column(db.Integer, default=0)
    paraBirimi = db.Column(db.Unicode(10), default='₺')
    gunlukFiyat = db.Column(db.Float, default=0.0)
    toplamFiyat = db.Column(db.Float, default=0.0)
    yakitMaliyeti = db.Column(db.Float, default=0.0)
    bakimMaliyeti = db.Column(db.Float, default=0.0)
    sigortaMaliyeti = db.Column(db.Float, default=0.0)
    digerMaliyetler = db.Column(db.Float, default=0.0)
    toplamMaliyet = db.Column(db.Float, default=0.0)
    kar = db.Column(db.Float, default=0.0)
    hasarDurumu = db.Column(db.String(20), default='yok')
    hasarAciklama = db.Column(db.Text)
    hasarMaliyeti = db.Column(db.Float, default=0.0)
    notlar = db.Column(db.Text)
    teslimAlanPersonel = db.Column(db.String(100))
    konaklamaTipi = db.Column(db.String(50))
    odaNo = db.Column(db.String(50))
    adres = db.Column(db.Text)
    kiralama_lat = db.Column(db.Float, default=0.0)
    kiralama_lng = db.Column(db.Float, default=0.0)
    teslim_lat = db.Column(db.Float, default=0.0)
    teslim_lng = db.Column(db.Float, default=0.0)
    odemeYontemi = db.Column(db.String(50))
    nakitTutar = db.Column(db.Float, default=0.0)
    kartTutar = db.Column(db.Float, default=0.0)
    musteriImza = db.Column(db.Text, nullable=True)
    musteri_biyometrik_veri_sifreli = db.Column(db.Text, nullable=True)
    musteri_biyometrik_hash = db.Column(db.String(64), nullable=True)
    firmaImza = db.Column(db.Text, nullable=True)
    is_signed = db.Column(db.Boolean, default=False)
    imzaTarihi = db.Column(db.String(20), nullable=True)
    musteriEmail = db.Column(db.String(100), nullable=True)
    musteriTelefon = db.Column(db.String(20), nullable=True)
    overdue_alert_sent = db.Column(db.Boolean, default=False)

    # KABIS Takip Alanlari
    kabis_kiralama_status = db.Column(db.String(20), default='bekliyor')
    kabis_kiralama_hata = db.Column(db.Text, nullable=True)
    kabis_teslim_status = db.Column(db.String(20), default='bekliyor')
    kabis_teslim_hata = db.Column(db.Text, nullable=True)

    # Sözleşme ayarları
    sozlesmeDili = db.Column(db.String(10), default='TR')
    sozlesmeMetni = db.Column(db.UnicodeText, nullable=True)

    def to_dict(self):
        # Exclude internal cost and profit data for security
        sensitive_fields = ['toplamMaliyet', 'kar', 'yakitMaliyeti', 'bakimMaliyeti', 'sigortaMaliyeti', 'digerMaliyetler', 'hasarMaliyeti']
        
        result_dict = {}
        for c in self.__table__.columns:
            if c.name not in sensitive_fields:
                val = getattr(self, c.name, None)
                result_dict[c.name] = val
        return result_dict

class Service(TenantBase):
    __tablename__ = 'services'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    arac_id = db.Column(db.String(50))
    plaka = db.Column(db.String(20), nullable=False, index=True)
    km = db.Column(db.Integer, default=0)
    ucret = db.Column(db.Float, default=0.0)
    paraBirimi = db.Column(db.Unicode(10), default='₺') 
    kisi = db.Column(db.String(100))
    yer = db.Column(db.String(100))
    gidis_tarihi = db.Column(db.String(20))
    tarih = db.Column(db.String(20))
    notlar = db.Column(db.Text)

class VehicleExpense(TenantBase):
    __tablename__ = 'vehicle_expenses'
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    arac_id = db.Column(db.String(50))
    plaka = db.Column(db.String(20), nullable=False, index=True)
    gider_tipi = db.Column(db.String(50), nullable=False)
    tutar = db.Column(db.Float, default=0.0)
    paraBirimi = db.Column(db.Unicode(10), default='₺')
    tarih = db.Column(db.String(20), index=True)
    notlar = db.Column(db.Text)

class DismissedAlert(TenantBase):
    __tablename__ = 'dismissed_alerts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(50))
    alert_type = db.Column(db.String(50))
    target_id = db.Column(db.String(50))
    state_value = db.Column(db.String(100))
    dismissed_at = db.Column(db.DateTime, default=datetime.now)

# Trigger reload for bcrypt
