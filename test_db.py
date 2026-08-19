
from app import create_app
import pyodbc

app = create_app()
with app.app_context():
    server = app.config['DB_SERVER']
    driver = app.config['DB_DRIVER']
    user_db = app.config.get('DB_USER')
    pass_db = app.config.get('DB_PASS')

    if user_db and pass_db:
        conn_str = f'Driver={{{driver}}};Server={server};Database=TurMasterDB;UID={user_db};PWD={pass_db};Encrypt=no;TrustServerCertificate=yes;'
    else:
        conn_str = f'Driver={{{driver}}};Server={server};Database=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;'
        
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute('''SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ''SystemUsers'' ''')
    print('SystemUsers columns:', cursor.fetchall())
    cursor.execute('''SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ''Agencies'' ''')
    print('Agencies columns:', cursor.fetchall())

