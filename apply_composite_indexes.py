from app import create_app
from extensions import db, get_tenant_session
from models import Company, Rental
import sqlalchemy

app = create_app()

def apply_indexes():
    with app.app_context():
        # Get all companies
        companies = Company.query.all()
        print(f"[{len(companies)}] Tenant veritabanı bulundu. İndeksler uygulanıyor...")
        
        for company in companies:
            if not company.subdomain:
                continue
                
            print(f"-> Tenant: {company.subdomain} isleniyor...")
            ts = get_tenant_session(company.subdomain)
            if not ts:
                print(f"   [!] {company.subdomain} icin veritabani baglantisi saglanamadi. Geciliyor...")
                continue
            
            # Use the tenant's engine to execute raw SQL for index creation
            engine = ts.get_bind()
            
            indexes_to_create = [
                "CREATE NONCLUSTERED INDEX idx_rental_plaka_baslangic ON rentals (plaka, baslangicTarihi)",
                "CREATE NONCLUSTERED INDEX idx_rental_plaka_bitis ON rentals (plaka, bitisTarihi)"
            ]
            
            with engine.connect() as conn:
                for idx_query in indexes_to_create:
                    try:
                        conn.execute(sqlalchemy.text(idx_query))
                        print(f"   [+] Basarili: {idx_query.split()[3]}")
                    except sqlalchemy.exc.ProgrammingError as e:
                        # Index likely already exists
                        if 'already exists' in str(e) or 'The operation failed because an index' in str(e):
                            print(f"   [-] Atlandi (Zaten Var): {idx_query.split()[3]}")
                        else:
                            print(f"   [!] Hata ({idx_query.split()[3]}): {e}")
                    except Exception as e:
                        print(f"   [!] Hata ({idx_query.split()[3]}): {e}")
                        
                conn.commit()

if __name__ == '__main__':
    apply_indexes()
    print("\n[OK] Tum tenant veritabanlarina indeksleme islemi tamamlandi.")
    import os
    os._exit(0)
