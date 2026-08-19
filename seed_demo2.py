import os
import json
import uuid
from datetime import datetime, timedelta
from app import app, db
from models import Vehicle, Rental, Service, VehicleExpense
from extensions import get_tenant_session
from dotenv import load_dotenv

load_dotenv()

def clear_data():
    print("Veritabanı temizleniyor...")
    with app.app_context():
        tenant_session = get_tenant_session('RentACarDemo', app)
        # Deletion order to respect foreign keys
        tenant_session.query(VehicleExpense).delete()
        tenant_session.query(Service).delete()
        tenant_session.query(Rental).delete()
        tenant_session.query(Vehicle).delete()
        tenant_session.commit()
    print("Veritabanı temizlendi.")

    print("JSON dosyaları temizleniyor...")
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    for filename in ['vehicles.json', 'rentals.json', 'servis.json']:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([], f)
            print(f"{filename} boşaltıldı.")

def seed_data():
    print("Yeni veriler ekleniyor...")
    with app.app_context():
        tenant_session = get_tenant_session('RentACarDemo', app)
        # 1. ARAÇLAR (Genişletilmiş ve Son Derece Gerçekçi 20 Araçlık Türkiye Filosu)
        vehicles_data = [
            {"plaka": "34 ABC 001", "marka": "Mercedes-Benz", "model": "C200", "yil": 2023, "renk": "Metalik Gri", "guncelKm": 18200, "alisKm": 0, "sigortaBitisTarihi": "2026-12-01", "vizeBitisTarihi": "2026-06-15", "bakimYapildigiKm": 15000},
            {"plaka": "06 XYZ 99", "marka": "BMW", "model": "320i", "yil": 2022, "renk": "Siyah", "guncelKm": 42000, "alisKm": 5000, "sigortaBitisTarihi": "2027-01-20", "vizeBitisTarihi": "2026-08-10", "bakimYapildigiKm": 40000},
            {"plaka": "35 TR 3535", "marka": "Audi", "model": "A4", "yil": 2024, "renk": "Beyaz", "guncelKm": 5200, "alisKm": 0, "sigortaBitisTarihi": "2027-04-10", "vizeBitisTarihi": "2027-04-10", "bakimYapildigiKm": 0},
            {"plaka": "07 ANT 07", "marka": "Volkswagen", "model": "Passat", "yil": 2021, "renk": "Okyanus Mavi", "guncelKm": 89500, "alisKm": 20000, "sigortaBitisTarihi": "2026-10-05", "vizeBitisTarihi": "2026-03-20", "bakimYapildigiKm": 80000},
            {"plaka": "34 RENT 01", "marka": "Renault", "model": "Megane", "yil": 2022, "renk": "Platin Gümüş", "guncelKm": 35000, "alisKm": 0, "sigortaBitisTarihi": "2026-05-15", "vizeBitisTarihi": "2026-05-15", "bakimYapildigiKm": 30000},
            {"plaka": "34 EGE 34", "marka": "Fiat", "model": "Egea Sedan", "yil": 2023, "renk": "Opak Beyaz", "guncelKm": 48300, "alisKm": 0, "sigortaBitisTarihi": "2026-11-20", "vizeBitisTarihi": "2026-11-20", "bakimYapildigiKm": 40000},
            {"plaka": "35 DAC 90", "marka": "Dacia", "model": "Duster", "yil": 2022, "renk": "Kum Beji", "guncelKm": 62400, "alisKm": 12000, "sigortaBitisTarihi": "2026-09-08", "vizeBitisTarihi": "2026-09-08", "bakimYapildigiKm": 60000},
            {"plaka": "06 PGT 300", "marka": "Peugeot", "model": "3008", "yil": 2023, "renk": "İnci Kırmızı", "guncelKm": 22100, "alisKm": 0, "sigortaBitisTarihi": "2026-07-22", "vizeBitisTarihi": "2026-07-22", "bakimYapildigiKm": 20000},
            {"plaka": "34 TOY 88", "marka": "Toyota", "model": "Corolla Hybrid", "yil": 2022, "renk": "Kar Beyazı", "guncelKm": 51200, "alisKm": 0, "sigortaBitisTarihi": "2027-02-14", "vizeBitisTarihi": "2027-02-14", "bakimYapildigiKm": 50000},
            {"plaka": "34 CIV 16", "marka": "Honda", "model": "Civic", "yil": 2023, "renk": "Kozmos Gri", "guncelKm": 18400, "alisKm": 0, "sigortaBitisTarihi": "2026-08-30", "vizeBitisTarihi": "2026-08-30", "bakimYapildigiKm": 10000},
            {"plaka": "34 HYU 55", "marka": "Hyundai", "model": "i20", "yil": 2023, "renk": "Buz Mavisi", "guncelKm": 28600, "alisKm": 0, "sigortaBitisTarihi": "2026-10-12", "vizeBitisTarihi": "2026-10-12", "bakimYapildigiKm": 20000},
            {"plaka": "34 TAY 911", "marka": "Porsche", "model": "Taycan 4S", "yil": 2024, "renk": "Metalik Mavi", "guncelKm": 3100, "alisKm": 0, "sigortaBitisTarihi": "2027-05-01", "vizeBitisTarihi": "2027-05-01", "bakimYapildigiKm": 0},
            {"plaka": "34 SKO 13", "marka": "Skoda", "model": "Octavia", "yil": 2023, "renk": "Grafıt Gri", "guncelKm": 14200, "alisKm": 0, "sigortaBitisTarihi": "2026-10-25", "vizeBitisTarihi": "2026-10-25", "bakimYapildigiKm": 10000},
            {"plaka": "34 KIA 44", "marka": "Kia", "model": "Sportage", "yil": 2023, "renk": "Çelik Gümüş", "guncelKm": 19500, "alisKm": 0, "sigortaBitisTarihi": "2026-09-12", "vizeBitisTarihi": "2026-09-12", "bakimYapildigiKm": 15000},
            {"plaka": "34 CLI 85", "marka": "Renault", "model": "Clio", "yil": 2023, "renk": "Alev Kırmızı", "guncelKm": 31000, "alisKm": 0, "sigortaBitisTarihi": "2026-08-14", "vizeBitisTarihi": "2026-08-14", "bakimYapildigiKm": 30000},
            {"plaka": "34 CRS 12", "marka": "Opel", "model": "Corsa", "yil": 2022, "renk": "Volkan Siyah", "guncelKm": 38500, "alisKm": 10000, "sigortaBitisTarihi": "2026-07-30", "vizeBitisTarihi": "2026-07-30", "bakimYapildigiKm": 30000},
            {"plaka": "34 FOC 55", "marka": "Ford", "model": "Focus", "yil": 2022, "renk": "Derin Mavi", "guncelKm": 46000, "alisKm": 0, "sigortaBitisTarihi": "2026-11-05", "vizeBitisTarihi": "2026-11-05", "bakimYapildigiKm": 40000},
            {"plaka": "34 QAS 77", "marka": "Nissan", "model": "Qashqai", "yil": 2022, "renk": "Manyetık Gri", "guncelKm": 53000, "alisKm": 15000, "sigortaBitisTarihi": "2026-12-20", "vizeBitisTarihi": "2026-12-20", "bakimYapildigiKm": 50000},
            {"plaka": "34 AUD 03", "marka": "Audi", "model": "Q3 SUV", "yil": 2023, "renk": "Mıtos Siyah", "guncelKm": 12800, "alisKm": 0, "sigortaBitisTarihi": "2026-10-18", "vizeBitisTarihi": "2026-10-18", "bakimYapildigiKm": 10000},
            {"plaka": "34 CUP 90", "marka": "Cupra", "model": "Formentor", "yil": 2023, "renk": "Mat Gri", "guncelKm": 15000, "alisKm": 0, "sigortaBitisTarihi": "2027-01-15", "vizeBitisTarihi": "2027-01-15", "bakimYapildigiKm": 10000}
        ]
        
        vehicles = []
        for v_info in vehicles_data:
            v = Vehicle(
                id=str(uuid.uuid4()),
                plaka=v_info["plaka"],
                marka=v_info["marka"],
                model=v_info["model"],
                yil=v_info["yil"],
                renk=v_info["renk"],
                guncelKm=v_info["guncelKm"],
                alisKm=v_info["alisKm"],
                sigortaBitisTarihi=v_info["sigortaBitisTarihi"],
                vizeBitisTarihi=v_info["vizeBitisTarihi"],
                bakimYapildigiKm=v_info["bakimYapildigiKm"]
            )
            tenant_session.add(v)
            vehicles.append(v)
        
        tenant_session.commit()
        print(f"{len(vehicles)} araç eklendi.")

        # 2. KİRALAMALAR (Aktif, Geçmiş ve Gelecek Kiralamalar)
        today = datetime.now()
        rentals_data = [
            {
                "vehicle": vehicles[0], "musteri": "Ahmet Yılmaz", "baslangic": (today - timedelta(days=10)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=5)).strftime('%Y-%m-%d'), "vKm": 12000, "aKm": 13500, "fiyat": 7500, "paraBirimi": "₺", "kurum": "Yılmaz Holding"
            },
            {
                "vehicle": vehicles[0], "musteri": "John Smith", "baslangic": (today - timedelta(days=25)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=18)).strftime('%Y-%m-%d'), "vKm": 10500, "aKm": 12000, "fiyat": 650, "paraBirimi": "€", "kurum": "Smith & Partners"
            },
            {
                "vehicle": vehicles[1], "musteri": "Mehmet Demir", "baslangic": (today - timedelta(days=3)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=2)).strftime('%Y-%m-%d'), "vKm": 41500, "aKm": 0, "fiyat": 10000, "paraBirimi": "₺", "kurum": "Demir İnşaat" # Şu an kirada
            },
            {
                "vehicle": vehicles[1], "musteri": "David Miller", "baslangic": (today - timedelta(days=12)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=6)).strftime('%Y-%m-%d'), "vKm": 40000, "aKm": 41500, "fiyat": 480, "paraBirimi": "$", "kurum": "Miller Logistics"
            },
            {
                "vehicle": vehicles[2], "musteri": "Hans Schmidt", "baslangic": (today - timedelta(days=5)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=3)).strftime('%Y-%m-%d'), "vKm": 4200, "aKm": 0, "fiyat": 720, "paraBirimi": "€", "kurum": "Schmidt Group" # Şu an kirada
            },
            {
                "vehicle": vehicles[3], "musteri": "Ayşe Kaya", "baslangic": (today - timedelta(days=20)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=15)).strftime('%Y-%m-%d'), "vKm": 82000, "aKm": 84000, "fiyat": 6000, "paraBirimi": "₺", "kurum": "Kaya Mimarlık"
            },
            {
                "vehicle": vehicles[4], "musteri": "Caner Öz", "baslangic": (today - timedelta(days=2)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=5)).strftime('%Y-%m-%d'), "vKm": 34500, "aKm": 0, "fiyat": 8400, "paraBirimi": "₺", "kurum": "Öz Gıda" # Şu an kirada
            },
            {
                "vehicle": vehicles[5], "musteri": "Selin Şahin", "baslangic": (today - timedelta(days=15)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=5)).strftime('%Y-%m-%d'), "vKm": 42000, "aKm": 44500, "fiyat": 12000, "paraBirimi": "₺", "kurum": "Şahin Teknoloji"
            },
            {
                "vehicle": vehicles[6], "musteri": "Kaan Karaca", "baslangic": (today - timedelta(days=1)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=6)).strftime('%Y-%m-%d'), "vKm": 61200, "aKm": 0, "fiyat": 10500, "paraBirimi": "₺", "kurum": "Karaca Otomotiv" # Şu an kirada
            },
            {
                "vehicle": vehicles[8], "musteri": "Zeynep Yurt", "baslangic": (today - timedelta(days=30)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=27)).strftime('%Y-%m-%d'), "vKm": 49000, "aKm": 49800, "fiyat": 3600, "paraBirimi": "₺", "kurum": "" # Bireysel
            },
            {
                "vehicle": vehicles[9], "musteri": "Ali Aslan", "baslangic": (today - timedelta(days=8)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=1)).strftime('%Y-%m-%d'), "vKm": 16200, "aKm": 17800, "fiyat": 9100, "paraBirimi": "₺", "kurum": "Aslan Lojistik"
            },
            {
                "vehicle": vehicles[10], "musteri": "Buse Çelik", "baslangic": (today - timedelta(days=4)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=1)).strftime('%Y-%m-%d'), "vKm": 27200, "aKm": 0, "fiyat": 6500, "paraBirimi": "₺", "kurum": "" # Bireysel
            },
            {
                "vehicle": vehicles[11], "musteri": "Hakan Sabancı", "baslangic": (today + timedelta(days=2)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=5)).strftime('%Y-%m-%d'), "vKm": 3100, "aKm": 0, "fiyat": 2500, "paraBirimi": "€", "kurum": "Sabancı Holding" # İleri tarihli rezervasyon
            },
            {
                "vehicle": vehicles[11], "musteri": "George Clooney", "baslangic": (today - timedelta(days=12)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=8)).strftime('%Y-%m-%d'), "vKm": 2100, "aKm": 3100, "fiyat": 3000, "paraBirimi": "$", "kurum": "Hollywood Productions"
            },
            {
                "vehicle": vehicles[12], "musteri": "Murat Yıldırım", "baslangic": (today - timedelta(days=7)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=1)).strftime('%Y-%m-%d'), "vKm": 13000, "aKm": 14100, "fiyat": 9600, "paraBirimi": "₺", "kurum": "" # Bireysel
            },
            {
                "vehicle": vehicles[14], "musteri": "Gamze Özçelik", "baslangic": (today - timedelta(days=5)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=3)).strftime('%Y-%m-%d'), "vKm": 30100, "aKm": 0, "fiyat": 6400, "paraBirimi": "₺", "kurum": "Gamze Vakfı" # Şu an kirada
            },
            {
                "vehicle": vehicles[16], "musteri": "Serkan Bolat", "baslangic": (today - timedelta(days=4)).strftime('%Y-%m-%d'), 
                "bitis": (today - timedelta(days=1)).strftime('%Y-%m-%d'), "vKm": 45200, "aKm": 45950, "fiyat": 4800, "paraBirimi": "₺", "kurum": "Art Life Mimarlık"
            },
            {
                "vehicle": vehicles[17], "musteri": "Eda Yıldız", "baslangic": (today - timedelta(days=3)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=4)).strftime('%Y-%m-%d'), "vKm": 52100, "aKm": 0, "fiyat": 11200, "paraBirimi": "₺", "kurum": "" # Bireysel
            },
            {
                "vehicle": vehicles[19], "musteri": "Tarkan Tevetoğlu", "baslangic": (today + timedelta(days=4)).strftime('%Y-%m-%d'), 
                "bitis": (today + timedelta(days=10)).strftime('%Y-%m-%d'), "vKm": 15000, "aKm": 0, "fiyat": 1500, "paraBirimi": "€", "kurum": "Hitt Müzik" # İleri tarihli rezervasyon
            }
        ]

        for r_info in rentals_data:
            v = r_info["vehicle"]
            d1 = datetime.strptime(r_info["baslangic"], '%Y-%m-%d')
            d2 = datetime.strptime(r_info["bitis"], '%Y-%m-%d')
            days = max(1, (d2 - d1).days)
            r = Rental(
                id=str(uuid.uuid4()),
                arac_id=v.id,
                plaka=v.plaka,
                marka=v.marka,
                model=v.model,
                musteriAdi=r_info["musteri"],
                isim=r_info["musteri"].split()[0],
                soyisim=r_info["musteri"].split()[1] if len(r_info["musteri"].split()) > 1 else "",
                kurumAdi=r_info.get("kurum", ""),
                baslangicTarihi=r_info["baslangic"],
                bitisTarihi=r_info["bitis"],
                kiralamaSuresi=days,
                verilisteKm=r_info["vKm"],
                alinistaKm=r_info["aKm"],
                kullanilanKm=max(0, r_info["aKm"] - r_info["vKm"]),
                gunlukFiyat=float(r_info["fiyat"] / days),
                toplamFiyat=r_info["fiyat"],
                kar=r_info["fiyat"],
                paraBirimi=r_info.get("paraBirimi", "₺")
            )
            tenant_session.add(r)
        
        # 3. SERVİS KAYITLARI (Bakım ve Tamir Kayıtları)
        service_data = [
            {"vehicle": vehicles[0], "km": 15000, "ucret": 4500, "yer": "Mercedes Yetkili Servisi", "notlar": "15.000 KM periyodik bakımı tamamlandı.", "paraBirimi": "₺"},
            {"vehicle": vehicles[0], "km": 10000, "ucret": 150, "yer": "Mercedes-Benz Berlin", "notlar": "Ön silecekler ve cam suyu değişti.", "paraBirimi": "€"},
            {"vehicle": vehicles[1], "km": 40000, "ucret": 6200, "yer": "Bosch Car Service", "notlar": "Ön-arka fren balataları yenilendi, diskler taşlandı.", "paraBirimi": "₺"},
            {"vehicle": vehicles[1], "km": 20000, "ucret": 200, "yer": "BMW Premium Service", "notlar": "Motor yağı ve filtre seti değişti.", "paraBirimi": "$"},
            {"vehicle": vehicles[3], "km": 80000, "ucret": 15500, "yer": "Volkswagen Özel Servisi", "notlar": "Ağır bakım yapıldı. Triger seti, devirdaim ve filtreler değişti.", "paraBirimi": "₺"},
            {"vehicle": vehicles[5], "km": 40000, "ucret": 3800, "yer": "Fiat Yetkili Servisi", "notlar": "40.000 KM periyodik yağ bakımı yapıldı.", "paraBirimi": "₺"},
            {"vehicle": vehicles[6], "km": 60000, "ucret": 8900, "yer": "Renault-Dacia Özel Servisi", "notlar": "Baskı balata seti ve şanzıman yağı değişti.", "paraBirimi": "₺"},
            {"vehicle": vehicles[8], "km": 50000, "ucret": 4200, "yer": "Toyota Yetkili Servisi", "notlar": "50.000 KM hibrit sistem kontrolü ve periyodik bakım.", "paraBirimi": "₺"},
            {"vehicle": vehicles[11], "km": 2500, "ucret": 450, "yer": "Porsche Stuttgart", "notlar": "İlk kontrol ve yazılım güncellemesi.", "paraBirimi": "€"},
            {"vehicle": vehicles[14], "km": 30000, "ucret": 3100, "yer": "Renault Yetkili Servisi", "notlar": "30.000 KM periyodik motor yağı ve buji değişimi.", "paraBirimi": "₺"},
            {"vehicle": vehicles[16], "km": 45000, "ucret": 5800, "yer": "Ford Özel Servisi", "notlar": "Ön amortisörler ve takozları yenilendi.", "paraBirimi": "₺"}
        ]

        for s_info in service_data:
            v = s_info["vehicle"]
            s = Service(
                id=str(uuid.uuid4()),
                arac_id=v.id,
                plaka=v.plaka,
                km=s_info["km"],
                ucret=s_info["ucret"],
                yer=s_info["yer"],
                tarih=(today - timedelta(days=60)).strftime('%Y-%m-%d'),
                notlar=s_info["notlar"],
                paraBirimi=s_info.get("paraBirimi", "₺")
            )
            tenant_session.add(s)

        # 4. GİDERLER (Sigorta, Vize, vb.)
        expense_data = [
            {"vehicle": vehicles[0], "tip": "Sigorta", "tutar": 12000, "notlar": "Allianz Genişletilmiş Kasko Yenileme", "paraBirimi": "₺"},
            {"vehicle": vehicles[0], "tip": "Sigorta", "tutar": 350, "notlar": "Avrupa Yeşil Kart Sigortası", "paraBirimi": "€"},
            {"vehicle": vehicles[1], "tip": "Vize", "tutar": 1850, "notlar": "TÜVTÜRK periyodik araç muayenesi geçildi", "paraBirimi": "₺"},
            {"vehicle": vehicles[1], "tip": "Sigorta", "tutar": 250, "notlar": "International Roadside Assistance Premium", "paraBirimi": "$"},
            {"vehicle": vehicles[2], "tip": "Sigorta", "tutar": 5500, "notlar": "Zorunlu Trafik Sigortası Poliçesi", "paraBirimi": "₺"},
            {"vehicle": vehicles[3], "tip": "Sigorta", "tutar": 9800, "notlar": "Axa Kasko Sigortası Yenileme", "paraBirimi": "₺"},
            {"vehicle": vehicles[5], "tip": "Sigorta", "tutar": 4200, "notlar": "Eureko Zorunlu Trafik Sigortası", "paraBirimi": "₺"},
            {"vehicle": vehicles[11], "tip": "Sigorta", "tutar": 1200, "notlar": "Porsche Premium Kasko ve Mini Hasar Güvencesi", "paraBirimi": "€"},
            {"vehicle": vehicles[12], "tip": "Sigorta", "tutar": 8500, "notlar": "Allianz Kasko Sigortası Poliçesi", "paraBirimi": "₺"},
            {"vehicle": vehicles[13], "tip": "Sigorta", "tutar": 5100, "notlar": "Axa Zorunlu Trafik Sigortası", "paraBirimi": "₺"},
            {"vehicle": vehicles[14], "tip": "Sigorta", "tutar": 6500, "notlar": "Mapfre Kasko Sigortası Poliçesi", "paraBirimi": "₺"},
            {"vehicle": vehicles[19], "tip": "Sigorta", "tutar": 450, "notlar": "Anadolu Sigorta Genişletilmiş Kasko Yenileme", "paraBirimi": "€"}
        ]

        for e_info in expense_data:
            v = e_info["vehicle"]
            e = VehicleExpense(
                id=str(uuid.uuid4()),
                arac_id=v.id,
                plaka=v.plaka,
                gider_tipi=e_info["tip"],
                tutar=e_info["tutar"],
                tarih=(today - timedelta(days=30)).strftime('%Y-%m-%d'),
                notlar=e_info["notlar"],
                paraBirimi=e_info.get("paraBirimi", "₺")
            )
            tenant_session.add(e)

        tenant_session.commit()
        print("Tüm örnek veriler başarıyla eklendi.")

if __name__ == "__main__":
    clear_data()
    seed_data()
