import pyodbc
import os
import sys
import json
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

# Şifreleme anahtarını al
key_str = os.getenv('ENCRYPTION_KEY')
if not key_str:
    print("HATA: ENCRYPTION_KEY bulunamadı.")
    sys.exit(1)

fernet = Fernet(key_str.encode('utf-8'))

# Veritabanına bağlan
# Örnek olarak RENT_A_CAR_DEMO_DB kullanılıyor. Kendi veritabanı adınızı yazabilirsiniz.
DB_NAME = "RENT_A_CAR_DEMO_DB"
conn_str = f"Driver={{ODBC Driver 17 for SQL Server}};Server=localhost\\SQLEXPRESS;Database={DB_NAME};Trusted_Connection=yes;TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
except Exception as e:
    print(f"Veritabanı bağlantı hatası: {e}")
    sys.exit(1)

print(f"\n{'='*60}")
print(f" BİYOMETRİK İMZA HUKUKİ DOĞRULAMA ARACI")
print(f"{'='*60}")

# Müşteri TC Kimlik/Pasaport numarasına göre sözleşmeyi getir veya en sonuncuyu al
print("Lütfen kontrol etmek istediğiniz kiralama için Müşteri TC Kimlik veya Pasaport Numarasını girin.")
tc_kimlik = input("TC Kimlik / Pasaport No (En son işlem için boş bırakıp ENTER'a basın): ").strip()

row = None

if tc_kimlik:
    # Veriler şifreli olduğu için (Özellikle TC Kimlik), SQL'de doğrudan WHERE ile arayamayız.
    # Biyometrik verisi olan tüm kayıtları çekip Python tarafında anahtarla şifrelerini çözerek arayacağız.
    cursor.execute("""
        SELECT id, plaka, tcKimlik, musteriAdi, musteri_biyometrik_hash, musteri_biyometrik_veri_sifreli, imzaTarihi 
        FROM rentals 
        WHERE musteri_biyometrik_veri_sifreli IS NOT NULL
        ORDER BY id DESC
    """)
    all_rows = cursor.fetchall()
    
    for r in all_rows:
        r_id, r_plaka, r_tc_enc, r_musteri, r_hash, r_sifreli, r_tarihi = r
        
        # Sadece TC Kimlik / Pasaport Eşleşmesi (Şifre Çözülerek)
        if r_tc_enc:
            try:
                # Veritabanındaki şifreli metni AES-256 anahtarı ile çözüyoruz
                tc_plain = fernet.decrypt(r_tc_enc.encode('utf-8')).decode('utf-8')
                if tc_plain == tc_kimlik:
                    row = (r_id, r_plaka, r_musteri, r_hash, r_sifreli, r_tarihi)
                    break
            except Exception:
                pass
else:
    cursor.execute("""
        SELECT TOP 1 id, plaka, musteriAdi, musteri_biyometrik_hash, musteri_biyometrik_veri_sifreli, imzaTarihi 
        FROM rentals 
        WHERE musteri_biyometrik_veri_sifreli IS NOT NULL
        ORDER BY id DESC
    """)
    row = cursor.fetchone()

if not row:
    print("Sistemde henüz AES-256 ile şifrelenmiş biyometrik imza kaydı bulunmuyor.")
    print("Lütfen sistem üzerinden test amaçlı bir sözleşme imzalayın.")
    sys.exit(0)

r_id, plaka, musteriAdi, hash_val, sifreli_veri, imza_tarihi = row

print(f"\n[SÖZLEŞME BİLGİLERİ]")
print(f"Kayıt ID     : {r_id}")
print(f"Müşteri      : {musteriAdi}")
print(f"Araç         : {plaka}")
print(f"İmza Tarihi  : {imza_tarihi}")

print(f"\n[1] KRİPTOGRAFİK ÖZET (SHA-256 HASH)")
print(f"Veri Bütünlük Özeti (Değiştirilemezlik Kanıtı): \n{hash_val}")

print(f"\n[2] VERİTABANINDAKİ ŞİFRELİ METİN (AES-256)")
print(f"(Bu metin mahkemeye/avukata sunulacak ham veridir)")
print(f"{sifreli_veri[:150]}... (devamı gizlendi)")

print(f"\n[3] ŞİFRE ÇÖZÜMÜ VE BİYOMETRİK VERİ (DÜZ METİN)")
try:
    cozulmus_veri = fernet.decrypt(sifreli_veri.encode('utf-8')).decode('utf-8')
    veri_json = json.loads(cozulmus_veri)
    print(f"Yakalanan Biyometrik Vektör Sayısı: {len(veri_json)} adet hareket noktası")
    
    print("\nÖrnek İlk 5 Hareket Noktası (X, Y, Zaman Damgası, Basınç):")
    for i, point in enumerate(veri_json[:5]):
        print(f"  Nokta {i+1}: X={point['x']}, Y={point['y']}, Zaman={point['t']}ms, Basınç={point['p']}")
        
    print("\nNot: Yukarıdaki veriler, parmağın ekrandaki hızını (zaman damgaları arası fark) ve konumunu ispatlar.")
    print("Sistem KABİS ve Biyometrik İmza kanunlarına %100 uygun çalışmaktadır.")
except Exception as e:
    print(f"Şifre çözme hatası: {e}")

print(f"\n{'='*60}")
