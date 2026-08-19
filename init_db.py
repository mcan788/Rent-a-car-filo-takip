from app import create_app
from extensions import db, create_tenant_database
from models import Company, User
from sqlalchemy import create_engine, event, text
import urllib.parse
import time

def init_db():
    app = create_app()
    with app.app_context():
        print("=" * 50)
        print("ZYRONOVA Multi-Tenant Veritabanı Kurulumu")
        print("=" * 50)
        
        print("\n[0/4] Master ve Tenant Veritabanları kontrol ediliyor...")
        server = app.config['DB_SERVER']
        driver = app.config['DB_DRIVER']
        master_db_name = "ZYRONOVA_MASTER"
        tenant_db_name = "www"
        
        # Robust connection to 'master' to drop and create our DB
        params = urllib.parse.quote_plus(f"DRIVER={{{driver}}};SERVER={server};DATABASE=master;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes")
        sys_url = f"mssql+pyodbc:///?odbc_connect={params}"
        sys_engine = create_engine(sys_url, isolation_level="AUTOCOMMIT")
        
        with sys_engine.connect() as conn:
            # Drop ZYRONOVA_MASTER if exists to avoid schema mismatch
            result = conn.execute(text(f"SELECT DB_ID('{master_db_name}')"))
            if result.scalar() is not None:
                print(f"  [!] Eski {master_db_name} veritabanı tespit edildi. Temizleniyor...")
                try:
                    conn.execute(text(f"ALTER DATABASE [{master_db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"))
                    conn.execute(text(f"DROP DATABASE [{master_db_name}]"))
                    print(f"  ✓ Eski {master_db_name} silindi.")
                except Exception as drop_err:
                    print(f"  ✗ {master_db_name} silinemedi (Devam ediliyor...): {drop_err}")
            
            # Drop tenant 'www' database if exists
            result_t = conn.execute(text(f"SELECT DB_ID('{tenant_db_name}')"))
            if result_t.scalar() is not None:
                print(f"  [!] Eski {tenant_db_name} veritabanı tespit edildi. Temizleniyor...")
                try:
                    conn.execute(text(f"ALTER DATABASE [{tenant_db_name}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"))
                    conn.execute(text(f"DROP DATABASE [{tenant_db_name}]"))
                    print(f"  ✓ Eski {tenant_db_name} silindi.")
                except Exception as drop_err:
                    print(f"  ✗ {tenant_db_name} silinemedi: {drop_err}")

            # Recreate MASTER DB fresh
            conn.execute(text(f"CREATE DATABASE [{master_db_name}]"))
            print(f"  ✓ Yeni {master_db_name} veritabanı oluşturuldu.")
            
        sys_engine.dispose()

        # KRİTİK: Flask-SQLAlchemy bağlantı havuzunu temizle.
        # ZYRONOVA_MASTER silindi ve yeniden oluşturuldu; pool'daki
        # eski bağlantılar artık geçersiz (pipe broken). dispose()
        # tüm havuzu boşaltır, create_all() temiz bir bağlantı açar.
        db.engine.dispose()

        # SQL Server'ın yeni veritabanını tam olarak hazır etmesi için
        # kısa bir bekleme — bazı ortamlarda anlık erişim başarısız olabilir.
        print("  ... SQL Server yeni veritabanını hazırlıyor (2 saniye bekleniyor)...")
        time.sleep(2)

        # Bağlantıyı doğrula: Yeni DB'ye ulaşılabildiğini garantile
        try:
            with db.engine.connect() as test_conn:
                test_conn.execute(text("SELECT 1"))
            print("  ✓ Yeni veritabanı bağlantısı doğrulandı.")
        except Exception as ping_err:
            print(f"  [!] Bağlantı doğrulama uyarısı (devam ediliyor): {ping_err}")

        print("\n[1/4] Master DB tabloları oluşturuluyor...")
        db.create_all()
        print("  ✓ Tablolar ve tüm sütunlar sıfırdan tertemiz oluşturuldu.")
        
        # Schema migration: Eksik sütunları ekle (mevcut DB'ler için)
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                res = conn.execute(text("""
                    SELECT name FROM sys.columns 
                    WHERE object_id = OBJECT_ID('users') 
                    AND name = 'two_factor_recovery_codes'
                """))
                if not res.fetchone():
                    conn.execute(text("ALTER TABLE users ADD two_factor_recovery_codes NVARCHAR(MAX) NULL"))
                    conn.commit()
                    print("  ✓ [MIGRATION] users.two_factor_recovery_codes sütunu eklendi.")
        except Exception as mig_err:
            print(f"  [MIGRATION] Sütun kontrolü: {mig_err}")
        
        print("\n[2/4] Varsayılan şirket oluşturuluyor...")
        if not db.session.get(Company, 1):
            default_company = Company(id=1, name='Zyronova Merkez', subdomain='www', contact_phone='05000000000')
            db.session.add(default_company)
            db.session.commit()
            print("  ✓ Zyronova Merkez hazır.")
        
        print("\n[3/4] Tenant veritabanı oluşturuluyor...")
        try:
            create_tenant_database('www', app)
            print("  ✓ 'www' tenant hazır.")
        except Exception as e:
            print(f"  ✗ Hata: {e}")
        
        print("\n[4/4] Admin kullanıcı oluşturuluyor...")
        master_user = User.query.filter_by(username='admin').first()
        if not master_user:
            super_admin = User(username='admin', name='Master', surname='Zyronova', role='master', role_id=11, company_id=1)
            super_admin.set_password('admin123')
            db.session.add(super_admin)
            db.session.commit()
            print("  ✓ Admin (admin / admin123) hazır.")

        print("\nKurulum Tamamlandı!")

if __name__ == '__main__':
    init_db()
