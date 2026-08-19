from flask import g
from models import Rental, Vehicle, Service, VehicleExpense
from sqlalchemy import func
from datetime import datetime, timedelta
import time
import threading

import redis
import json

class StatsCache:
    # Initialize a Redis connection pool on localhost:6379
    # db=0 is used for RentACar_Sistem caching
    _redis_pool = redis.ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True, protocol=2)
    _redis_client = redis.Redis(connection_pool=_redis_pool)

    @classmethod
    def get(cls, subdomain, key):
        try:
            full_key = f"statscache:{subdomain}:{key}"
            data = cls._redis_client.get(full_key)
            if data:
                return json.loads(data)
            return None
        except redis.RedisError as e:
            print(f"[REDIS ERROR] get: {e}")
            return None

    @classmethod
    def set(cls, subdomain, key, data):
        try:
            full_key = f"statscache:{subdomain}:{key}"
            # 1 saatlik TTL - sayfa geçişlerinde cache kaybolmasını engeller
            cls._redis_client.setex(full_key, 3600, json.dumps(data))
        except redis.RedisError as e:
            print(f"[REDIS ERROR] set: {e}")

    @classmethod
    def invalidate(cls, subdomain):
        try:
            # Find all keys matching this subdomain's cache pattern
            pattern = f"statscache:{subdomain}:*"
            keys = cls._redis_client.keys(pattern)
            if keys:
                cls._redis_client.delete(*keys)
                print(f"[STATS CACHE] Invalidated all Redis cache entries for tenant: {subdomain}")
        except redis.RedisError as e:
            print(f"[REDIS ERROR] invalidate: {e}")

def _get_ts():
    """Get tenant session or None."""
    return g.get('tenant_session')

def _get_subdomain():
    try:
        return g.current_company.subdomain.upper()
    except:
        return 'SYSTEM'

def invalidate_stats_cache():
    try:
        subdomain = _get_subdomain()
        StatsCache.invalidate(subdomain)
        
        # Enqueue background job to recalculate stats and warm the cache
        from redis import Redis
        from rq import Queue
        from utils.cache_jobs import warm_tenant_cache
        
        redis_conn = Redis(host='localhost', port=6379, db=0, protocol=2)
        q = Queue('default', connection=redis_conn)
        q.enqueue(warm_tenant_cache, subdomain)
    except Exception as e:
        print(f"[REDIS ERROR] invalidate: {e}", flush=True)

def get_currency_totals():
    subdomain = _get_subdomain()
    cached = StatsCache.get(subdomain, 'currency_totals')
    if cached is not None:
        return cached

    ts = _get_ts()
    totals = {
        '₺': {'gelir': 0, 'gider': 0, 'kar': 0},
        '$': {'gelir': 0, 'gider': 0, 'kar': 0},
        '€': {'gelir': 0, 'gider': 0, 'kar': 0}
    }
    if not ts:
        return totals
    
    # 1. Kiralama Gelir ve Karları (Database-side aggregation)
    rental_stats = ts.query(
        Rental.paraBirimi,
        func.sum(Rental.toplamFiyat).label('gelir'),
        func.sum(Rental.toplamMaliyet).label('gider')
    ).group_by(Rental.paraBirimi).all()
    
    for r in rental_stats:
        cur = r.paraBirimi or '₺'
        if cur not in totals: totals[cur] = {'gelir': 0, 'gider': 0, 'kar': 0}
        totals[cur]['gelir'] += float(r.gelir or 0)
        totals[cur]['gider'] += float(r.gider or 0)
        totals[cur]['kar'] += float((r.gelir or 0) - (r.gider or 0))
        
    # 2. Servis Giderleri (Database-side aggregation)
    service_stats = ts.query(
        Service.paraBirimi,
        func.sum(Service.ucret).label('gider')
    ).group_by(Service.paraBirimi).all()
    
    for s in service_stats:
        cur = s.paraBirimi or '₺'
        if cur not in totals: totals[cur] = {'gelir': 0, 'gider': 0, 'kar': 0}
        totals[cur]['gider'] += float(s.gider or 0)
        totals[cur]['kar'] -= float(s.gider or 0)
        
    # 3. Genel Araç Giderleri (Database-side aggregation)
    expense_stats = ts.query(
        VehicleExpense.paraBirimi,
        func.sum(VehicleExpense.tutar).label('gider')
    ).group_by(VehicleExpense.paraBirimi).all()
    
    for e in expense_stats:
        cur = e.paraBirimi or '₺'
        if cur not in totals: totals[cur] = {'gelir': 0, 'gider': 0, 'kar': 0}
        totals[cur]['gider'] += float(e.gider or 0)
        totals[cur]['kar'] -= float(e.gider or 0)
    
    StatsCache.set(subdomain, 'currency_totals', totals)
    return totals

