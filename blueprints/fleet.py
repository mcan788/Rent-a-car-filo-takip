from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g
from flask_login import login_required, current_user
from extensions import db
from models import Vehicle, Rental, Service, VehicleExpense
from utils.helpers import safe_int, safe_float, log_action
from utils.stats import invalidate_stats_cache
from datetime import datetime
from sqlalchemy import or_, and_
from sqlalchemy.orm import load_only
import os
import hashlib
from cryptography.fernet import Fernet

fleet_bp = Blueprint('fleet', __name__)

@fleet_bp.route('/araclar')
@login_required
def araclar():
    if not current_user.get_permissions().get('araclar', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))

    if not g.current_company: return redirect(url_for('main.dashboard'))
    ts = g.tenant_session
    if not ts: return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    durum_filter = request.args.get('durum', 'hepsi')
    per_page = 10
    
    query = ts.query(Vehicle).filter(Vehicle.is_deleted == False)
    if search:
        query = query.filter(or_(
            Vehicle.plaka.like(f'%{search}%'),
            Vehicle.marka.like(f'%{search}%'),
            Vehicle.model.like(f'%{search}%')
        ))
    
    if durum_filter != 'hepsi':
        all_v = query.all()
        vehicles_filtered = [v for v in all_v if v.durum == durum_filter]
        total = len(vehicles_filtered)
        start = (page - 1) * per_page
        end = start + per_page
        vehicles_pagination = vehicles_filtered[start:end]
        has_prev = page > 1
        has_next = end < total
        pages = (total + per_page - 1) // per_page
    else:
        # Manual pagination for tenant session (no Flask-SQLAlchemy paginate)
        total = query.count()
        pages = (total + per_page - 1) // per_page
        offset = (page - 1) * per_page
        vehicles_pagination = query.order_by(Vehicle.plaka).offset(offset).limit(per_page).all()
        has_prev = page > 1
        has_next = page < pages

    return render_template('araclar.html',
        active_page='araclar',
        vehicles=vehicles_pagination,
        all_vehicles=ts.query(Vehicle).filter_by(is_deleted=False).options(
            load_only(Vehicle.id, Vehicle.plaka, Vehicle.marka, Vehicle.model)
        ).order_by(Vehicle.plaka).all(),
        search=search,
        durum_filter=durum_filter,
        page=page,
        pages=pages,
        has_prev=has_prev,
        has_next=has_next,
        now=datetime.now()
    )

@fleet_bp.route('/araclar/ekle', methods=['POST'])
@login_required
def arac_ekle():
    if not current_user.get_permissions().get('araclar', {}).get('actions', {}).get('add') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.araclar'))

    ts = g.tenant_session
    if not ts:
        flash('Veritabanı bağlantısı kurulamadı.', 'error')
        return redirect(url_for('fleet.araclar'))

    alis_km = safe_int(request.form.get('alisKm'))
    guncel_km = safe_int(request.form.get('guncelKm'))
    if guncel_km == 0: guncel_km = alis_km

    vehicle = Vehicle(
        plaka=request.form.get('plaka', '').upper(),
        marka=request.form.get('marka', ''),
        model=request.form.get('model', ''),
        yil=safe_int(request.form.get('yil') or datetime.now().year),
        renk=request.form.get('renk', ''),
        guncelKm=guncel_km,
        bakimYapildigiKm=safe_int(request.form.get('bakimYapildigiKm')),
        alisKm=alis_km,
        sigortaBitisTarihi=request.form.get('sigortaBitisTarihi', ''),
        vizeBitisTarihi=request.form.get('vizeBitisTarihi', ''),
        sigortaMaliyeti=safe_float(request.form.get('sigortaMaliyeti')),
        vizeMaliyeti=safe_float(request.form.get('vizeMaliyeti')),
        gunlukUcret=safe_float(request.form.get('gunlukUcret'))
    )
    if not vehicle.plaka or not vehicle.marka:
        flash('Plaka ve Marka alanları zorunludur', 'error')
        return redirect(url_for('fleet.araclar'))
        
    # Plaka teklik kontrolü (IntegrityError koruması)
    existing_vehicle = ts.query(Vehicle).filter_by(plaka=vehicle.plaka).first()
    if existing_vehicle:
        flash(f'Bu plakaya ({vehicle.plaka}) sahip bir araç zaten kayıtlıdır! Lütfen farklı bir plaka girin.', 'error')
        return redirect(url_for('fleet.araclar'))
    
    try:
        ts.add(vehicle)
        ts.commit()
        invalidate_stats_cache()
        log_action(current_user, 'vehicle_add', f'Yeni araç eklendi: {vehicle.plaka}')
        flash('Araç başarıyla eklendi', 'success')
    except Exception as e:
        ts.rollback()
        flash(f'Hata: {str(e)}', 'error')
        
    return redirect(url_for('fleet.araclar'))

