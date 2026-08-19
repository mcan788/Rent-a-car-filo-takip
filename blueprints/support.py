from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from flask_login import login_required, current_user
from extensions import db
from models import SupportTicket, SupportTicketMessage
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
import os
from flask import current_app
from utils.helpers import log_action

support_bp = Blueprint('support', __name__, url_prefix='/destek')

@support_bp.route('/')
@login_required
def destek_talepleri():
    if not current_user.is_manager:
        flash('Bu sayfa için yetkiniz bulunmamaktadır.', 'error')
        return redirect(url_for('main.dashboard'))
        
    tickets = SupportTicket.query.filter_by(company_id=g.current_company.id).order_by(SupportTicket.updated_at.desc()).all()
    return render_template('support.html', active_page='support', tickets=tickets)

@support_bp.route('/yeni', methods=['POST'])
@login_required
def yeni_talep():
    if not current_user.is_manager:
        flash('Yetkisiz işlem.', 'error')
        return redirect(url_for('support.destek_talepleri'))
        
    subject = request.form.get('subject')
    category = request.form.get('category', 'Genel Destek')
    priority = request.form.get('priority', 'Normal')
    message = request.form.get('message')
    
    if not subject or not message:
        flash('Konu ve mesaj zorunludur.', 'error')
        return redirect(url_for('support.destek_talepleri'))
        
    ticket = SupportTicket(
        company_id=g.current_company.id,
        user_id=current_user.id,
        subject=subject,
        category=category,
        priority=priority
    )
    db.session.add(ticket)
    db.session.commit() # Get ticket id
    
    attachment_path = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            filename = secure_filename(f"{ticket.id}_{file.filename}")
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'support')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            attachment_path = f"/static/uploads/support/{filename}"
    
    msg = SupportTicketMessage(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        is_master=False,
        message=message,
        attachment_path=attachment_path
    )
    db.session.add(msg)
    db.session.commit()
    
    log_action(current_user, 'support_ticket_create', f"Yeni destek talebi açıldı: {subject}")
    flash('Destek talebiniz başarıyla iletildi.', 'success')
    return redirect(url_for('support.destek_talepleri'))

@support_bp.route('/<ticket_id>/cevap', methods=['POST'])
@login_required
def cevap_yaz(ticket_id):
    if not current_user.is_manager:
        flash('Yetkisiz işlem.', 'error')
        return redirect(url_for('support.destek_talepleri'))
        
    ticket = SupportTicket.query.filter_by(id=ticket_id, company_id=g.current_company.id).first_or_404()
    
    if ticket.status == 'Kapalı':
        flash('Bu destek talebi kapatılmıştır. Yeni bir mesaj gönderemezsiniz.', 'error')
        return redirect(url_for('support.destek_talepleri'))
        
    message = request.form.get('message')
    
    attachment_path = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            filename = secure_filename(f"reply_{ticket.id}_{file.filename}")
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'support')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            attachment_path = f"/static/uploads/support/{filename}"
            
    if message or attachment_path:
        msg = SupportTicketMessage(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            is_master=False,
            message=message or 'Dosya eklendi',
            attachment_path=attachment_path
        )
        db.session.add(msg)
        ticket.status = 'Açık' # User replied, set to Açık
        ticket.updated_at = datetime.now()
        db.session.commit()
        flash('Cevabınız gönderildi.', 'success')
        
    return redirect(url_for('support.destek_talepleri'))
