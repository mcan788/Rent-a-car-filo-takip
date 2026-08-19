import os
import random
from datetime import datetime, timedelta
from app import app
from extensions import get_tenant_session

from sqlalchemy import text

def seed_multi_currency_data():
    subdomain = 'RentACarDemo'
    
    with app.app_context():
        ts = get_tenant_session(subdomain)
        if not ts:
            print("Could not connect to tenant db!")
            return
            
        try:
            # Get all vehicles
            vehicles = ts.execute(text("SELECT id, plaka, gunlukUcret FROM vehicles")).fetchall()
            
            if not vehicles:
                print("No vehicles found!")
                return
                
            currencies = ['₺', '$', '€']
            customers = [
                ("Michael Johnson", "English", "555-0102"),
                ("Hans Schmidt", "German", "555-0103"),
                ("Elena Rossi", "Italian", "555-0104"),
                ("Ahmet Yılmaz", "Turkish", "555-0105"),
                ("John Doe", "American", "555-0106")
            ]
            
            expense_types = ['Servis (Bakım)', 'Yakıt', 'Sigorta', 'Hasar', 'Yıkama']
            
            # Start date 3 months ago
            start_date = datetime.now() - timedelta(days=90)
            
            for v in vehicles:
                v_id, plaka, base_price = v
                base_price = float(base_price) if base_price else 1000.0
                
                # Add 3-5 rentals for each vehicle in different currencies
                num_rentals = random.randint(3, 5)
                
                for _ in range(num_rentals):
                    currency = random.choice(currencies)
                    customer = random.choice(customers)
                    
                    # Adjust price based on currency
                    if currency == '$':
                        daily_price = base_price / 32.0
                    elif currency == '€':
                        daily_price = base_price / 35.0
                    else:
                        daily_price = base_price
                        
                    days = random.randint(2, 10)
                    total_price = daily_price * days
                    
                    r_start = start_date + timedelta(days=random.randint(0, 80))
                    r_end = r_start + timedelta(days=days)
                    
                    import uuid
                    ts.execute(text("""
                        INSERT INTO rentals (
                            id, arac_id, plaka, isim, soyisim, musteriAdi, uyruk, tcKimlik, 
                            baslangicTarihi, bitisTarihi, kiralamaSuresi,
                            paraBirimi, gunlukFiyat, toplamFiyat,
                            alinistaKm, verilisteKm, kullanilanKm, kar,
                            kabis_kiralama_status, kabis_teslim_status
                        ) VALUES (:id, :arac_id, :plaka, :isim, :soyisim, :musteriAdi, :uyruk, :tcKimlik, :baslangicTarihi, :bitisTarihi, :kiralamaSuresi, :paraBirimi, :gunlukFiyat, :toplamFiyat, :alinistaKm, :verilisteKm, :kullanilanKm, :kar, 'bekliyor', 'bekliyor')
                    """), {
                        "id": str(uuid.uuid4()),
                        "arac_id": v_id, "plaka": plaka, "isim": customer[0].split()[0], "soyisim": customer[0].split()[-1], "musteriAdi": customer[0], "uyruk": customer[1], "tcKimlik": customer[2],
                        "baslangicTarihi": r_start.strftime('%Y-%m-%d'), "bitisTarihi": r_end.strftime('%Y-%m-%d'), "kiralamaSuresi": days,
                        "paraBirimi": currency, "gunlukFiyat": daily_price, "toplamFiyat": total_price,
                        "alinistaKm": 10000, "verilisteKm": 10000 + (days * 50), "kullanilanKm": days * 50, "kar": total_price * 0.7
                    })
                    
                    # Add 1-2 expenses for this vehicle
                    num_expenses = random.randint(1, 2)
                    for _ in range(num_expenses):
                        e_type = random.choice(expense_types)
                        e_currency = random.choice(currencies)
                        
                        if e_currency == '$':
                            e_amount = random.uniform(50, 300)
                        elif e_currency == '€':
                            e_amount = random.uniform(50, 300)
                        else:
                            e_amount = random.uniform(1500, 5000)
                            
                        e_date = r_start - timedelta(days=random.randint(1, 10))
                        
                        ts.execute(text("""
                            INSERT INTO vehicle_expenses (
                                id, arac_id, plaka, gider_tipi, tutar, paraBirimi, tarih, notlar
                            ) VALUES (:id, :arac_id, :plaka, :gider_tipi, :tutar, :paraBirimi, :tarih, :notlar)
                        """), {
                            "id": str(uuid.uuid4()),
                            "arac_id": v_id, "plaka": plaka, "gider_tipi": e_type, "tutar": e_amount, "paraBirimi": e_currency, "tarih": e_date.strftime('%Y-%m-%d'), 
                            "notlar": f"Periyodik {e_type} gideri"
                        })
            
            ts.commit()
            print("Successfully added multi-currency rentals and expenses!")
            
        except Exception as e:
            ts.rollback()
            print(f"Error: {e}")
        finally:
            ts.close()

if __name__ == '__main__':
    seed_multi_currency_data()