def get_monthly_data():
    subdomain = _get_subdomain()
    cached = StatsCache.get(subdomain, 'monthly_data')
    if cached is not None:
        return cached

    ts = _get_ts()
    months_tr = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    result = []
    
    # Initialize 12 months
    for i in range(1, 13):
        result.append({
            'name': months_tr[i-1],
            'month_num': i,
            'gelir_₺': 0, 'gider_₺': 0,
            'gelir_$': 0, 'gider_$': 0,
            'gelir_€': 0, 'gider_€': 0
        })
    
    if not ts:
        return result
    
    # 1. Rental Monthly Data
    rental_subq = ts.query(
        func.substring(Rental.baslangicTarihi, 6, 2).label('month'),
        Rental.paraBirimi,
        Rental.toplamFiyat,
        Rental.toplamMaliyet
    ).subquery()

    rental_monthly = ts.query(
        rental_subq.c.month,
        rental_subq.c.paraBirimi,
        func.sum(rental_subq.c.toplamFiyat).label('gelir'),
        func.sum(rental_subq.c.toplamMaliyet).label('gider')
    ).group_by(rental_subq.c.month, rental_subq.c.paraBirimi).all()
    
    for r in rental_monthly:
        try:
            m_idx = int(r.month) - 1
            pb = r.paraBirimi or '₺'
            if 0 <= m_idx < 12:
                result[m_idx][f'gelir_{pb}'] += float(r.gelir or 0)
                result[m_idx][f'gider_{pb}'] += float(r.gider or 0)
        except: continue

    # 2. Service Monthly Data
    service_subq = ts.query(
        func.substring(Service.tarih, 6, 2).label('month'),
        Service.paraBirimi,
        Service.ucret
    ).subquery()

    service_monthly = ts.query(
        service_subq.c.month,
        service_subq.c.paraBirimi,
        func.sum(service_subq.c.ucret).label('gider')
    ).group_by(service_subq.c.month, service_subq.c.paraBirimi).all()
    
    for s in service_monthly:
        try:
            m_idx = int(s.month) - 1
            pb = s.paraBirimi or '₺'
            if 0 <= m_idx < 12:
                result[m_idx][f'gider_{pb}'] += float(s.gider or 0)
        except: continue

    # 3. Expense Monthly Data
    expense_subq = ts.query(
        func.substring(VehicleExpense.tarih, 6, 2).label('month'),
        VehicleExpense.id,
        VehicleExpense.tutar
    ).subquery()

    expense_monthly = ts.query(
        expense_subq.c.month,
        VehicleExpense.paraBirimi,
        func.sum(expense_subq.c.tutar).label('gider')
    ).join(VehicleExpense, VehicleExpense.id == expense_subq.c.id).group_by(expense_subq.c.month, VehicleExpense.paraBirimi).all()
    
    for e in expense_monthly:
        try:
            m_idx = int(e.month) - 1
            pb = e.paraBirimi or '₺'
            if 0 <= m_idx < 12:
                result[m_idx][f'gider_{pb}'] += float(e.gider or 0)
        except: continue

    StatsCache.set(subdomain, 'monthly_data', result)
    return result