@fleet_bp.route('/araclar/guncelle/<id>', methods=['POST'])
@login_required
def arac_guncelle(id):
    if not current_user.get_permissions().get('araclar', {}).get('actions', {}).get('edit') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.araclar'))

    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.araclar'))
    
    vehicle = ts.query(Vehicle).filter_by(id=id).first()
    if not vehicle:
        flash('Araç bulunamadı.', 'error')
        return redirect(url_for('fleet.araclar'))
    new_plaka = request.form.get('plaka', vehicle.plaka).strip().upper()
    if new_plaka != vehicle.plaka:
        existing_vehicle = ts.query(Vehicle).filter_by(plaka=new_plaka).first()
        if existing_vehicle:
            flash(f'Bu plakaya ({new_plaka}) sahip başka bir araç zaten kayıtlıdır! Lütfen farklı bir plaka girin.', 'error')
            return redirect(url_for('fleet.araclar'))
            
    vehicle.plaka = new_plaka
    vehicle.marka = request.form.get('marka', vehicle.marka)
    vehicle.model = request.form.get('model', vehicle.model)
    vehicle.yil = safe_int(request.form.get('yil') or vehicle.yil)
    vehicle.renk = request.form.get('renk', vehicle.renk)
    vehicle.alisKm = safe_int(request.form.get('alisKm') or vehicle.alisKm)
    vehicle.sigortaBitisTarihi = request.form.get('sigortaBitisTarihi', vehicle.sigortaBitisTarihi)
    vehicle.vizeBitisTarihi = request.form.get('vizeBitisTarihi', vehicle.vizeBitisTarihi)
    vehicle.sigortaMaliyeti = safe_float(request.form.get('sigortaMaliyeti') or vehicle.sigortaMaliyeti)
    vehicle.vizeMaliyeti = safe_float(request.form.get('vizeMaliyeti') or vehicle.vizeMaliyeti)
    vehicle.gunlukUcret = safe_float(request.form.get('gunlukUcret') or vehicle.gunlukUcret)
    
    is_active_str = request.form.get('is_active')
    if is_active_str is not None:
        vehicle.is_active = (is_active_str == 'true')
        
    ts.commit()
    invalidate_stats_cache()
    flash('Araç güncellendi', 'success')
    return redirect(url_for('fleet.araclar'))

@fleet_bp.route('/araclar/bakima_al/<id>', methods=['POST'])
@login_required
def arac_bakima_al(id):
    if not current_user.get_permissions().get('araclar', {}).get('actions', {}).get('edit') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.araclar'))

    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.araclar'))
    
    vehicle = ts.query(Vehicle).filter_by(id=id).first()
    if not vehicle:
        flash('Araç bulunamadı.', 'error')
        return redirect(url_for('fleet.araclar'))
    
    vehicle.is_in_maintenance = True
    vehicle.bakim_yeri = request.form.get('bakim_yeri', '')
    vehicle.bakim_nedeni = request.form.get('bakim_nedeni', '')
    vehicle.bakim_gonderen = request.form.get('bakim_gonderen', '')
    vehicle.bakim_gidis_km = safe_int(request.form.get('bakim_gidis_km'))
    vehicle.bakim_gidis_tarihi = request.form.get('bakim_gidis_tarihi', '')
    ts.commit()
    flash('Araç başarılı bir şekilde bakıma alındı', 'success')
    return redirect(url_for('fleet.araclar'))

@fleet_bp.route('/araclar/sil/<id>', methods=['POST'])
@login_required
def arac_sil(id):
    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.araclar'))
    
    vehicle = ts.query(Vehicle).filter_by(id=id).first()
    if not vehicle:
        flash('Araç bulunamadı.', 'error')
        return redirect(url_for('fleet.araclar'))
    
    plaka = vehicle.plaka
    # Soft delete: mark as deleted but keep in DB for financial history
    vehicle.is_deleted = True
    vehicle.is_active = False
    
    # Release unique plaka constraint by appending a compact unique suffix (max 20 chars)
    import secrets
    suffix = f"_D{secrets.token_hex(2).upper()}" # e.g. _DA9B1 (6 chars)
    vehicle.plaka = (plaka[:20-len(suffix)] + suffix).upper()
    
    ts.commit()
    invalidate_stats_cache()
    log_action(current_user, 'vehicle_delete', f'Araç silindi: {plaka}')
    flash('Araç silindi', 'success')
    return redirect(url_for('fleet.araclar'))

@fleet_bp.route('/araclar/gider_ekle', methods=['POST'])
@login_required
def gider_ekle():
    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.araclar'))

    arac_id = request.form.get('arac_id')
    plaka = request.form.get('plaka', '').upper()
    gider_tipi = request.form.get('gider_tipi', 'Diğer')
    tutar = safe_float(request.form.get('tutar'))
    tarih = request.form.get('tarih', datetime.now().strftime('%Y-%m-%d'))
    paraBirimi = request.form.get('paraBirimi', '₺')
    notlar = request.form.get('notlar', '')

    # Validate vehicle ownership
    vehicle = ts.query(Vehicle).filter_by(id=arac_id).first()
    if not vehicle:
        flash('Geçersiz araç bilgisi', 'error')
        return redirect(url_for('fleet.araclar'))

    expense = VehicleExpense(
        arac_id=arac_id,
        plaka=plaka,
        gider_tipi=gider_tipi,
        tutar=tutar,
        paraBirimi=paraBirimi,
        tarih=tarih,
        notlar=notlar
    )
    
    # Update vehicle expiry dates if provided
    yeni_bitis = request.form.get('yeni_bitis_tarihi')
    if yeni_bitis:
        if gider_tipi == 'Sigorta':
            vehicle.sigortaBitisTarihi = yeni_bitis
            vehicle.sigortaMaliyeti = tutar
        elif gider_tipi == 'Vize':
            vehicle.vizeBitisTarihi = yeni_bitis
            vehicle.vizeMaliyeti = tutar
    
    try:
        ts.add(expense)
        ts.commit()
        invalidate_stats_cache()
        log_action(current_user, 'expense_add', f'Araç gideri eklendi: {plaka} ({gider_tipi})')
        flash(f'{plaka} için {gider_tipi} gideri kaydedildi ve tarih güncellendi', 'success')
    except Exception as e:
        ts.rollback()
        flash(f'Hata: {str(e)}', 'error')
        
    return redirect(url_for('fleet.araclar'))

