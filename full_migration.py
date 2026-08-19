"""
KAPSAMLI VERİTABANI MİGRASYON SCRİPTİ
- Tüm RentACar tenant veritabanlarını tespit eder
- Her DB'de eksik sütunları ekler (KABIS + şifreleme uyumu)
- Mevcut PII verilerini (tcKimlik, ehliyetNo) şifreler
- Şifrelenmiş sütunların boyutunu 255'e çıkarır
"""

import pyodbc
import os
import sys
import uuid
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

CONN_OPTS = "Driver={ODBC Driver 17 for SQL Server};Server=localhost\\SQLEXPRESS;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"

# RentACar DB'lerini tespit et (rentals tablosu olanlar)
RENTACAR_DBS = [
    'RENT_A_CAR_DEMO_DB',
    'rentacardemo', 
    'baysalrentacar',
    'fuglarentacar',
    'yadelrentacar',
    'www',
]

# models.py'deki Rental sınıfından türetilen tam sütun listesi
# (type, default) formatında
REQUIRED_COLUMNS = {
    # Temel bilgiler
    'arac_id':                  ('VARCHAR(50)',    'NULL'),
    'plaka':                    ('VARCHAR(20)',    "''"),
    'marka':                    ('VARCHAR(50)',    'NULL'),
    'model':                    ('VARCHAR(50)',    'NULL'),
    'isim':                     ('VARCHAR(50)',    'NULL'),
    'soyisim':                  ('VARCHAR(50)',    'NULL'),
    'musteriAdi':               ('VARCHAR(100)',   'NULL'),
    'tcKimlik':                 ('VARCHAR(500)',   'NULL'),   # Şifreli - büyük alan
    'uyruk':                    ('VARCHAR(100)',   "'TC'"),
    'kurumAdi':                 ('VARCHAR(100)',   'NULL'),
    'personelAdi':              ('VARCHAR(50)',    'NULL'),
    'surucuAdSoyad':            ('VARCHAR(100)',   'NULL'),
    'ehliyetNo':                ('VARCHAR(500)',   'NULL'),   # Şifreli - büyük alan
    'ehliyetVerilisTarihi':     ('VARCHAR(20)',    'NULL'),
    'ehliyetGecerlilikTarihi':  ('VARCHAR(20)',    'NULL'),
    # Tarih/Süre
    'baslangicTarihi':          ('VARCHAR(20)',    'NULL'),
    'baslangicSaati':           ('VARCHAR(10)',    "'09:00'"),
    'bitisTarihi':              ('VARCHAR(20)',    'NULL'),
    'bitisSaati':               ('VARCHAR(10)',    "'09:00'"),
    'kiralamaSuresi':           ('INT',            '0'),
    # Km
    'verilisteKm':              ('INT',            '0'),
    'alinistaKm':               ('INT',            '0'),
    'kullanilanKm':             ('INT',            '0'),
    # Finans
    'paraBirimi':               ('NVARCHAR(10)',   "N'₺'"),
    'gunlukFiyat':              ('FLOAT',          '0.0'),
    'toplamFiyat':              ('FLOAT',          '0.0'),
    'yakitMaliyeti':            ('FLOAT',          '0.0'),
    'bakimMaliyeti':            ('FLOAT',          '0.0'),
    'sigortaMaliyeti':          ('FLOAT',          '0.0'),
    'digerMaliyetler':          ('FLOAT',          '0.0'),
    'toplamMaliyet':            ('FLOAT',          '0.0'),
    'kar':                      ('FLOAT',          '0.0'),
    # Hasar
    'hasarDurumu':              ('VARCHAR(20)',    "'yok'"),
    'hasarAciklama':            ('TEXT',           'NULL'),
    'hasarMaliyeti':            ('FLOAT',          '0.0'),
    # Diğer
    'notlar':                   ('TEXT',           'NULL'),
    'teslimAlanPersonel':       ('VARCHAR(100)',   'NULL'),
    'konaklamaTipi':            ('VARCHAR(50)',    'NULL'),
    'odaNo':                    ('VARCHAR(50)',    'NULL'),
    'adres':                    ('TEXT',           'NULL'),
    'kiralama_lat':             ('FLOAT',          '0.0'),
    'kiralama_lng':             ('FLOAT',          '0.0'),
    'teslim_lat':               ('FLOAT',          '0.0'),
    'teslim_lng':               ('FLOAT',          '0.0'),
    'odemeYontemi':             ('VARCHAR(50)',    'NULL'),
    'nakitTutar':               ('FLOAT',          '0.0'),
    'kartTutar':                ('FLOAT',          '0.0'),
    'musteriImza':              ('TEXT',           'NULL'),
    'musteri_biyometrik_veri_sifreli': ('TEXT',    'NULL'),
    'musteri_biyometrik_hash':  ('VARCHAR(64)',    'NULL'),
    'firmaImza':                ('TEXT',           'NULL'),
    'is_signed':                ('BIT',            '0'),
    'imzaTarihi':               ('VARCHAR(20)',    'NULL'),
    # KABIS - zorunlu entegrasyon alanları
    'kabis_kiralama_status':    ('VARCHAR(50)',    "'bekliyor'"),
    'kabis_kiralama_hata':      ('TEXT',           'NULL'),
    'kabis_teslim_status':      ('VARCHAR(50)',    "'bekliyor'"),
    'kabis_teslim_hata':        ('TEXT',           'NULL'),
}


