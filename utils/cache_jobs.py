from app import create_app
from extensions import get_tenant_session
from flask import g

def warm_tenant_cache(subdomain):
    """
    Arka planda (RQ worker içinde) çalışarak bir müşterinin istatistik önbelleğini 
    yeniden hesaplar ve Redis'e yazar (Write-Through Cache).
    """
    app = create_app()
    with app.app_context():
        # Fake 'g' context to simulate a web request so utils.stats can work unmodified
        g.tenant_session = get_tenant_session(subdomain)
        class FakeCompany:
            pass
        fc = FakeCompany()
        fc.subdomain = subdomain
        g.current_company = fc
        
        from utils.stats import (
            get_currency_totals, get_monthly_data, get_top_10_details,
            get_hasar_distribution, get_durum_distribution, get_arac_gelir,
            get_period_stats
        )
        
        try:
            get_currency_totals()
            get_monthly_data()
            get_top_10_details()
            get_hasar_distribution()
            get_durum_distribution()
            get_arac_gelir()
            for field in ['toplamFiyat', 'toplamMaliyet', 'kar']:
                get_period_stats(field)
            print(f"[RQ] [CACHE WARMED] Tenant: {subdomain}")
        except Exception as e:
            print(f"[RQ] [CACHE ERROR] Tenant {subdomain}: {e}")
