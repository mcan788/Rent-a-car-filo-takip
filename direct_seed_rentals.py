import pyodbc
import uuid
import random
from datetime import datetime, timedelta

conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=RENT_A_CAR_DEMO_DB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes')
cursor = conn.cursor()

# Get all vehicles
cursor.execute("SELECT id, plaka, marka, model, yil, guncelKm FROM vehicles WHERE is_deleted=0")
vehicles = cursor.fetchall()

if not vehicles:
    print("NO VEHICLES FOUND!")
    exit()

# Clear existing rentals, services, expenses
cursor.execute("DELETE FROM vehicle_expenses; DELETE FROM services; DELETE FROM rentals;")
conn.commit()

now = datetime.now()

# We will generate realistic rentals for the last 6 months
# Some cars will have active rentals, some will have past rentals.
# 60% past rentals, 20% active rentals, 20% available.

first_names = ['Ahmet', 'Mehmet', 'Ali', 'Veli', 'Ayse', 'Fatma', 'Zeynep', 'Mustafa', 'Kemal', 'Osman', 'Hasan', 'Huseyin', 'Burak', 'Can', 'Deniz', 'Emre', 'Fatih', 'Gokhan', 'Hakan', 'Ibrahim', 'Kaan', 'Levent', 'Murat', 'Nihat', 'Okan', 'Polat', 'Ridvan', 'Sinan', 'Tarik', 'Ugur', 'Volkan', 'Yasin', 'Zafer']
last_names = ['Yilmaz', 'Kaya', 'Demir', 'Celik', 'Sahin', 'Yildiz', 'Yildirim', 'Ozturk', 'Aydin', 'Ozdemir', 'Arslan', 'Dogan', 'Kilic', 'Aslan', 'Cetin', 'Kara', 'Koc', 'Kurt', 'Ozkan', 'Simsek', 'Polat', 'Ozcelik', 'Korkmaz', 'Erdogan', 'Yavuz', 'Can', 'Erdem']

company_names = ['Koc Holding', 'Sabanci', 'Eczacibasi', 'Zorlu', 'Dogus', 'Yildiz Holding', 'Enka', 'Ronesans', 'Limak', 'Kalyon', 'Cengiz', 'Tekfen', 'Tofas', 'Ford Otosan', 'Vestel', 'Arçelik']

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

def generate_tc():
    return str(random.randint(10000000000, 99999999999))

rentals_to_insert = []
expenses_to_insert = []