def get_connection(db_name):
    conn_str = f"{CONN_OPTS}Database={db_name};"
    return pyodbc.connect(conn_str, timeout=5)


def get_existing_columns(cursor, table='rentals'):
    cursor.execute(f"SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='{table}'")
    return {row[0]: (row[1], row[2]) for row in cursor.fetchall()}


def has_table(cursor, table):
    cursor.execute(f"SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME='{table}'")
    return cursor.fetchone() is not None


def migrate_database(db_name, fernet):
    print(f"\n{'='*60}")
    print(f"  Veritabanı: {db_name}")
    print(f"{'='*60}")
    
    try:
        conn = get_connection(db_name)
        cursor = conn.cursor()
    except Exception as e:
        print(f"  ❌ Bağlanamadı: {e}")
        return False

    # 1. rentals tablosu var mı?
    if not has_table(cursor, 'rentals'):
        print(f"  ⚠️  rentals tablosu yok, atlanıyor.")
        conn.close()
        return False

    # 2. Mevcut sütunları al
    existing = get_existing_columns(cursor, 'rentals')
    print(f"  📋 Mevcut sütun sayısı: {len(existing)}")

    # 3. Eksik sütunları ekle
    added = 0
    for col_name, (col_type, col_default) in REQUIRED_COLUMNS.items():
        if col_name not in existing:
            try:
                if col_default == 'NULL':
                    sql = f"ALTER TABLE rentals ADD [{col_name}] {col_type} NULL"
                else:
                    sql = f"ALTER TABLE rentals ADD [{col_name}] {col_type} NULL CONSTRAINT [df_{col_name}_{db_name[:10]}] DEFAULT {col_default}"
                cursor.execute(sql)
                conn.commit()
                print(f"  ✅ Eklendi: {col_name} ({col_type})")
                added += 1
            except Exception as e:
                print(f"  ⚠️  {col_name} eklenemedi: {e}")
        else:
            # Şifreli sütunların boyutu yetersizse genişlet
            if col_name in ('tcKimlik', 'ehliyetNo'):
                _, max_len = existing[col_name]
                if max_len is not None and max_len < 500:
                    try:
                        cursor.execute(f"ALTER TABLE rentals ALTER COLUMN [{col_name}] VARCHAR(500) NULL")
                        conn.commit()
                        print(f"  🔄 Genişletildi: {col_name} -> VARCHAR(500)")
                    except Exception as e:
                        print(f"  ⚠️  {col_name} genişletilemedi: {e}")

    print(f"  ✅ Toplam {added} yeni sütun eklendi.")

    # 4. Mevcut PII verilerini şifrele
    print(f"  🔐 PII şifreleme başlıyor...")
    try:
        cursor.execute("SELECT id, tcKimlik, ehliyetNo FROM rentals")
        rows = cursor.fetchall()
        encrypt_count = 0
        skip_count = 0
        
        for row in rows:
            r_id, tc, ehliyet = row
            updates = {}
            
            # Fernet token'ları 'gAAAAA' ile başlar ve ~100+ karakter uzundur
            def is_encrypted(val):
                return val and len(str(val)) > 80 and str(val).startswith('gAAAAA')
            
            if tc and not is_encrypted(tc):
                try:
                    updates['tcKimlik'] = fernet.encrypt(str(tc).encode('utf-8')).decode('utf-8')
                except:
                    pass
                    
            if ehliyet and not is_encrypted(ehliyet):
                try:
                    updates['ehliyetNo'] = fernet.encrypt(str(ehliyet).encode('utf-8')).decode('utf-8')
                except:
                    pass
                    
            if updates:
                set_parts = ', '.join([f"[{k}] = ?" for k in updates.keys()])
                vals = list(updates.values()) + [r_id]
                cursor.execute(f"UPDATE rentals SET {set_parts} WHERE id = ?", vals)
                encrypt_count += 1
            else:
                skip_count += 1
                
        conn.commit()
        print(f"  🔐 {encrypt_count} kayıt şifrelendi, {skip_count} kayıt atlandı (zaten şifreli veya boş).")
    except Exception as e:
        print(f"  ❌ Şifreleme hatası: {e}")
        conn.rollback()

    # 5. KABIS null değerlerini varsayılanla doldur
    print(f"  🔧 KABIS varsayılan değerleri ayarlanıyor...")
    try:
        cursor.execute("UPDATE rentals SET kabis_kiralama_status='bekliyor' WHERE kabis_kiralama_status IS NULL")
        cursor.execute("UPDATE rentals SET kabis_teslim_status='bekliyor' WHERE kabis_teslim_status IS NULL")
        conn.commit()
        print(f"  ✅ KABIS varsayılan değerleri güncellendi.")
    except Exception as e:
        print(f"  ⚠️  KABIS güncelleme hatası: {e}")

    conn.close()
    return True