def get_top_10_details():
    subdomain = _get_subdomain()
    cached = StatsCache.get(subdomain, 'top_10_details')
    if cached is not None:
        return cached

    ts = _get_ts()
    if not ts:
        return []
    
    from sqlalchemy import text as sa_text

    # En yüksek getiri sağlayan araçları bul (ham SQL - ORM decrypt yükünden kaçın)
    top_rows = ts.execute(sa_text("""
        SELECT TOP 10 plaka, marka, model,
               COUNT(id) as cnt,
               SUM(toplamFiyat) as total
        FROM rentals
        GROUP BY plaka, marka, model
        ORDER BY SUM(toplamFiyat) DESC
    """)).fetchall()
    
    result = []
    for d in top_rows:
        plaka = d[0]
        marka = d[1]
        model = d[2]

        # Para birimi bazlı gelir/gider/kar - sadece finansal sütunları çek (şifreli alan YOK)
        rental_stats = ts.execute(sa_text("""
            SELECT paraBirimi, 
                   SUM(toplamFiyat) as gelir,
                   SUM(toplamMaliyet) as gider,
                   SUM(kar) as kar
            FROM rentals
            WHERE plaka = :plaka
            GROUP BY paraBirimi
        """), {'plaka': plaka}).fetchall()

        expense_stats = ts.execute(sa_text("""
            SELECT paraBirimi, SUM(tutar) as toplam
            FROM vehicle_expenses
            WHERE plaka = :plaka
            GROUP BY paraBirimi
        """), {'plaka': plaka}).fetchall()

        currency_stats = {
            '₺': {'gelir': 0, 'gider': 0, 'kar': 0},
            '$': {'gelir': 0, 'gider': 0, 'kar': 0},
            '€': {'gelir': 0, 'gider': 0, 'kar': 0}
        }

        for r in rental_stats:
            pb = r[0] or '₺'
            if pb not in currency_stats: currency_stats[pb] = {'gelir': 0, 'gider': 0, 'kar': 0}
            currency_stats[pb]['gelir'] += float(r[1] or 0)
            currency_stats[pb]['gider'] += float(r[2] or 0)
            currency_stats[pb]['kar']   += float(r[3] or 0)

        for e in expense_stats:
            pb = e[0] or '₺'
            if pb not in currency_stats: currency_stats[pb] = {'gelir': 0, 'gider': 0, 'kar': 0}
            currency_stats[pb]['gider'] += float(e[1] or 0)
            currency_stats[pb]['kar']   -= float(e[1] or 0)

        # Son 5 kiralama - şifreli tcKimlik/ehliyetNo sütunlarını ALMA
        rentals_raw = ts.execute(sa_text("""
            SELECT TOP 5 id, plaka, marka, model, musteriAdi, isim, soyisim,
                   uyruk, baslangicTarihi, bitisTarihi, kiralamaSuresi,
                   alinistaKm, verilisteKm, kullanilanKm,
                   paraBirimi, gunlukFiyat, toplamFiyat, kar,
                   hasarDurumu, odemeYontemi, kabis_kiralama_status, kabis_teslim_status
            FROM rentals
            WHERE plaka = :plaka
            ORDER BY baslangicTarihi DESC
        """), {'plaka': plaka}).fetchall()

        rentals_list = []
        for r in rentals_raw:
            keys = ['id','plaka','marka','model','musteriAdi','isim','soyisim',
                    'uyruk','baslangicTarihi','bitisTarihi','kiralamaSuresi',
                    'alinistaKm','verilisteKm','kullanilanKm',
                    'paraBirimi','gunlukFiyat','toplamFiyat','kar',
                    'hasarDurumu','odemeYontemi','kabis_kiralama_status','kabis_teslim_status']
            rentals_list.append(dict(zip(keys, r)))

        # Son 10 gider
        expenses_raw = ts.execute(sa_text("""
            SELECT TOP 10 id, tutar, paraBirimi, tarih, gider_tipi, notlar
            FROM vehicle_expenses
            WHERE plaka = :plaka
            ORDER BY tarih DESC
        """), {'plaka': plaka}).fetchall()

        expenses_list = [
            {'id': e[0], 'tutar': e[1], 'paraBirimi': e[2], 
             'tarih': e[3], 'gider_tipi': e[4], 'notlar': e[5]}
            for e in expenses_raw
        ]

        result.append({
            'plaka': plaka,
            'arac_adi': f"{marka} {model}",
            'kiralama_sayisi': d[3],
            'currency_stats': currency_stats,
            'rentals': rentals_list,
            'expenses': expenses_list
        })
        
    StatsCache.set(subdomain, 'top_10_details', result)
    return result

