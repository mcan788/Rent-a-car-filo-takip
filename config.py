import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY or SECRET_KEY == 'rentacar-ciro-secret-key-2026':
        raise RuntimeError("CRITICAL SECURITY ERROR: SECRET_KEY is not configured or insecure fallback is used in .env!")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_REFRESH_EACH_REQUEST = True
    
    # Multi-tenant DB settings
    DB_SERVER = os.getenv('DB_SERVER', 'localhost')
    DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    # Robust connection string for SQL Server
    import urllib.parse
    # Ensure TCP/IP works even if DB_SERVER uses the local pipe alias '.'
    _tcp_server = DB_SERVER.replace('.\\', 'localhost\\') if DB_SERVER.startswith('.\\') else DB_SERVER
    
    if DB_USER and DB_PASSWORD:
        # Docker/Production with SQL Authentication
        _conn_str = f"DRIVER={{{DB_DRIVER}}};SERVER={_tcp_server};DATABASE=ZYRONOVA_MASTER;UID={DB_USER};PWD={DB_PASSWORD};Encrypt=no;TrustServerCertificate=yes"
    else:
        # Local Windows Development with Windows Authentication
        _conn_str = f"DRIVER={{{DB_DRIVER}}};SERVER={_tcp_server};DATABASE=ZYRONOVA_MASTER;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes"
    
    _params = urllib.parse.quote_plus(_conn_str)
    SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={_params}"
    
    # Custom configurations
    TCMB_XML_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