def main():
    # Şifreleme anahtarını yükle
    key_str = os.getenv('ENCRYPTION_KEY')
    if not key_str:
        print("❌ ENCRYPTION_KEY bulunamadı! .env dosyasını kontrol edin.")
        sys.exit(1)
    
    fernet = Fernet(key_str.encode('utf-8'))
    print(f"✅ Şifreleme anahtarı yüklendi.")
    
    # Dinamik olarak tüm DB'leri tara
    print("\n🔍 Tüm veritabanları taranıyor...")
    try:
        master_conn = get_connection('master')
        master_cursor = master_conn.cursor()
        master_cursor.execute("""
            SELECT name FROM sys.databases 
            WHERE name NOT IN ('master','tempdb','model','msdb','ZYRONOVA_MASTER','TurMasterDB','sa','zyronova')
            AND name NOT LIKE 'TUR_TAKIP%'
            AND name NOT LIKE 'MELIS%'
            AND name NOT LIKE 'DENEME%'
            ORDER BY name
        """)
        all_dbs = [row[0] for row in master_cursor.fetchall()]
        master_conn.close()
        print(f"  Bulunan potansiyel RentACar veritabanları: {all_dbs}")
    except Exception as e:
        print(f"❌ Veritabanları listelenemedi: {e}")
        all_dbs = RENTACAR_DBS

    success = 0
    fail = 0
    for db in all_dbs:
        result = migrate_database(db, fernet)
        if result:
            success += 1
        else:
            fail += 1

    print(f"\n{'='*60}")
    print(f"  MİGRASYON TAMAMLANDI")
    print(f"  Başarılı: {success} DB | Atlandı/Hata: {fail} DB")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