rental_query = """
INSERT INTO rentals (
    id, arac_id, plaka, marka, model, isim, soyisim, musteriAdi, tcKimlik, uyruk, kurumAdi, 
    baslangicTarihi, baslangicSaati, bitisTarihi, bitisSaati, kiralamaSuresi, verilisteKm, alinistaKm, 
    kullanilanKm, paraBirimi, gunlukFiyat, toplamFiyat, yakitMaliyeti, bakimMaliyeti, sigortaMaliyeti, 
    digerMaliyetler, toplamMaliyet, kar, hasarDurumu, hasarAciklama, hasarMaliyeti, odemeYontemi, 
    nakitTutar, kartTutar, is_signed, imzaTarihi
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

expense_query = """
INSERT INTO vehicle_expenses (
    id, arac_id, plaka, gider_tipi, tutar, paraBirimi, tarih, notlar
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
"""

for v in vehicles:
    v_id, v_plaka, v_marka, v_model, v_yil, v_guncel_km = v
    
    # 2 to 5 past rentals per vehicle
    num_past_rentals = random.randint(2, 5)
    
    current_verilis_km = v_guncel_km - 15000 # Let's say car had 15k less km 6 months ago
    if current_verilis_km < 0: current_verilis_km = 0
    
    base_price = random.choice([1200, 1500, 1800, 2000, 2500, 3000, 4000])
    if v_marka in ['Porsche', 'Mercedes-Benz', 'BMW', 'Audi']:
        base_price *= 2
        
    for i in range(num_past_rentals):
        start_dt = now - timedelta(days=random.randint(10, 180))
        duration = random.randint(1, 14)
        end_dt = start_dt + timedelta(days=duration)
        
        if end_dt > now - timedelta(days=2):
            end_dt = now - timedelta(days=2) # Keep it strictly in the past
            
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        
        gunluk = base_price + random.randint(-200, 200)
        toplam = gunluk * duration
        
        used_km = random.randint(50, 200) * duration
        alis_km = current_verilis_km + used_km
        
        maliyet = toplam * random.uniform(0.1, 0.3)
        kar = toplam - maliyet
        
        hasar = random.choices(['yok', 'hafif', 'orta'], weights=[80, 15, 5])[0]
        hasar_aciklama = ""
        hasar_maliyeti = 0
        if hasar == 'hafif':
            hasar_aciklama = "Sag kapi cizik"
            hasar_maliyeti = 1500
        elif hasar == 'orta':
            hasar_aciklama = "On tampon hasarli"
            hasar_maliyeti = 5000
            
        maliyet += hasar_maliyeti
        kar -= hasar_maliyeti
        
        rentals_to_insert.append((
            str(uuid.uuid4()), v_id, v_plaka, v_marka, v_model, fname, lname, f"{fname} {lname}", generate_tc(), 'TC', 
            random.choice(company_names) if random.random() > 0.8 else '',
            start_dt.strftime('%Y-%m-%d'), '09:00', end_dt.strftime('%Y-%m-%d'), '18:00', duration,
            current_verilis_km, alis_km, used_km, '₺', gunluk, toplam,
            0, 0, 0, maliyet, maliyet, kar, hasar, hasar_aciklama, hasar_maliyeti,
            'Kredi Karti' if random.random() > 0.3 else 'Nakit',
            toplam if random.random() <= 0.3 else 0,
            toplam if random.random() > 0.3 else 0,
            1, start_dt.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        current_verilis_km = alis_km
        
    # Maybe 1 active rental
    is_active = random.random() > 0.6
    if is_active:
        start_dt = now - timedelta(days=random.randint(1, 5))
        duration = random.randint(3, 10)
        end_dt = start_dt + timedelta(days=duration)
        
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        
        gunluk = base_price + random.randint(-200, 200)
        toplam = gunluk * duration
        
        rentals_to_insert.append((
            str(uuid.uuid4()), v_id, v_plaka, v_marka, v_model, fname, lname, f"{fname} {lname}", generate_tc(), 'TC', 
            '',
            start_dt.strftime('%Y-%m-%d'), '09:00', end_dt.strftime('%Y-%m-%d'), '09:00', duration,
            v_guncel_km, 0, 0, '₺', gunluk, toplam,
            0, 0, 0, 0, 0, toplam, 'yok', '', 0,
            'Kredi Karti', 0, toplam,
            1, start_dt.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Update vehicle status to kirada (actually handled via rental logic in app, but lets ensure guncelKm is fine)
        cursor.execute("UPDATE vehicles SET is_active=1 WHERE id=?", (v_id,))
        
    # Generate expenses
    for i in range(random.randint(1, 3)):
        gider_tarih = now - timedelta(days=random.randint(5, 180))
        gider_tip = random.choice(['Yikama', 'Yakit', 'Bakim', 'Lastik Degisimi', 'HGS/OGS', 'Trafik Cezasi'])
        tutar = random.randint(200, 2500)
        if gider_tip == 'Bakim': tutar = random.randint(3000, 8000)
        if gider_tip == 'Lastik Degisimi': tutar = random.randint(4000, 12000)
        
        expenses_to_insert.append((
            str(uuid.uuid4()), v_id, v_plaka, gider_tip, tutar, '₺', gider_tarih.strftime('%Y-%m-%d'), f"Arac icin {gider_tip} harcamasi"
        ))

# Batch Insert Rentals
for r in rentals_to_insert:
    cursor.execute(rental_query, r)

# Batch Insert Expenses
for e in expenses_to_insert:
    cursor.execute(expense_query, e)

conn.commit()
print(f"SUCCESSFULLY ADDED {len(rentals_to_insert)} RENTALS AND {len(expenses_to_insert)} EXPENSES!")
