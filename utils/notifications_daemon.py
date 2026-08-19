import os
import time
import threading
from datetime import datetime, timedelta
from models import Company, Vehicle, Rental
from utils.mailer import send_email

# ─── Günlük spam önleme: Her şirket için son expiry e-posta tarihini takip et ───
_last_expiry_email_date = {}  # { company_id: "YYYY-MM-DD" }

def init_notifications_daemon(app):
    daemon_thread = threading.Thread(target=notifications_loop, args=(app,), daemon=True)
    daemon_thread.start()
    print("[NOTIFICATIONS DAEMON] Background notification scanner started (interval: 10 min).", flush=True)

def notifications_loop(app):
    # Wait for the server to spin up completely
    time.sleep(10)
    
    while True:
        try:
            with app.app_context():
                # 1. Run overdue return checks every cycle (10 min)
                check_overdue_rentals(app)
                
                # 2. Run daily vehicle expiry checks (once per day per company)
                check_vehicle_expiries(app)
                    
        except Exception as e:
            print(f"[NOTIFICATIONS DAEMON ERROR] Error in loop: {e}", flush=True)
            
        # Sleep for 10 minutes — near-realtime overdue detection
        time.sleep(600)

def check_overdue_rentals(app):
    from extensions import get_tenant_session
    
    # Get all active companies
    companies = Company.query.filter_by(is_active=True).all()
    now = datetime.now()
    
    for company in companies:
        try:
            ts = get_tenant_session(subdomain=company.subdomain, app=app)
            # Find rentals where:
            # - not returned yet (alinistaKm == 0 or alinistaKm is null)
            # - overdue_alert_sent == False
            overdue_rentals = ts.query(Rental).filter(
                (Rental.alinistaKm == 0) | (Rental.alinistaKm == None),
                Rental.overdue_alert_sent == False
            ).all()
            
            alerts_to_send = []
            for rental in overdue_rentals:
                try:
                    # Parse bitisTarihi and bitisSaati
                    end_time_str = f"{rental.bitisTarihi} {rental.bitisSaati or '09:00'}"
                    end_datetime = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
                except Exception:
                    try:
                        end_datetime = datetime.strptime(rental.bitisTarihi, "%Y-%m-%d")
                    except Exception:
                        continue
                
                # 10 dakikalık gecikme payı: bitiş saatine 10 dk ekleniyor
                grace_deadline = end_datetime + timedelta(minutes=10)
                if grace_deadline < now:
                    alerts_to_send.append(rental)
            
            if alerts_to_send and company.contact_email:
                import jwt
                
                # Generate a 48-hour valid token for this company
                token_payload = {
                    'company_id': company.id,
                    'subdomain': company.subdomain,
                    'exp': datetime.utcnow() + timedelta(hours=48)
                }
                token = jwt.encode(token_payload, os.getenv('JWT_SECRET', 'zyronova_captcha_fallback_secret'), algorithm='HS256')
                
                # Construct the link
                portal_url = os.getenv('PORTAL_URL', 'https://zyronova.com').rstrip('/')
                if not portal_url.startswith('http'):
                    portal_url = 'https://zyronova.com'
                public_link = f"{portal_url}/public/geciken-araclar?token={token}"

                # Send a single email with the secure link
                subject = f"🔴 GECİKEN KİRALAMA BİLDİRİMİ - {company.name}"
                body_html = f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    <div style="background-color: #ef4444; color: white; padding: 20px; text-align: center;">
                        <h2 style="margin: 0; font-size: 20px;">Geciken Araç Teslimatları</h2>
                    </div>
                    <div style="padding: 20px; background-color: #ffffff; color: #334155;">
                        <p style="font-size: 16px;">Sayın Yetkili,</p>
                        <p style="font-size: 15px; line-height: 1.5;">Teslim tarihi/saati geçmiş olmasına rağmen <b>{len(alerts_to_send)} adet</b> aracınız henüz teslim alınmamıştır.</p>
                        <p style="font-size: 15px; margin-bottom: 30px;">Mobil uyumlu tablonuzu görüntülemek için aşağıdaki butona tıklayabilirsiniz:</p>
                        <div style="text-align: center;">
                            <a href="{public_link}" style="background-color: #3b82f6; color: white; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; display: inline-block; font-size: 16px;">Araçları Görüntüle</a>
                        </div>
                        <p style="font-size: 12px; color: #64748b; margin-top: 30px; text-align: center;">Bu link güvenliğiniz için 48 saat sonra iptal olacaktır.</p>
                    </div>
                </div>
                """
                
                # Update overdue_alert_sent flag for these rentals
                for r in alerts_to_send:
                    r.overdue_alert_sent = True
                
                # Send email and commit alert status if successful
                if send_email(company.contact_email, subject, body_html):
                    ts.commit()
                    print(f"[NOTIFICATIONS DAEMON] Overdue alert sent and committed for company: {company.subdomain}", flush=True)
                
        except Exception as e:
            err_msg = str(e)
            if '42S02' in err_msg or 'Invalid object name' in err_msg:
                # Rent A Car tablosu bulunmayan (örn. Tur Takip acenteleri veya boş tenant DB) veritabanlarını sessizce atla
                pass
            else:
                print(f"[NOTIFICATIONS DAEMON ERROR] Failed to check overdue rentals for {company.subdomain}: {e}", flush=True)

def check_vehicle_expiries(app):
    from extensions import get_tenant_session
    
    companies = Company.query.filter_by(is_active=True).all()
    today = datetime.now().date()
    today_str = today.strftime("%Y-%m-%d")
    
    for company in companies:
        # Günlük spam önleme: Bu şirket için bugün zaten e-posta gönderildi mi?
        if _last_expiry_email_date.get(company.id) == today_str:
            continue
        
        try:
            ts = get_tenant_session(subdomain=company.subdomain, app=app)
            vehicles = ts.query(Vehicle).filter_by(is_deleted=False).all()
            
            expiring_vehicles = [] # List of tuples: (vehicle, alert_type, days_left, exp_date)
            
            for v in vehicles:
                # Parse vizeBitisTarihi
                if v.vizeBitisTarihi:
                    try:
                        vize_date = datetime.strptime(v.vizeBitisTarihi, "%Y-%m-%d").date()
                        days_left = (vize_date - today).days
                        # 30 gün kala: tek seferlik uyarı
                        # 14 gün ve altı: her gün uyarı
                        if days_left == 30 or (0 <= days_left <= 14):
                            expiring_vehicles.append((v, 'Vize (Muayene)', days_left, v.vizeBitisTarihi))
                    except ValueError:
                        pass
                
                # Parse sigortaBitisTarihi
                if v.sigortaBitisTarihi:
                    try:
                        sigorta_date = datetime.strptime(v.sigortaBitisTarihi, "%Y-%m-%d").date()
                        days_left = (sigorta_date - today).days
                        # 30 gün kala: tek seferlik uyarı
                        # 14 gün ve altı: her gün uyarı
                        if days_left == 30 or (0 <= days_left <= 14):
                            expiring_vehicles.append((v, 'Sigorta', days_left, v.sigortaBitisTarihi))
                    except ValueError:
                        pass
            
            if expiring_vehicles and company.contact_email:
                # Aciliyet seviyesine göre e-posta başlığı belirle
                min_days = min(d for _, _, d, _ in expiring_vehicles)
                if min_days <= 3:
                    subject = f"🔴 ACİL: Araç Vize/Sigorta Süresi Doluyor! - {company.name}"
                elif min_days <= 7:
                    subject = f"🟠 DİKKAT: Araç Vize/Sigorta Hatırlatması - {company.name}"
                elif min_days <= 14:
                    subject = f"⚠️ Araç Vize ve Sigorta Hatırlatma Raporu - {company.name}"
                else:
                    subject = f"📋 Araç Vize/Sigorta Ön Bilgilendirme (30 Gün) - {company.name}"

                body_html = f"""
                <div style="font-family: sans-serif; max-width: 650px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                    <div style="background-color: {'#ef4444' if min_days <= 3 else '#f59e0b' if min_days <= 14 else '#3b82f6'}; color: white; padding: 20px; text-align: center;">
                        <h2 style="margin: 0; font-size: 20px;">Araç Vize / Sigorta Hatırlatma</h2>
                    </div>
                    <div style="padding: 20px; background-color: #ffffff; color: #334155;">
                        <p style="font-size: 16px;">Sayın Yetkili,</p>
                        <p style="font-size: 15px; line-height: 1.5;">Aşağıda plakası ve detayları belirtilen araçlarınızın vize/sigorta süreleri dolmak üzeredir:</p>
                        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 15px;">
                            <tr style="background-color: #f8fafc;">
                                <th style="padding: 10px;">Plaka</th>
                                <th style="padding: 10px;">Araç Bilgisi</th>
                                <th style="padding: 10px;">Hatırlatma Türü</th>
                                <th style="padding: 10px;">Kalan Gün</th>
                                <th style="padding: 10px;">Bitiş Tarihi</th>
                            </tr>
                """
                for v, alert_type, days_left, exp_date in expiring_vehicles:
                    if days_left <= 0:
                        day_text = "SÜRESİ DOLDU!"
                        day_color = "#dc2626"
                    elif days_left <= 3:
                        day_text = f"{days_left} Gün"
                        day_color = "#dc2626"
                    elif days_left <= 7:
                        day_text = f"{days_left} Gün"
                        day_color = "#ea580c"
                    elif days_left <= 14:
                        day_text = f"{days_left} Gün"
                        day_color = "#d97706"
                    else:
                        day_text = f"{days_left} Gün"
                        day_color = "#2563eb"

                    body_html += f"""
                            <tr>
                                <td style="padding: 8px;"><b>{v.plaka}</b></td>
                                <td style="padding: 8px;">{v.marka} {v.model} ({v.yil})</td>
                                <td style="padding: 8px;">{alert_type}</td>
                                <td style="padding: 8px; color: {day_color}; font-weight: bold;">{day_text}</td>
                                <td style="padding: 8px;">{exp_date}</td>
                            </tr>
                    """
                
                body_html += """
                        </table>
                        <p style="font-size: 14px; margin-top: 20px; line-height: 1.6;">Lütfen yasal işlemlerin aksamaması için gerekli işlemleri yapınız.</p>
                        <p style="font-size: 12px; color: #94a3b8; margin-top: 15px;">Bu e-posta Zyronova otomatik bildirim sistemi tarafından gönderilmiştir.</p>
                    </div>
                </div>
                """
                
                if send_email(company.contact_email, subject, body_html):
                    # Başarılı gönderimde bugünün tarihini kaydet (spam önleme)
                    _last_expiry_email_date[company.id] = today_str
                    print(f"[NOTIFICATIONS DAEMON] Expiry report sent for company: {company.subdomain} (min {min_days} days left)", flush=True)
                
        except Exception as e:
            err_msg = str(e)
            if '42S02' in err_msg or 'Invalid object name' in err_msg:
                # Rent A Car tablosu bulunmayan (örn. Tur Takip acenteleri veya boş tenant DB) veritabanlarını sessizce atla
                pass
            else:
                print(f"[NOTIFICATIONS DAEMON ERROR] Failed to check vehicle expiries for {company.subdomain}: {e}", flush=True)