@fleet_bp.route('/kiralamalar')
@login_required
def kiralamalar():
    if not current_user.get_permissions().get('kiralamalar', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))

    if not g.current_company: return redirect(url_for('main.dashboard'))
    ts = g.tenant_session
    if not ts: return redirect(url_for('main.dashboard'))
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    hasar_filter = request.args.get('hasar', 'hepsi')
    status_filter = request.args.get('status', 'hepsi')
    per_page = 10
    
    query = ts.query(Rental)
    if search:
        conditions = [
            Rental.plaka.like(f'%{search}%'),
            Rental.musteriAdi.like(f'%{search}%'),
            Rental.marka.like(f'%{search}%'),
            Rental.baslangicTarihi.like(f'%{search}%'),
            Rental.bitisTarihi.like(f'%{search}%')
        ]
        
        # Tarih formatı kontrolü
        import re
        # YYYY-MM-DD kontrolü
        if re.match(r'^\d{4}-\d{2}-\d{2}$', search):
            conditions.append(and_(Rental.baslangicTarihi <= search, Rental.bitisTarihi >= search))
        # DD-MM-YYYY veya DD.MM.YYYY kontrolü (Türkiye Formatı)
        elif re.match(r'^\d{2}[-.]\d{2}[-.]\d{4}$', search):
            try:
                # Gün-Ay-Yıl -> Yıl-Ay-Gün çevirisi
                p = re.split('[-.]', search)
                db_date = f"{p[2]}-{p[1]}-{p[0]}"
                conditions.append(and_(Rental.baslangicTarihi <= db_date, Rental.bitisTarihi >= db_date))
            except: pass
            
        query = query.filter(or_(*conditions))
    
    if hasar_filter != 'hepsi':
        query = query.filter(Rental.hasarDurumu == hasar_filter)

    if status_filter == 'gecikmis':
        today_str = datetime.now().strftime('%Y-%m-%d')
        query = query.filter(Rental.bitisTarihi <= today_str, Rental.alinistaKm == 0)
    elif status_filter == 'aktif':
        query = query.filter(Rental.alinistaKm == 0)
    elif status_filter == 'tamamlanmis':
        query = query.filter(Rental.alinistaKm > 0)
    
    # Manual pagination
    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page
    rentals = query.order_by(Rental.baslangicTarihi.desc(), Rental.baslangicSaati.desc()).offset(offset).limit(per_page).all()
    has_prev = page > 1
    has_next = page < pages
    
    rentals_json = [r.to_dict() for r in rentals]
    vehicles = ts.query(Vehicle).filter_by(is_active=True).all()
    
    # Fetch recent rentals to evaluate KABIS status in-memory (avoids 4000ms SQL full table scan latency)
    recent_rentals = []
    
    # 1. Checkout (Kiralama) failed/pending (only if signed, active, and not successful)
    kabis_pending_checkout = []
    
    # 2. Return (Teslim) failed/pending (returned, but not successful)
    kabis_pending_return = []
    
    kabis_total_pending = 0
    
    active_rentals = ts.query(Rental).filter(or_(Rental.alinistaKm == 0, Rental.alinistaKm == None)).order_by(Rental.baslangicTarihi.desc(), Rental.baslangicSaati.desc()).all()
    active_rentals_json = [r.to_dict() for r in active_rentals]
    
    return render_template('kiralamalar.html',
        active_page='kiralamalar',
        rentals=rentals,
        rentals_json=rentals_json,
        active_rentals=active_rentals,
        active_rentals_json=active_rentals_json,
        vehicles=vehicles,
        kabis_pending_checkout=kabis_pending_checkout,
        kabis_pending_return=kabis_pending_return,
        kabis_total_pending=kabis_total_pending,
        search=search,
        hasar_filter=hasar_filter,
        status_filter=status_filter,
        page=page,
        pages=pages,
        has_prev=has_prev,
        has_next=has_next,
        now=datetime.now()
    )

@fleet_bp.route('/kiralamalar/detay/<id>')
@login_required
def kiralama_detay(id):
    ts = g.tenant_session
    if not ts: return jsonify({'error': 'Bağlantı hatası'}), 500
    
    rental = ts.query(Rental).filter_by(id=id).first()
    if not rental:
        return jsonify({'error': 'Kiralama bulunamadı'}), 404
        
    return jsonify(rental.to_dict())

