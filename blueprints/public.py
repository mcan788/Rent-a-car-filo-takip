from flask import Blueprint, request, render_template, current_app, redirect
import jwt
import os
from datetime import datetime

public_bp = Blueprint('public', __name__, url_prefix='/public')

@public_bp.route('/geciken-araclar', methods=['GET'])
def geciken_araclar():
    token = request.args.get('token')
    if not token:
        return render_template('geciken_araclar_public.html', error="Token eksik. Lütfen e-postanızdaki linke tekrar tıklayın.")

    try:
        secret = os.getenv('JWT_SECRET')
        if not secret:
            raise ValueError("JWT_SECRET is not configured!")
        decoded = jwt.decode(token, secret, algorithms=['HS256'])
        subdomain = decoded.get('subdomain')
        
        if not subdomain:
            raise ValueError("Geçersiz token formatı.")
            
    except jwt.ExpiredSignatureError:
        return render_template('geciken_araclar_public.html', error="Bu linkin süresi (48 saat) dolmuştur. Yeni bildirim geldiğinde güncel linki kullanabilirsiniz.")
    except Exception as e:
        return render_template('geciken_araclar_public.html', error="Geçersiz veya bozuk link.")

    # Token geçerli. İlgili acentenin verilerini çekelim.
    try:
        from extensions import get_tenant_session
        from models import Rental
        
        ts = get_tenant_session(subdomain=subdomain, app=current_app)
        
        # Süresi geçmiş araçları bul
        now = datetime.now()
        # alinistaKm boş/0 olanlar, henüz teslim alınmamış araçlar.
        rentals_query = ts.query(Rental).filter(
            (Rental.alinistaKm == 0) | (Rental.alinistaKm == None)
        ).all()
        
        overdue_rentals = []
        for r in rentals_query:
            try:
                end_time_str = f"{r.bitisTarihi} {r.bitisSaati or '09:00'}"
                end_datetime = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
            except Exception:
                try:
                    end_datetime = datetime.strptime(r.bitisTarihi, "%Y-%m-%d")
                except Exception:
                    continue
            
            if end_datetime < now:
                overdue_rentals.append(r)
                
        # Tabloyu render et
        return render_template('geciken_araclar_public.html', rentals=overdue_rentals, company_name=subdomain.upper(), error=None)
        
    except Exception as e:
        current_app.logger.error(f"[PUBLIC ROUTE ERROR] {e}")
        return render_template('geciken_araclar_public.html', error="Sistemde bir hata oluştu. Lütfen daha sonra tekrar deneyin.")