def get_hasar_distribution():
    subdomain = _get_subdomain()
    cached = StatsCache.get(subdomain, 'hasar_distribution')
    if cached is not None:
        return cached

    ts = _get_ts()
    if not ts:
        return []
    
    data = ts.query(
        Rental.hasarDurumu,
        func.count(Rental.id)
    ).group_by(Rental.hasarDurumu).all()
    labels = {'yok': 'Hasarsız', 'hafif': 'Hafif', 'orta': 'Orta', 'agir': 'Ağır'}
    result = [{'name': labels.get(d[0], d[0]), 'value': d[1]} for d in data]
    
    StatsCache.set(subdomain, 'hasar_distribution', result)
    return result

def get_durum_distribution():
    subdomain = _get_subdomain()
    cached = StatsCache.get(subdomain, 'durum_distribution')
    if cached is not None:
        return cached

    ts = _get_ts()
    if not ts:
        return []
    
    vehicles = ts.query(Vehicle).filter_by(is_deleted=False).all()
    dist = {'bosta': 0, 'kirada': 0, 'bakimda': 0, 'pasif': 0}
    for v in vehicles:
        d = v.durum
        if d in dist: dist[d] += 1
    labels = {'bosta': 'Boşta', 'kirada': 'Kirada', 'bakimda': 'Bakımda', 'pasif': 'Pasif'}
    result = [{'name': labels.get(k, k), 'value': v} for k, v in dist.items() if v > 0]
    
    StatsCache.set(subdomain, 'durum_distribution', result)
    return result

def get_arac_gelir():
    subdomain = _get_subdomain()
    cached = StatsCache.get(subdomain, 'arac_gelir')
    if cached is not None:
        return cached

    ts = _get_ts()
    if not ts:
        return []
    
    data = ts.query(
        Rental.plaka,
        func.sum(Rental.toplamFiyat)
    ).group_by(Rental.plaka).order_by(func.sum(Rental.toplamFiyat).desc()).limit(5).all()
    result = [{'name': d[0], 'gelir': float(d[1])} for d in data]
    
    StatsCache.set(subdomain, 'arac_gelir', result)
    return result

