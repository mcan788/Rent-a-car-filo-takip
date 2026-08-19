import sys
import os
sys.path.append('C:\\SUNUCU_PAKETI\\RentACar_Sistem')

from app import create_app
from extensions import get_tenant_session
from models import Vehicle

app = create_app()

real_vehicles = [
    {"plaka": "34ABC123", "marka": "Renault", "model": "Clio", "yil": 2023, "renk": "Beyaz", "guncelKm": 15400, "gunlukUcret": 800.0, "is_active": True},
    {"plaka": "34DEF456", "marka": "Fiat", "model": "Egea", "yil": 2022, "renk": "Kursun Gri", "guncelKm": 42000, "gunlukUcret": 750.0, "is_active": True},
    {"plaka": "34GHI789", "marka": "Toyota", "model": "Corolla", "yil": 2023, "renk": "Inci Beyazi", "guncelKm": 12000, "gunlukUcret": 1100.0, "is_active": True},
    {"plaka": "06JKL012", "marka": "Volkswagen", "model": "Passat", "yil": 2021, "renk": "Siyah", "guncelKm": 75000, "gunlukUcret": 1600.0, "is_active": True},
    {"plaka": "35MNO345", "marka": "Ford", "model": "Focus", "yil": 2022, "renk": "Mavi", "guncelKm": 31000, "gunlukUcret": 950.0, "is_active": True},
    {"plaka": "34PQR678", "marka": "Peugeot", "model": "3008", "yil": 2023, "renk": "Bakir", "guncelKm": 18500, "gunlukUcret": 1800.0, "is_active": True},
    {"plaka": "34STU901", "marka": "Dacia", "model": "Duster", "yil": 2022, "renk": "Haki", "guncelKm": 54000, "gunlukUcret": 850.0, "is_active": True},
    {"plaka": "07VWX234", "marka": "Hyundai", "model": "i20", "yil": 2023, "renk": "Kirmizi", "guncelKm": 8500, "gunlukUcret": 750.0, "is_active": True},
    {"plaka": "34YZA567", "marka": "Skoda", "model": "Octavia", "yil": 2022, "renk": "Beyaz", "guncelKm": 28000, "gunlukUcret": 1200.0, "is_active": True},
    {"plaka": "34BCD890", "marka": "Honda", "model": "Civic", "yil": 2021, "renk": "Gumus Gri", "guncelKm": 68000, "gunlukUcret": 1050.0, "is_active": True},
    {"plaka": "16EFG123", "marka": "Nissan", "model": "Qashqai", "yil": 2022, "renk": "Beyaz", "guncelKm": 36000, "gunlukUcret": 1650.0, "is_active": True},
    {"plaka": "34HIJ456", "marka": "Mercedes-Benz", "model": "C200d", "yil": 2021, "renk": "Siyah", "guncelKm": 82000, "gunlukUcret": 3500.0, "is_active": True},
    {"plaka": "34KLM789", "marka": "BMW", "model": "320i", "yil": 2023, "renk": "Lacivert", "guncelKm": 14000, "gunlukUcret": 3800.0, "is_active": True},
    {"plaka": "41NOP012", "marka": "Audi", "model": "A3", "yil": 2022, "renk": "Beyaz", "guncelKm": 25000, "gunlukUcret": 2200.0, "is_active": True},
    {"plaka": "34QRS345", "marka": "Kia", "model": "Sportage", "yil": 2023, "renk": "Yesil", "guncelKm": 9000, "gunlukUcret": 1900.0, "is_active": True}
]

with app.app_context():
    session = get_tenant_session('RentACarDemo')
    if not session:
        print("Failed to get tenant session for RentACarDemo")
        sys.exit(1)
        
    try:
        added_count = 0
        for v in real_vehicles:
            # Check if vehicle exists
            exists = session.query(Vehicle).filter_by(plaka=v['plaka']).first()
            if not exists:
                new_v = Vehicle(**v)
                session.add(new_v)
                added_count += 1
                
        session.commit()
        print(f"Successfully added {added_count} vehicles.")
    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
    finally:
        session.close()
