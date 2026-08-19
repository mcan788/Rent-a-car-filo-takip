from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, g
from flask_login import login_required, current_user
from extensions import db
from models import Vehicle, Rental, Company
from utils.helpers import safe_int, safe_float
import os
import pandas as pd
from datetime import datetime
from io import BytesIO

reports_bp = Blueprint('reports', __name__)

from utils.stats import get_report_data

@reports_bp.route('/rapor')
@login_required
def rapor():
    if not current_user.get_permissions().get('rapor', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
    
    filter_type = request.args.get('type', 'hepsi')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    page = request.args.get('page', 1, type=int)
    per_page = 15
    
    report_data = get_report_data(start_date, end_date, page=page, per_page=per_page)
    
    total_rentals = report_data.pop('total_rentals', 0)
    pages = (total_rentals + per_page - 1) // per_page if total_rentals > 0 else 1
    has_prev = page > 1
    has_next = page < pages
    
    return render_template('rapor.html', 
                           active_page='rapor',
                           filter_type=filter_type,
                           start_date=start_date,
                           end_date=end_date,
                           page=page,
                           pages=pages,
                           total_rentals=total_rentals,
                           has_prev=has_prev,
                           has_next=has_next,
                           per_page=per_page,
                           **report_data)

@reports_bp.route('/excel')
@login_required
def excel_page():
    if not current_user.get_permissions().get('excel', {}).get('all') and not current_user.is_manager:
        flash('Bu sayfaya erişim yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('excel.html', active_page='excel')

@reports_bp.route('/excel/export/<type>')
@login_required
def excel_export(type):
    if not current_user.get_permissions().get('excel', {}).get('all') and not current_user.is_manager:
        flash('Bu işlem için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))

    ts = g.tenant_session
    if not ts:
        flash('Veritabanı bağlantısı kurulamadı.', 'error')
        return redirect(url_for('reports.excel_page'))
    
    from extensions import get_tenant_engine
    tenant_engine = get_tenant_engine(g.current_company.subdomain)
    
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    if type == 'araclar':
        df = pd.read_sql(ts.query(Vehicle).statement, tenant_engine)
    elif type == 'kiralamalar':
        df = pd.read_sql(ts.query(Rental).statement, tenant_engine)
    else:
        return "Invalid type", 400
    
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    writer.close()
    output.seek(0)
    
    return send_file(output, as_attachment=True, download_name=f"{type}_{datetime.now().strftime('%Y%m%d')}.xlsx")

@reports_bp.route('/excel/import', methods=['POST'])
@login_required
def excel_import():
    if not current_user.get_permissions().get('excel', {}).get('all') and not current_user.is_manager:
        flash('Yetkiniz yok.', 'error')
        return redirect(url_for('reports.excel_page'))
    
    # Import logic placeholder
    flash('Excel içe aktarma özelliği şu an geliştirme aşamasındadır.', 'info')
    return redirect(url_for('reports.excel_page'))

@reports_bp.route('/excel/template/<type>')
@login_required
def excel_template(type):
    # Template download logic placeholder
    flash('Excel şablon indirme özelliği şu an geliştirme aşamasındadır.', 'info')
    return redirect(url_for('reports.excel_page'))
