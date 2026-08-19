import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(to_email, subject, body_html):
    """Send an HTML email using SMTP configuration from environment variables."""
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")

    # If SMTP_SERVER is not set or empty, skip sending to prevent errors
    if not smtp_server or not smtp_user:
        print("[MAILER] SMTP Server or User is not configured. Skipping email dispatch.", flush=True)
        return False

    try:
        smtp_port = int(smtp_port) if smtp_port else 587
    except ValueError:
        smtp_port = 587

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to_email

    # Rich premium HTML wrapper
    styled_html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Outfit', 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                color: #1e293b;
                line-height: 1.6;
                margin: 0;
                padding: 0;
                background-color: #f8fafc;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.025);
            }}
            .header {{
                background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
                color: #ffffff;
                padding: 30px 20px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: -0.025em;
            }}
            .content {{
                padding: 30px 20px;
            }}
            .footer {{
                background-color: #f1f5f9;
                color: #64748b;
                text-align: center;
                padding: 20px;
                font-size: 12px;
                border-top: 1px solid #e2e8f0;
            }}
            a {{
                color: #2563eb;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>ZYRONOVA BİLDİRİM SİSTEMİ</h1>
            </div>
            <div class="content">
                {body_html}
            </div>
            <div class="footer">
                Bu e-posta <b>Zyronova Araç Kiralama Portalı</b> aracılığıyla otomatik olarak gönderilmiştir.<br>
                © 2026 Zyronova. Tüm hakları saklıdır.
            </div>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(styled_html, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_email, msg.as_string())
        server.quit()
        print(f"[MAILER] Email successfully sent to {to_email} with subject: {subject}", flush=True)
        return True
    except Exception as e:
        print(f"[MAILER ERROR] Failed to send email to {to_email}: {e}", flush=True)
        return False