@fleet_bp.route('/kiralamalar/ekle', methods=['POST'])
@login_required
def kiralama_ekle():
    if not current_user.get_permissions().get('kiralamalar', {}).get('actions', {}).get('add') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    ts = g.tenant_session
    if not ts:
        flash('Veritabanı bağlantısı kurulamadı.', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    required_fields = ['isim', 'soyisim', 'kurumAdi', 'personelAdi', 'baslangicTarihi', 'bitisTarihi', 'verilisteKm']
    for field in required_fields:
        if not request.form.get(field):
            flash('Lütfen tüm zorunlu alanları doldurun', 'error')
            return redirect(url_for('fleet.kiralamalar'))
            
    verilis_km = safe_int(request.form.get('verilisteKm'))
    toplam_fiyat = safe_float(request.form.get('toplamFiyat'))
    arac_id = request.form.get('arac_id') or request.form.get('aracId')
    
    # Araç müsaitlik kontrolü
    vehicle = ts.query(Vehicle).filter_by(id=arac_id).first()
    if not vehicle:
        flash('Geçersiz araç seçimi.', 'error')
        return redirect(url_for('fleet.kiralamalar'))
        
    if vehicle.durum != 'bosta':
        flash(f'Araç ({vehicle.plaka}) şu anda müsait değil (Durum: {vehicle.durum}).', 'error')
        return redirect(url_for('fleet.kiralamalar'))
        
    if verilis_km < vehicle.guncelKm:
        flash(f'Veriliş kilometresi ({verilis_km}) aracın güncel kilometresinden ({vehicle.guncelKm}) az olamaz.', 'error')
        return redirect(url_for('fleet.kiralamalar'))
    
    isim = request.form.get('isim', '')
    soyisim = request.form.get('soyisim', '')
    
    try:
        d1 = datetime.strptime(request.form.get('baslangicTarihi'), '%Y-%m-%d')
        d2 = datetime.strptime(request.form.get('bitisTarihi'), '%Y-%m-%d')
        gun_sayisi = max(1, (d2 - d1).days)
    except:
        gun_sayisi = 1

    musteri_imza = request.form.get('musteriImza', '').strip()
    firma_imza = request.form.get('firmaImza', '').strip()
    biyometrik_json = request.form.get('biyometrikVeri', '').strip()
    
    biyometrik_hash = None
    biyometrik_sifreli = None
    
    if biyometrik_json and len(biyometrik_json) > 10:
        try:
            # SHA-256 Hash
            biyometrik_hash = hashlib.sha256(biyometrik_json.encode('utf-8')).hexdigest()
            # AES-256 (Fernet) Encryption
            key_str = os.getenv('ENCRYPTION_KEY')
            if key_str:
                fernet = Fernet(key_str.encode('utf-8'))
                biyometrik_sifreli = fernet.encrypt(biyometrik_json.encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"[BIOMETRIC ENCRYPTION ERROR] {e}", flush=True)

    if not musteri_imza or not firma_imza or not musteri_imza.startswith('data:image/png;base64,') or not firma_imza.startswith('data:image/png;base64,') or len(musteri_imza) < 500 or len(firma_imza) < 500:
        flash('Kiralama sözleşmesi imzalanmadan sistem kayda izin vermemektedir. Lütfen imzaları eksiksiz doldurun.', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    dili = request.form.get('sozlesmeDili', 'TR')
    raw_template = g.current_company.contract_template or ''
    metni = raw_template
    if raw_template.startswith('{'):
        try:
            import json
            parsed = json.loads(raw_template)
            metni = parsed.get(dili, raw_template)
        except:
            pass

    rental = Rental(
        arac_id=arac_id,
        plaka=vehicle.plaka,
        marka=vehicle.marka,
        model=vehicle.model,
        isim=isim,
        soyisim=soyisim,
        musteriAdi=request.form.get('isim') + ' ' + request.form.get('soyisim'),
        uyruk=request.form.get('uyruk', 'TC'),
        tcKimlik=request.form.get('tcKimlik', ''),
        dogumYeri=request.form.get('dogumYeri', ''),
        kurumAdi=request.form.get('kurumAdi', ''),
        personelAdi=request.form.get('personelAdi', ''),
        baslangicTarihi=request.form.get('baslangicTarihi'),
        baslangicSaati=request.form.get('baslangicSaati', '09:00'),
        bitisTarihi=request.form.get('bitisTarihi'),
        bitisSaati=request.form.get('bitisSaati', '09:00'),
        kiralamaSuresi=max(1, gun_sayisi),
        verilisteKm=verilis_km,
        konaklamaTipi=request.form.get('konaklamaTipi', 'ev'),
        odaNo=request.form.get('odaNo', ''),
        adres=request.form.get('adres', ''),
        kiralama_lat=safe_float(request.form.get('kiralama_lat')),
        kiralama_lng=safe_float(request.form.get('kiralama_lng')),
        odemeYontemi=', '.join([m for m in ['Nakit' if request.form.get('pay_nakit') else None, 'Kart' if request.form.get('pay_kart') else None] if m]),
        nakitTutar=safe_float(request.form.get('nakitTutar')),
        kartTutar=safe_float(request.form.get('kartTutar')),
        surucuAdSoyad=request.form.get('surucuAdSoyad', ''),
        ehliyetNo=request.form.get('ehliyetNo', ''),
        ehliyetVerilisTarihi=request.form.get('ehliyetVerilisTarihi', ''),
        ehliyetGecerlilikTarihi=request.form.get('ehliyetGecerlilikTarihi', ''),
        paraBirimi=request.form.get('paraBirimi', '₺'),
        gunlukFiyat=float(request.form.get('gunlukFiyat', 0)),
        toplamFiyat=toplam_fiyat,
        kar=toplam_fiyat,
        hasarDurumu=request.form.get('hasarDurumu', 'yok'),
        hasarAciklama=request.form.get('hasarAciklama', ''),
        musteriImza=musteri_imza,
        musteri_biyometrik_veri_sifreli=biyometrik_sifreli,
        musteri_biyometrik_hash=biyometrik_hash,
        firmaImza=firma_imza,
        is_signed=True,
        imzaTarihi=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        musteriEmail=request.form.get('musteriEmail', '').strip() or None,
        musteriTelefon=request.form.get('musteriTelefon', '').strip() or None,
        sozlesmeDili=dili,
        sozlesmeMetni=metni
    )
    
    ts.add(rental)
    ts.commit()
    invalidate_stats_cache()
    log_action(current_user, 'rental_add', f'Yeni kiralama yapıldı: {rental.plaka}')
    
    # E-posta Bildirimi Gönder (Non-blocking Thread)
    if rental.musteriEmail:
        try:
            import threading
            from utils.mailer import send_email
            subject = f"🚗 Kiralama Sözleşmesi ve Bilgilendirme - {g.current_company.name}"
            
            contract_template = g.current_company.contract_template or ""
            replacements = {
                '{{musteriAdi}}': rental.musteriAdi,
                '{{plaka}}': rental.plaka,
                '{{marka}}': rental.marka,
                '{{model}}': rental.model,
                '{{baslangicTarihi}}': f"{rental.baslangicTarihi} {rental.baslangicSaati}",
                '{{bitisTarihi}}': f"{rental.bitisTarihi} {rental.bitisSaati}",
                '{{kiralamaSuresi}}': f"{rental.kiralamaSuresi} Gün",
                '{{toplamFiyat}}': f"{rental.toplamFiyat} {rental.paraBirimi}",
                '{{odemeYontemi}}': rental.odemeYontemi or 'Nakit',
                '{{verilisteKm}}': f"{rental.verilisteKm} km"
            }
            
            for placeholder, val in replacements.items():
                contract_template = contract_template.replace(placeholder, str(val))
            
            body_html = f"""
            <h3>Sayın {rental.musteriAdi},</h3>
            <p>Firmamızdan yapmış olduğunuz araç kiralama işlemi başarıyla tamamlanmıştır. Detaylar aşağıda belirtilmiştir:</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%; font-size: 13px;">
                <tr style="background-color: #f8fafc;">
                    <th colspan="2">Kiralama Detayları</th>
                </tr>
                <tr><td><b>Araç Plakası</b></td><td>{rental.plaka}</td></tr>
                <tr><td><b>Marka / Model</b></td><td>{rental.marka} {rental.model}</td></tr>
                <tr><td><b>Alış Tarihi</b></td><td>{rental.baslangicTarihi} {rental.baslangicSaati}</td></tr>
                <tr><td><b>İade Tarihi</b></td><td>{rental.bitisTarihi} {rental.bitisSaati}</td></tr>
                <tr><td><b>Kiralama Süresi</b></td><td>{rental.kiralamaSuresi} Gün</td></tr>
                <tr><td><b>Toplam Ücret</b></td><td>{rental.toplamFiyat} {rental.paraBirimi}</td></tr>
                <tr><td><b>Ödeme Yöntemi</b></td><td>{rental.odemeYontemi or 'Belirtilmedi'}</td></tr>
            </table>
            <br>
            <hr>
            <h4>Kiralama Şartları & Sözleşme Metni</h4>
            <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; white-space: pre-wrap; font-size: 12px; color: #334155;">
                {contract_template}
            </div>
            <br>
            <p>İyi yolculuklar dileriz.</p>
            <p><b>{g.current_company.name}</b></p>
            """
            threading.Thread(target=send_email, args=(rental.musteriEmail, subject, body_html), daemon=True).start()
        except Exception as mail_err:
            print(f"[MAIL BİLDİRİM HATA] Kiralama e-postası gönderilemedi: {mail_err}", flush=True)

    flash('Kiralama başarıyla eklendi', 'success')
    return redirect(url_for('fleet.kiralamalar'))

@fleet_bp.route('/kiralamalar/guncelle/<id>', methods=['POST'])
@login_required
def kiralama_guncelle(id):
    if not current_user.get_permissions().get('kiralamalar', {}).get('actions', {}).get('edit') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.kiralamalar'))
    
    rental = ts.query(Rental).filter_by(id=id).first()
    if not rental:
        flash('Kiralama kaydı bulunamadı.', 'error')
        return redirect(url_for('fleet.kiralamalar'))
    
    arac_id = request.form.get('arac_id') or request.form.get('aracId') or rental.arac_id
    if arac_id:
        vehicle = ts.query(Vehicle).filter_by(id=arac_id).first()
        if vehicle:
            rental.arac_id = vehicle.id
            rental.plaka = vehicle.plaka
            rental.marka = vehicle.marka
            rental.model = vehicle.model
    rental.isim = request.form.get('isim', rental.isim)
    rental.soyisim = request.form.get('soyisim', rental.soyisim)
    rental.musteriAdi = f"{rental.isim} {rental.soyisim}".strip()
    rental.uyruk = request.form.get('uyruk', rental.uyruk)
    rental.tcKimlik = request.form.get('tcKimlik', rental.tcKimlik)
    rental.dogumYeri = request.form.get('dogumYeri', rental.dogumYeri)
    rental.kurumAdi = request.form.get('kurumAdi', rental.kurumAdi)
    rental.personelAdi = request.form.get('personelAdi', rental.personelAdi)
    rental.baslangicTarihi = request.form.get('baslangicTarihi', rental.baslangicTarihi)
    rental.baslangicSaati = request.form.get('baslangicSaati', rental.baslangicSaati)
    rental.bitisTarihi = request.form.get('bitisTarihi', rental.bitisTarihi)
    rental.bitisSaati = request.form.get('bitisSaati', rental.bitisSaati)
    rental.kiralamaSuresi = safe_int(request.form.get('kiralamaSuresi')) or rental.kiralamaSuresi
    rental.verilisteKm = safe_int(request.form.get('verilisteKm') or rental.verilisteKm)
    rental.surucuAdSoyad = request.form.get('surucuAdSoyad', rental.surucuAdSoyad)
    rental.ehliyetNo = request.form.get('ehliyetNo', rental.ehliyetNo)
    rental.ehliyetVerilisTarihi = request.form.get('ehliyetVerilisTarihi', rental.ehliyetVerilisTarihi)
    rental.ehliyetGecerlilikTarihi = request.form.get('ehliyetGecerlilikTarihi', rental.ehliyetGecerlilikTarihi)
    rental.paraBirimi = request.form.get('paraBirimi', rental.paraBirimi)
    rental.gunlukFiyat = safe_float(request.form.get('gunlukFiyat'))
    rental.toplamFiyat = safe_float(request.form.get('toplamFiyat'))
    rental.hasarDurumu = request.form.get('hasarDurumu', rental.hasarDurumu)
    rental.hasarAciklama = request.form.get('hasarAciklama', rental.hasarAciklama)
    rental.musteriEmail = request.form.get('musteriEmail', '').strip() or None
    rental.musteriTelefon = request.form.get('musteriTelefon', '').strip() or None
    
    # Contract language and snapshotting
    new_dili = request.form.get('sozlesmeDili')
    if new_dili:
        # If language changed, or if old rental has no snapshot, update snapshot
        if rental.sozlesmeDili != new_dili or not rental.sozlesmeMetni:
            rental.sozlesmeDili = new_dili
            raw_template = g.current_company.contract_template or ''
            metni = raw_template
            if raw_template.startswith('{'):
                try:
                    import json
                    parsed = json.loads(raw_template)
                    metni = parsed.get(new_dili, raw_template)
                except:
                    pass
            rental.sozlesmeMetni = metni

    # Recalculate profit taking existing costs into account
    rental.kar = rental.toplamFiyat - (rental.toplamMaliyet or 0)
    
    try:
        d1 = datetime.strptime(rental.baslangicTarihi, '%Y-%m-%d')
        d2 = datetime.strptime(rental.bitisTarihi, '%Y-%m-%d')
        rental.kiralamaSuresi = max(1, (d2 - d1).days)
    except:
        pass
    
    ts.commit()
    invalidate_stats_cache()
    flash('Kiralama güncellendi', 'success')
    return redirect(url_for('fleet.kiralamalar'))

@fleet_bp.route('/kiralamalar/extend/<id>', methods=['POST'])
@login_required
def kiralama_uzat(id):
    if not current_user.get_permissions().get('kiralamalar', {}).get('actions', {}).get('extend') and not current_user.is_manager:
        return jsonify({'success': False, 'message': 'Bu işlem için yetkiniz bulunmamaktadır.'}), 403

    ts = g.tenant_session
    if not ts: 
        return jsonify({'success': False, 'message': 'Oturum hatası.'}), 400
    
    rental = ts.query(Rental).filter_by(id=id).first()
    if not rental:
        return jsonify({'success': False, 'message': 'Kiralama kaydı bulunamadı.'}), 404
        
    ek_gun = safe_int(request.form.get('ekGun'))
    ek_tutar = safe_float(request.form.get('ekTutar'))
    odeme_yontemi = request.form.get('odemeYontemi')
    
    if ek_gun <= 0:
        return jsonify({'success': False, 'message': 'Geçerli bir gün sayısı giriniz.'}), 400
        
    # Yeni bitiş tarihi hesaplama
    try:
        from datetime import datetime, timedelta
        mevcut_bitis = datetime.strptime(rental.bitisTarihi, '%Y-%m-%d')
        yeni_bitis = mevcut_bitis + timedelta(days=ek_gun)
        rental.bitisTarihi = yeni_bitis.strftime('%Y-%m-%d')
    except Exception as e:
        return jsonify({'success': False, 'message': 'Tarih formatı hatası.'}), 400
        
    rental.kiralamaSuresi = (rental.kiralamaSuresi or 0) + ek_gun
    rental.toplamFiyat = (rental.toplamFiyat or 0.0) + ek_tutar
    rental.kar = rental.toplamFiyat - (rental.toplamMaliyet or 0)
    
    if odeme_yontemi == 'nakit':
        rental.nakitTutar = (rental.nakitTutar or 0.0) + ek_tutar
    elif odeme_yontemi == 'kart':
        rental.kartTutar = (rental.kartTutar or 0.0) + ek_tutar
        
    ts.commit()
    
    return jsonify({'success': True, 'message': 'Süre başarıyla uzatıldı.'})

@fleet_bp.route('/kiralamalar/teslim/<id>', methods=['POST'])
@login_required
def kiralama_teslim(id):
    if not current_user.get_permissions().get('kiralamalar', {}).get('actions', {}).get('edit') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.kiralamalar'))

    alinistaKm_val = request.form.get('alinistaKm')
    if not alinistaKm_val:
        flash('Lütfen Araç Dönüş Kilometresi alanını doldurun', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    rental = ts.query(Rental).filter_by(id=id).first()
    if not rental:
        flash('Kiralama kaydı bulunamadı.', 'error')
        return redirect(url_for('fleet.kiralamalar'))
    
    alinistaKm = safe_int(alinistaKm_val)
    
    if alinistaKm < rental.verilisteKm:
        flash(f'Hata: Dönüş kilometresi ({alinistaKm}), çıkış kilometresinden ({rental.verilisteKm}) küçük olamaz!', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    rental.bitisTarihi = request.form.get('bitisTarihi', rental.bitisTarihi)
    
    # Recalculate duration if return date changed
    try:
        d1 = datetime.strptime(rental.baslangicTarihi, '%Y-%m-%d')
        d2 = datetime.strptime(rental.bitisTarihi, '%Y-%m-%d')
        rental.kiralamaSuresi = max(1, (d2 - d1).days)
    except:
        pass

    rental.alinistaKm = alinistaKm
    rental.kullanilanKm = alinistaKm - rental.verilisteKm
    rental.hasarDurumu = request.form.get('hasarDurumu', 'yok')
    rental.hasarAciklama = request.form.get('hasarAciklama', '')
    rental.teslimAlanPersonel = request.form.get('teslimAlanPersonel', '')
    
    teslim_lat_val = request.form.get('teslim_lat')
    teslim_lng_val = request.form.get('teslim_lng')
    if teslim_lat_val:
        rental.teslim_lat = float(teslim_lat_val)
    if teslim_lng_val:
        rental.teslim_lng = float(teslim_lng_val)
    
    # Recalculate net profit based on updated duration/costs
    rental.kar = (rental.toplamFiyat or 0.0) - (rental.toplamMaliyet or 0.0)
    
    vehicle = ts.query(Vehicle).filter_by(plaka=rental.plaka).first()
    if vehicle:
        if alinistaKm > (vehicle.guncelKm or 0):
            vehicle.guncelKm = alinistaKm
        
    ts.commit()
    invalidate_stats_cache()
    log_action(current_user, 'rental_deliver', f'Araç teslim alındı: {rental.plaka}')
    
    # Hasar Bildirimi Gönder (Non-blocking Thread)
    if rental.hasarDurumu != 'yok' and g.current_company.contact_email:
        try:
            import threading
            from utils.mailer import send_email
            subject = f"🚨 UYARI: Hasarlı Dönüş Bildirimi - Plaka: {rental.plaka} - {g.current_company.name}"
            body_html = f"""
            <h3>Sayın Yönetici,</h3>
            <p>Aşağıda detayları belirtilen kiralama işleminde araç <b>HASARLI</b> olarak iade edilmiştir:</p>
            <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%; font-size: 13px;">
                <tr><td><b>Araç Plakası</b></td><td><b>{rental.plaka}</b> ({rental.marka} {rental.model})</td></tr>
                <tr><td><b>Müşteri Adı</b></td><td>{rental.musteriAdi}</td></tr>
                <tr><td><b>Dönüş Tarihi</b></td><td>{rental.bitisTarihi}</td></tr>
                <tr><td><b>Dönüş Kilometresi</b></td><td>{rental.alinistaKm} km</td></tr>
                <tr style="background-color: #fee2e2; color: #991b1b;">
                    <td><b>Hasar Durumu</b></td>
                    <td><b>{rental.hasarDurumu.upper()} Hasarlı</b></td>
                </tr>
                <tr><td><b>Hasar Açıklaması</b></td><td>{rental.hasarAciklama or 'Açıklama belirtilmemiş.'}</td></tr>
                <tr><td><b>Teslim Alan Personel</b></td><td>{rental.teslimAlanPersonel or 'Belirtilmemiş'}</td></tr>
            </table>
            <br>
            <p>Detayları incelemek için lütfen sisteme giriş yapınız.</p>
            """
            threading.Thread(target=send_email, args=(g.current_company.contact_email, subject, body_html), daemon=True).start()
        except Exception as mail_err:
            print(f"[MAIL BİLDİRİM HATA] Hasar bildirim e-postası gönderilemedi: {mail_err}", flush=True)

    # KABİS Otomatik Teslim (Dönüş) Bildirimi - Devre Dışı
    if False:
        pass
    else:
        flash('Araç teslim işlemi başarıyla gerçekleştirildi.', 'success')
        
    return redirect(url_for('fleet.kiralamalar'))

@fleet_bp.route('/kiralamalar/sil/<id>', methods=['POST'])
@login_required
def kiralama_sil(id):
    if not current_user.get_permissions().get('kiralamalar', {}).get('actions', {}).get('delete') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.kiralamalar'))

    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.kiralamalar'))
    
    rental = ts.query(Rental).filter_by(id=id).first()
    if not rental:
        flash('Kiralama kaydı bulunamadı.', 'error')
        return redirect(url_for('fleet.kiralamalar'))
    
    plaka = rental.plaka
    ts.delete(rental)
    ts.commit()
    invalidate_stats_cache()
    log_action(current_user, 'rental_delete', f'Kiralama kaydı silindi: {plaka}')
    flash('Kiralama silindi', 'success')
    return redirect(url_for('fleet.kiralamalar'))

@fleet_bp.route('/servis')
@login_required
def servis_page():
    if not current_user.get_permissions().get('servis', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))

    if not g.current_company: return redirect(url_for('main.dashboard'))
    ts = g.tenant_session
    if not ts: return redirect(url_for('main.dashboard'))

    page = request.args.get('page', 1, type=int)
    per_page = 20
    total_servis = ts.query(Service).count()
    pages_servis = max(1, (total_servis + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    bakimdaki_araclar = ts.query(Vehicle).filter_by(is_in_maintenance=True, is_deleted=False).all()
    tum_araclar = ts.query(Vehicle).filter_by(is_deleted=False).order_by(Vehicle.plaka).all()
    servis_listesi = ts.query(Service).order_by(Service.tarih.desc()).offset(offset).limit(per_page).all()
    return render_template('servis.html', active_page='servis',
                           bakimdaki_araclar=bakimdaki_araclar,
                           servis_listesi=servis_listesi,
                           tum_araclar=tum_araclar,
                           page=page,
                           pages=pages_servis,
                           total_servis=total_servis,
                           has_prev=(page > 1),
                           has_next=(page < pages_servis))

@fleet_bp.route('/servis/ekle', methods=['POST'])
@login_required
def servis_ekle():
    if not current_user.get_permissions().get('servis', {}).get('actions', {}).get('add') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('fleet.servis_page'))

    ts = g.tenant_session
    if not ts: return redirect(url_for('fleet.servis_page'))

    plaka = request.form.get('plaka')
    if not request.form.get('yer') or not request.form.get('notlar'):
        flash('Bakım Yapılan Yer ve Bakım Notları alanları zorunludur.', 'error')
        return redirect(url_for('fleet.servis_page'))
    
    vehicle = ts.query(Vehicle).filter_by(plaka=plaka).first()
    if vehicle:
        girilen_km = safe_int(request.form.get('km'))
        min_km = safe_int(request.form.get('min_km') or vehicle.bakim_gidis_km)
        
        if girilen_km < min_km:
            flash(f'Hata: Bakım dönüş kilometresi ({girilen_km}), gidiş kilometresinden ({min_km}) küçük olamaz!', 'error')
            return redirect(url_for('fleet.servis_page'))

        service = Service(
            arac_id=vehicle.id,
            plaka=plaka,
            km=girilen_km,
            ucret=safe_float(request.form.get('ucret')),
            paraBirimi=request.form.get('paraBirimi', '₺'),
            yer=request.form.get('yer'),
            kisi=request.form.get('kisi'),
            gidis_tarihi=request.form.get('gidis_tarihi', vehicle.bakim_gidis_tarihi),
            tarih=request.form.get('tarih', datetime.now().strftime('%Y-%m-%d')),
            notlar=request.form.get('notlar')
        )
        vehicle.is_in_maintenance = False
        if service.km > vehicle.guncelKm:
            vehicle.guncelKm = service.km
        vehicle.bakimYapildigiKm = service.km
        
        vehicle.bakim_gonderen = ''
        vehicle.bakim_gidis_km = 0
        vehicle.bakim_gidis_tarihi = ''
        
        ts.add(service)
        ts.commit()
        invalidate_stats_cache()
        log_action(current_user, 'service_add', f'Servis kaydı eklendi: {plaka}')
        flash('Servis kaydı başarıyla oluşturuldu.', 'success')
    return redirect(url_for('fleet.servis_page'))

@fleet_bp.route('/kiralama_arac_km')
@login_required
def api_arac_km():
    ts = g.tenant_session
    if not ts:
        return jsonify({'success': False, 'guncelKm': 0, 'alisKm': 0})
    
    plaka = request.args.get('plaka')
    v = ts.query(Vehicle).filter_by(plaka=plaka).first()
    if v:
        return jsonify({
            'success': True, 
            'guncelKm': v.guncelKm,
            'alisKm': v.alisKm,
            'gunlukUcret': v.gunlukUcret or 0
        })
    return jsonify({'success': False, 'guncelKm': 0, 'alisKm': 0})

# KABİS Entegrasyonu - Devre Dışı
@fleet_bp.route('/kiralamalar/kabis_bildir/<id>', methods=['POST'])
@login_required
def kabis_bildir(id):
    return jsonify({'success': False, 'message': 'KABİS entegrasyonu pasife alınmıştır.'}), 400

@fleet_bp.route('/kiralamalar/kabis_teslim_bildir/<id>', methods=['POST'])
@login_required
def kabis_teslim_bildir(id):
    return jsonify({'success': False, 'message': 'KABİS entegrasyonu pasife alınmıştır.'}), 400

@fleet_bp.route('/kiralamalar/kabis_xml/<id>')
@login_required
def kabis_xml(id):
    flash('KABİS entegrasyonu pasife alınmıştır.', 'error')
    return redirect(url_for('fleet.kiralamalar'))


@fleet_bp.route('/kiralamalar/imzala/<id>', methods=['POST'])
@login_required
def kiralama_imzala(id):
    ts = g.tenant_session
    if not ts:
        return jsonify({'success': False, 'message': 'Veritabanı bağlantısı yok.'}), 500
        
    rental = ts.query(Rental).filter_by(id=id).first()
    if not rental:
        return jsonify({'success': False, 'message': 'Kiralama kaydı bulunamadı.'}), 404
        
    musteri_imza = request.json.get('musteriImza')
    firma_imza = request.json.get('firmaImza')
    biyometrik_json = request.json.get('biyometrikVeri')
    
    if not musteri_imza or not musteri_imza.startswith('data:image/png;base64,'):
        return jsonify({'success': False, 'message': 'Geçersiz müşteri imzası.'}), 400
    if not firma_imza or not firma_imza.startswith('data:image/png;base64,'):
        return jsonify({'success': False, 'message': 'Geçersiz firma imzası.'}), 400
        
    try:
        rental.musteriImza = musteri_imza
        rental.firmaImza = firma_imza
        
        if biyometrik_json and len(biyometrik_json) > 10:
            try:
                rental.musteri_biyometrik_hash = hashlib.sha256(biyometrik_json.encode('utf-8')).hexdigest()
                key_str = os.getenv('ENCRYPTION_KEY')
                if key_str:
                    fernet = Fernet(key_str.encode('utf-8'))
                    rental.musteri_biyometrik_veri_sifreli = fernet.encrypt(biyometrik_json.encode('utf-8')).decode('utf-8')
            except Exception as e:
                print(f"[BIOMETRIC ENCRYPTION ERROR] {e}", flush=True)

        rental.is_signed = True
        rental.imzaTarihi = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        ts.commit()
        log_action(current_user, 'rental_sign', f'Kiralama sözleşmesi imzalandı: {rental.plaka}')
        return jsonify({'success': True, 'message': 'Sözleşme başarıyla imzalandı.'})
    except Exception as e:
        ts.rollback()
        return jsonify({'success': False, 'message': f'Sözleşme kaydedilemedi: {str(e)}'}), 500


@fleet_bp.route('/kiralamalar/sozlesme/<id>')
@login_required
def kiralama_sozlesme(id):
    ts = g.tenant_session
    if not ts:
        flash('Veritabanı bağlantısı yok.', 'error')
        return redirect(url_for('fleet.kiralamalar'))
        
    rental = ts.query(Rental).filter_by(id=id).first()
    if not rental:
        flash('Kiralama kaydı bulunamadı.', 'error')
        return redirect(url_for('fleet.kiralamalar'))
        
    company = g.current_company
    
    final_contract_text = rental.sozlesmeMetni
    
    # Fallback if contract text is empty or corrupted (e.g. contains multiple consecutive question marks due to encoding failure)
    if not final_contract_text or '?????' in final_contract_text:
        raw = company.contract_template or ''
        if raw.startswith('{'):
            try:
                import json
                parsed = json.loads(raw)
                final_contract_text = parsed.get(rental.sozlesmeDili or 'TR', raw)
            except:
                final_contract_text = raw
        else:
            final_contract_text = raw
            
    return render_template('sozlesme.html', rental=rental, company=company, final_contract_text=final_contract_text)
