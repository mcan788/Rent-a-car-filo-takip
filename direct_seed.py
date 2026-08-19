import pyodbc
import uuid
from datetime import datetime

conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=RENT_A_CAR_DEMO_DB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes')
cursor = conn.cursor()
cursor.execute('DELETE FROM vehicle_expenses; DELETE FROM services; DELETE FROM rentals; DELETE FROM vehicles;')

vehicles_data = [
    {'plaka': '34 ABC 001', 'marka': 'Mercedes-Benz', 'model': 'C200', 'yil': 2023, 'renk': 'Metalik Gri', 'guncelKm': 18200, 'alisKm': 0, 'sigortaBitisTarihi': '2026-12-01', 'vizeBitisTarihi': '2026-06-15', 'bakimYapildigiKm': 15000},
    {'plaka': '06 XYZ 99', 'marka': 'BMW', 'model': '320i', 'yil': 2022, 'renk': 'Siyah', 'guncelKm': 42000, 'alisKm': 5000, 'sigortaBitisTarihi': '2027-01-20', 'vizeBitisTarihi': '2026-08-10', 'bakimYapildigiKm': 40000},
    {'plaka': '35 TR 3535', 'marka': 'Audi', 'model': 'A4', 'yil': 2024, 'renk': 'Beyaz', 'guncelKm': 5200, 'alisKm': 0, 'sigortaBitisTarihi': '2027-04-10', 'vizeBitisTarihi': '2027-04-10', 'bakimYapildigiKm': 0},
    {'plaka': '07 ANT 07', 'marka': 'Volkswagen', 'model': 'Passat', 'yil': 2021, 'renk': 'Okyanus Mavi', 'guncelKm': 89500, 'alisKm': 20000, 'sigortaBitisTarihi': '2026-10-05', 'vizeBitisTarihi': '2026-03-20', 'bakimYapildigiKm': 80000},
    {'plaka': '34 RENT 01', 'marka': 'Renault', 'model': 'Megane', 'yil': 2022, 'renk': 'Platin Gümüs', 'guncelKm': 35000, 'alisKm': 0, 'sigortaBitisTarihi': '2026-05-15', 'vizeBitisTarihi': '2026-05-15', 'bakimYapildigiKm': 30000},
    {'plaka': '34 EGE 34', 'marka': 'Fiat', 'model': 'Egea Sedan', 'yil': 2023, 'renk': 'Opak Beyaz', 'guncelKm': 48300, 'alisKm': 0, 'sigortaBitisTarihi': '2026-11-20', 'vizeBitisTarihi': '2026-11-20', 'bakimYapildigiKm': 40000},
    {'plaka': '35 DAC 90', 'marka': 'Dacia', 'model': 'Duster', 'yil': 2022, 'renk': 'Kum Beji', 'guncelKm': 62400, 'alisKm': 12000, 'sigortaBitisTarihi': '2026-09-08', 'vizeBitisTarihi': '2026-09-08', 'bakimYapildigiKm': 60000},
    {'plaka': '06 PGT 300', 'marka': 'Peugeot', 'model': '3008', 'yil': 2023, 'renk': 'Inci Kirmizi', 'guncelKm': 22100, 'alisKm': 0, 'sigortaBitisTarihi': '2026-07-22', 'vizeBitisTarihi': '2026-07-22', 'bakimYapildigiKm': 20000},
    {'plaka': '34 TOY 88', 'marka': 'Toyota', 'model': 'Corolla Hybrid', 'yil': 2022, 'renk': 'Kar Beyazi', 'guncelKm': 51200, 'alisKm': 0, 'sigortaBitisTarihi': '2027-02-14', 'vizeBitisTarihi': '2027-02-14', 'bakimYapildigiKm': 50000},
    {'plaka': '34 CIV 16', 'marka': 'Honda', 'model': 'Civic', 'yil': 2023, 'renk': 'Kozmos Gri', 'guncelKm': 18400, 'alisKm': 0, 'sigortaBitisTarihi': '2026-08-30', 'vizeBitisTarihi': '2026-08-30', 'bakimYapildigiKm': 10000},
    {'plaka': '34 HYU 55', 'marka': 'Hyundai', 'model': 'i20', 'yil': 2023, 'renk': 'Buz Mavisi', 'guncelKm': 28600, 'alisKm': 0, 'sigortaBitisTarihi': '2026-10-12', 'vizeBitisTarihi': '2026-10-12', 'bakimYapildigiKm': 20000},
    {'plaka': '34 TAY 911', 'marka': 'Porsche', 'model': 'Taycan 4S', 'yil': 2024, 'renk': 'Metalik Mavi', 'guncelKm': 3100, 'alisKm': 0, 'sigortaBitisTarihi': '2027-05-01', 'vizeBitisTarihi': '2027-05-01', 'bakimYapildigiKm': 0},
    {'plaka': '34 SKO 13', 'marka': 'Skoda', 'model': 'Octavia', 'yil': 2023, 'renk': 'Grafit Gri', 'guncelKm': 14200, 'alisKm': 0, 'sigortaBitisTarihi': '2026-10-25', 'vizeBitisTarihi': '2026-10-25', 'bakimYapildigiKm': 10000},
    {'plaka': '34 KIA 44', 'marka': 'Kia', 'model': 'Sportage', 'yil': 2023, 'renk': 'Celik Gümüs', 'guncelKm': 19500, 'alisKm': 0, 'sigortaBitisTarihi': '2026-09-12', 'vizeBitisTarihi': '2026-09-12', 'bakimYapildigiKm': 15000},
    {'plaka': '34 CLI 85', 'marka': 'Renault', 'model': 'Clio', 'yil': 2023, 'renk': 'Alev Kirmizi', 'guncelKm': 31000, 'alisKm': 0, 'sigortaBitisTarihi': '2026-08-14', 'vizeBitisTarihi': '2026-08-14', 'bakimYapildigiKm': 30000},
    {'plaka': '34 CRS 12', 'marka': 'Opel', 'model': 'Corsa', 'yil': 2022, 'renk': 'Volkan Siyah', 'guncelKm': 38500, 'alisKm': 10000, 'sigortaBitisTarihi': '2026-07-30', 'vizeBitisTarihi': '2026-07-30', 'bakimYapildigiKm': 30000},
    {'plaka': '34 FOC 55', 'marka': 'Ford', 'model': 'Focus', 'yil': 2022, 'renk': 'Derin Mavi', 'guncelKm': 46000, 'alisKm': 0, 'sigortaBitisTarihi': '2026-11-05', 'vizeBitisTarihi': '2026-11-05', 'bakimYapildigiKm': 40000},
    {'plaka': '34 QAS 77', 'marka': 'Nissan', 'model': 'Qashqai', 'yil': 2022, 'renk': 'Manyetik Gri', 'guncelKm': 53000, 'alisKm': 15000, 'sigortaBitisTarihi': '2026-12-20', 'vizeBitisTarihi': '2026-12-20', 'bakimYapildigiKm': 50000},
    {'plaka': '34 AUD 03', 'marka': 'Audi', 'model': 'Q3 SUV', 'yil': 2023, 'renk': 'Mitos Siyah', 'guncelKm': 12800, 'alisKm': 0, 'sigortaBitisTarihi': '2026-10-18', 'vizeBitisTarihi': '2026-10-18', 'bakimYapildigiKm': 10000},
    {'plaka': '34 CUP 90', 'marka': 'Cupra', 'model': 'Formentor', 'yil': 2023, 'renk': 'Mat Gri', 'guncelKm': 15000, 'alisKm': 0, 'sigortaBitisTarihi': '2027-01-15', 'vizeBitisTarihi': '2027-01-15', 'bakimYapildigiKm': 10000}
]

query = "INSERT INTO vehicles (id, plaka, marka, model, yil, renk, guncelKm, alisKm, sigortaBitisTarihi, vizeBitisTarihi, bakimYapildigiKm, is_active, is_deleted, is_in_maintenance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"

for v in vehicles_data:
    cursor.execute(query, (str(uuid.uuid4()), v['plaka'], v['marka'], v['model'], v['yil'], v['renk'], v['guncelKm'], v['alisKm'], v['sigortaBitisTarihi'], v['vizeBitisTarihi'], v['bakimYapildigiKm'], 1, 0, 0))

conn.commit()
print('SUCCESSFULLY ADDED 20 VEHICLES TO RENT_A_CAR_DEMO_DB!')