def get_period_stats(field_name):
    subdomain = _get_subdomain()
    cache_key = f'period_stats_{field_name}'
    cached = StatsCache.get(subdomain, cache_key)
    if cached is not None:
        return cached

    ts = _get_ts()
    now = datetime.now()
    
    period_starts = {
        'gun':   now.strftime('%Y-%m-%d'),
        'hafta': (now - timedelta(days=7)).strftime('%Y-%m-%d'),
        'ay':    (now - timedelta(days=30)).strftime('%Y-%m-%d'),
        'yil':   now.replace(month=1, day=1).strftime('%Y-%m-%d')
    }
    results = {k: 0.0 for k in period_starts}
    
    if not ts:
        return results

    from utils.helpers import get_tcmb_rates
    rates = get_tcmb_rates() or {}
    usd_rate = float(rates.get('USD', {}).get('selling', 0) or 0)
    eur_rate = float(rates.get('EUR', {}).get('selling', 0) or 0)

    def to_tl(amount, currency):
        if not amount: return 0.0
        currency = currency or '₺'
        if currency == '$' and usd_rate > 0:
            return float(amount) * usd_rate
        elif currency == '€' and eur_rate > 0:
            return float(amount) * eur_rate
        return float(amount)

    # En eski dönem başlangıcı (yil) - tüm dönemleri tek sorguda çek
    oldest_start = period_starts['yil']

    if field_name == 'toplamFiyat':  # GELİR
        rows = ts.execute(
            __import__('sqlalchemy').text(
                "SELECT paraBirimi, baslangicTarihi, SUM(toplamFiyat) as v "
                "FROM rentals WHERE baslangicTarihi >= :s "
                "GROUP BY paraBirimi, baslangicTarihi"
            ), {'s': oldest_start}
        ).fetchall()
        # Her satırı uygun dönemlere dağıt
        for pb, tarih, v in rows:
            val = to_tl(v, pb)
            for label, start in period_starts.items():
                if tarih and str(tarih)[:10] >= start:
                    results[label] += val

    elif field_name == 'toplamMaliyet':  # GİDER
        r_rows = ts.execute(
            __import__('sqlalchemy').text(
                "SELECT paraBirimi, baslangicTarihi, SUM(toplamMaliyet) as v "
                "FROM rentals WHERE baslangicTarihi >= :s "
                "GROUP BY paraBirimi, baslangicTarihi"
            ), {'s': oldest_start}
        ).fetchall()
        s_rows = ts.execute(
            __import__('sqlalchemy').text(
                "SELECT paraBirimi, tarih, SUM(ucret) as v "
                "FROM services WHERE tarih >= :s "
                "GROUP BY paraBirimi, tarih"
            ), {'s': oldest_start}
        ).fetchall()
        v_rows = ts.execute(
            __import__('sqlalchemy').text(
                "SELECT paraBirimi, tarih, SUM(tutar) as v "
                "FROM vehicle_expenses WHERE tarih >= :s "
                "GROUP BY paraBirimi, tarih"
            ), {'s': oldest_start}
        ).fetchall()
        for pb, tarih, v in (list(r_rows) + list(s_rows) + list(v_rows)):
            val = to_tl(v, pb)
            for label, start in period_starts.items():
                if tarih and str(tarih)[:10] >= start:
                    results[label] += val

    elif field_name == 'kar':  # KAR
        r_rows = ts.execute(
            __import__('sqlalchemy').text(
                "SELECT paraBirimi, baslangicTarihi, SUM(toplamFiyat) as gelir, SUM(toplamMaliyet) as gider "
                "FROM rentals WHERE baslangicTarihi >= :s "
                "GROUP BY paraBirimi, baslangicTarihi"
            ), {'s': oldest_start}
        ).fetchall()
        s_rows = ts.execute(
            __import__('sqlalchemy').text(
                "SELECT paraBirimi, tarih, SUM(ucret) as v "
                "FROM services WHERE tarih >= :s "
                "GROUP BY paraBirimi, tarih"
            ), {'s': oldest_start}
        ).fetchall()
        v_rows = ts.execute(
            __import__('sqlalchemy').text(
                "SELECT paraBirimi, tarih, SUM(tutar) as v "
                "FROM vehicle_expenses WHERE tarih >= :s "
                "GROUP BY paraBirimi, tarih"
            ), {'s': oldest_start}
        ).fetchall()
        for pb, tarih, gelir, gider in r_rows:
            net = to_tl(gelir, pb) - to_tl(gider, pb)
            for label, start in period_starts.items():
                if tarih and str(tarih)[:10] >= start:
                    results[label] += net
        for pb, tarih, v in (list(s_rows) + list(v_rows)):
            val = to_tl(v, pb)
            for label, start in period_starts.items():
                if tarih and str(tarih)[:10] >= start:
                    results[label] -= val
    else:
        val = ts.query(func.sum(getattr(Rental, field_name))).scalar() or 0
        results = {k: float(val) for k in period_starts}

    StatsCache.set(subdomain, cache_key, results)
    return results

