from extensions import get_tenant_session
from models import Rental, Company
from app import create_app
from utils.kabis import KabisManager

def process_kabis_async(subdomain, rental_id, kabis_username, kabis_password, kabis_sirket_kodu, is_return=False):
    """
    Arka planda KABİS bildirimini (Çıkış veya Dönüş) EGM web servisine gönderir ve sonucu veritabanına yazar.
    """
    app = create_app()
    with app.app_context():
        # Tenant (Müşteri) veritabanı oturumunu al
        ts = get_tenant_session(subdomain)
        rental = ts.query(Rental).filter_by(id=rental_id).first()
        
        if not rental:
            print(f"[RQ] Kiralama bulunamadı: {rental_id} ({subdomain})")
            return
            
        try:
            if is_return:
                response = KabisManager.send_return_to_kabis_soap(
                    rental, kabis_username, kabis_password, kabis_sirket_kodu
                )
                
                if response.get("success"):
                    rental.kabis_donus_durum = 1
                    rental.kabis_donus_hata = None
                    print(f"[RQ] [KABIS-DONUS] BASARILI: {rental_id}")
                else:
                    rental.kabis_donus_durum = -1
                    rental.kabis_donus_hata = response.get("message", "Bilinmeyen Hata")
                    print(f"[RQ] [KABIS-DONUS] HATA: {rental.kabis_donus_hata}")
            else:
                response = KabisManager.send_to_kabis_soap(
                    rental, kabis_username, kabis_password, kabis_sirket_kodu
                )
                
                if response.get("success"):
                    rental.kabis_cikis_durum = 1
                    rental.kabis_cikis_hata = None
                    print(f"[RQ] [KABIS-CIKIS] BASARILI: {rental_id}")
                else:
                    rental.kabis_cikis_durum = -1
                    rental.kabis_cikis_hata = response.get("message", "Bilinmeyen Hata")
                    print(f"[RQ] [KABIS-CIKIS] HATA: {rental.kabis_cikis_hata}")
                    
            ts.commit()
            
            # Flush statscache for UI updates
            from utils.stats import StatsCache
            StatsCache.invalidate(subdomain)
            
        except Exception as e:
            ts.rollback()
            print(f"[RQ] KABIS Islemi sirasinda sistem hatasi: {e}")
            if is_return:
                rental.kabis_donus_durum = -1
                rental.kabis_donus_hata = f"Kuyruk Hatası: {str(e)}"
            else:
                rental.kabis_cikis_durum = -1
                rental.kabis_cikis_hata = f"Kuyruk Hatası: {str(e)}"
            ts.commit()
