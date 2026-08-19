from app import app
from extensions import db
import pyodbc

with app.app_context():
    server = app.config['DB_SERVER']
    driver = app.config['DB_DRIVER']
    user_db = app.config.get('DB_USER')
    pass_db = app.config.get('DB_PASSWORD')
    
    if user_db and pass_db:
        conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;UID={user_db};PWD={pass_db};Encrypt=no;TrustServerCertificate=yes;"
    else:
        conn_str = f"Driver={{{driver}}};Server={server};Database=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"
    
    try:
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT Username, Role FROM SystemUsers WHERE Username = 'Demir_enes' OR Username = 'demir_enes'")
                row = cursor.fetchone()
                if row:
                    print(f"User Found in SystemUsers! Username: {row[0]}, Role: {row[1]}")
                else:
                    print("User NOT found in SystemUsers!")
    except Exception as e:
        print("Error connecting to TurMasterDB:", e)