def get_report_stats(start_date=None, end_date=None):
    """
    Raporlar sayfası için ağır istatistik hesaplamaları.
    Sonuçlar Redis'te 1 saat boyunca önbelleğe alınır.
    Sadece aggregate/özet veriler — paginated rentals listesi buraya dahil DEĞİL.
    """
    subdomain = _get_subdomain()
    cache_key = f'report_stats:{start_date or "all"}:{end_date or "all"}'
    cached = StatsCache.get(subdomain, cache_key)
    if cached is not None:
        return cached

    ts = _get_ts()
    _EMPTY = {
        'stats': {
            'currency_stats': {},
            'total_count': 0,
            'total_revenue': 0,
            'total_expense': 0,
            'net_profit': 0,
            'chart_data': {'labels': [], 'revenue_points': [], 'expense_points': []},
            'vehicle_chart_data': {'labels': [], 'data_points': []},
            'market_analysis': [],
            'monthly_dist': []
        },
        'vehicle_stats': [],
        'company_stats': [],
        'total_rentals': 0
    }
    if not ts:
        return _EMPTY

    from sqlalchemy import text as sa_text

    where_clauses = []
    params = {}
    if start_date:
        where_clauses.append("baslangicTarihi >= :start_date")
        params['start_date'] = start_date
    if end_date:
        where_clauses.append("baslangicTarihi <= :end_date")
        params['end_date'] = end_date
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Toplam kayıt sayısı
    count_row = ts.execute(sa_text(f"SELECT COUNT(id) FROM rentals {where_sql}"), params).fetchone()
    total_rentals = count_row[0] if count_row else 0

    # İstatistik için TÜM kiralama kayıtları (sayfalanmamış)
    all_raw = ts.execute(sa_text(f"""
        SELECT id, plaka, marka, model, musteriAdi, uyruk, kurumAdi,
               baslangicTarihi, kiralamaSuresi,
               paraBirimi, toplamFiyat, toplamMaliyet, kar
        FROM rentals
        {where_sql}
        ORDER BY baslangicTarihi DESC
    """), params).fetchall()

    rk = ['id','plaka','marka','model','musteriAdi','uyruk','kurumAdi',
          'baslangicTarihi','kiralamaSuresi',
          'paraBirimi','toplamFiyat','toplamMaliyet','kar']
    all_rentals = [dict(zip(rk, r)) for r in all_raw]

    # ── Currency Stats ────────────────────────────────────────────────
    currency_stats = {
        '₺': {'revenue': 0, 'expense': 0, 'profit': 0, 'count': 0},
        '$': {'revenue': 0, 'expense': 0, 'profit': 0, 'count': 0},
        '€': {'revenue': 0, 'expense': 0, 'profit': 0, 'count': 0}
    }
    total_revenue_tl = 0.0
    total_expense_tl = 0.0

    for r in all_rentals:
        cur = r['paraBirimi'] or '₺'
        if cur not in currency_stats:
            currency_stats[cur] = {'revenue': 0, 'expense': 0, 'profit': 0, 'count': 0}
        r_rev = r['toplamFiyat'] or 0
        r_exp = r['toplamMaliyet'] or 0
        currency_stats[cur]['revenue'] += r_rev
        currency_stats[cur]['expense'] += r_exp
        currency_stats[cur]['profit']  += (r_rev - r_exp)
        currency_stats[cur]['count']   += 1
        if cur == '₺':
            total_revenue_tl += r_rev
            total_expense_tl += r_exp

    svc_where = ("WHERE " + " AND ".join([c.replace("baslangicTarihi", "tarih") for c in where_clauses])) if where_clauses else ""
    all_services_raw = ts.execute(sa_text(f"SELECT paraBirimi, ucret, tarih FROM services {svc_where}"), params).fetchall()
    all_expenses_raw = ts.execute(sa_text(f"SELECT paraBirimi, tutar, tarih, plaka FROM vehicle_expenses {svc_where}"), params).fetchall()

    for s in all_services_raw:
        cur = s[0] or '₺'
        if cur not in currency_stats:
            currency_stats[cur] = {'revenue': 0, 'expense': 0, 'profit': 0, 'count': 0}
        currency_stats[cur]['expense'] += s[1] or 0
        currency_stats[cur]['profit']  -= s[1] or 0
        if cur == '₺': total_expense_tl += s[1] or 0

    for e in all_expenses_raw:
        cur = e[0] or '₺'
        if cur not in currency_stats:
            currency_stats[cur] = {'revenue': 0, 'expense': 0, 'profit': 0, 'count': 0}
        currency_stats[cur]['expense'] += e[1] or 0
        currency_stats[cur]['profit']  -= e[1] or 0
        if cur == '₺': total_expense_tl += e[1] or 0

    # ── Vehicle Stats ─────────────────────────────────────────────────
    v_map = {}
    for r in all_rentals:
        p = r['plaka']
        if p not in v_map:
            v_map[p] = {'plaka': p, 'marka': r['marka'], 'model': r['model'],
                        'kiralama_sayisi': 0, 'toplam_gun': 0,
                        'toplam_gelir': 0, 'toplam_gider': 0, 'net_kar': 0}
        s = v_map[p]
        r_rev = r['toplamFiyat'] or 0
        r_exp = r['toplamMaliyet'] or 0
        s['kiralama_sayisi'] += 1
        s['toplam_gun']      += r['kiralamaSuresi'] or 0
        s['toplam_gelir']    += r_rev
        s['toplam_gider']    += r_exp
        s['net_kar']         += (r_rev - r_exp)
    for e in all_expenses_raw:
        p = e[3]
        if p and p not in v_map:
            v_map[p] = {'plaka': p, 'marka': '-', 'model': '-',
                        'kiralama_sayisi': 0, 'toplam_gun': 0,
                        'toplam_gelir': 0, 'toplam_gider': 0, 'net_kar': 0}
        if p:
            v_map[p]['toplam_gider'] += (e[1] or 0)
            v_map[p]['net_kar']      -= (e[1] or 0)
    vehicle_stats = sorted(v_map.values(), key=lambda x: x['kiralama_sayisi'], reverse=True)

    # ── Company Stats ─────────────────────────────────────────────────
    c_map = {}
    for r in all_rentals:
        cname = r['kurumAdi'] or 'Bireysel'
        if cname not in c_map:
            c_map[cname] = {'name': cname, 'kiralama_sayisi': 0, 'toplam_gelir': 0, 'net_kar': 0}
        c_map[cname]['kiralama_sayisi'] += 1
        c_map[cname]['toplam_gelir']    += r['toplamFiyat'] or 0
        c_map[cname]['net_kar']         += r['kar'] or 0
    company_stats = sorted(c_map.values(), key=lambda x: x['kiralama_sayisi'], reverse=True)

    # ── Monthly Distribution ──────────────────────────────────────────
    months_tr = ["Ocak","Şubat","Mart","Nisan","Mayıs","Haziran",
                 "Temmuz","Ağustos","Eylül","Ekim","Kasım","Aralık"]
    monthly_dist = [{'name': months_tr[i], 'count': 0, 'revenue': 0, 'expense': 0} for i in range(12)]
    for r in all_rentals:
        try:
            dt = datetime.strptime(r['baslangicTarihi'], '%Y-%m-%d')
            monthly_dist[dt.month-1]['count']   += 1
            monthly_dist[dt.month-1]['revenue'] += r['toplamFiyat'] or 0
            monthly_dist[dt.month-1]['expense'] += r['toplamMaliyet'] or 0
        except: continue
    for s in all_services_raw:
        try:
            dt = datetime.strptime(s[2], '%Y-%m-%d')
            monthly_dist[dt.month-1]['expense'] += s[1] or 0
        except: continue
    for e in all_expenses_raw:
        try:
            dt = datetime.strptime(e[2], '%Y-%m-%d')
            monthly_dist[dt.month-1]['expense'] += e[1] or 0
        except: continue

    # ── Market Analysis ───────────────────────────────────────────────
    market_rows = ts.execute(sa_text(
        "SELECT TOP 5 uyruk, COUNT(id) as cnt FROM rentals GROUP BY uyruk ORDER BY COUNT(id) DESC"
    )).fetchall()
    market_analysis = []
    for m in market_rows:
        top_v = ts.execute(sa_text(
            "SELECT TOP 1 plaka FROM rentals WHERE uyruk=:u GROUP BY plaka ORDER BY COUNT(id) DESC"
        ), {'u': m[0]}).fetchone()
        market_analysis.append({'uyruk': m[0], 'count': m[1],
                                 'top_vehicle': top_v[0] if top_v else '-'})

    result = {
        'stats': {
            'currency_stats': currency_stats,
            'total_count': total_rentals,
            'total_revenue': total_revenue_tl,
            'total_expense': total_expense_tl,
            'net_profit': total_revenue_tl - total_expense_tl,
            'chart_data': {
                'labels': [m['name'] for m in monthly_dist],
                'revenue_points': [m['revenue'] for m in monthly_dist],
                'expense_points': [m['expense'] for m in monthly_dist],
            },
            'vehicle_chart_data': {
                'labels': [v['plaka'] for v in vehicle_stats[:5]],
                'data_points': [v['toplam_gelir'] for v in vehicle_stats[:5]],
            },
            'market_analysis': market_analysis,
            'monthly_dist': monthly_dist
        },
        'vehicle_stats': vehicle_stats,
        'company_stats': company_stats,
        'total_rentals': total_rentals
    }

    StatsCache.set(subdomain, cache_key, result)
    return result


def get_report_data(start_date=None, end_date=None, page=1, per_page=15):
    """
    Raporlar sayfası verisi.
    Ağır istatistikler get_report_stats() üzerinden Redis cache'den gelir.
    Sadece sayfalanmış rentals listesi her seferinde taze çekilir.
    """
    ts = _get_ts()
    base_stats = get_report_stats(start_date, end_date)

    if not ts:
        return {**base_stats, 'rentals': []}

    from sqlalchemy import text as sa_text

    where_clauses = []
    params = {}
    if start_date:
        where_clauses.append("baslangicTarihi >= :start_date")
        params['start_date'] = start_date
    if end_date:
        where_clauses.append("baslangicTarihi <= :end_date")
        params['end_date'] = end_date
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    offset = (page - 1) * per_page
    params_page = {**params, 'offset_val': offset, 'fetch_val': per_page}

    raw_rentals = ts.execute(sa_text(f"""
        SELECT id, plaka, marka, model, musteriAdi, isim, soyisim, uyruk, kurumAdi,
               baslangicTarihi, bitisTarihi, kiralamaSuresi,
               paraBirimi, gunlukFiyat, toplamFiyat, toplamMaliyet, kar,
               hasarDurumu, odemeYontemi
        FROM rentals
        {where_sql}
        ORDER BY baslangicTarihi DESC
        OFFSET :offset_val ROWS FETCH NEXT :fetch_val ROWS ONLY
    """), params_page).fetchall()

    rental_keys = ['id','plaka','marka','model','musteriAdi','isim','soyisim','uyruk','kurumAdi',
                   'baslangicTarihi','bitisTarihi','kiralamaSuresi',
                   'paraBirimi','gunlukFiyat','toplamFiyat','toplamMaliyet','kar',
                   'hasarDurumu','odemeYontemi']
    rentals = [dict(zip(rental_keys, r)) for r in raw_rentals]

    return {**base_stats, 'rentals': rentals}
