
from app import create_app
from extensions import db
from models import User
import pyodbc

app = create_app()
with app.app_context():
    server = app.config.get('DB_SERVER')
    driver = app.config.get('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    user_db = app.config.get('DB_USER')
    pass_db = app.config.get('DB_PASS')

    conn_str = f'Driver={{{driver}}};Server={server};Database=TurMasterDB;'
    if user_db and pass_db:
        conn_str += f'UID={user_db};PWD={pass_db};Encrypt=no;TrustServerCertificate=yes;'
    else:
        conn_str += 'Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;'

    try:
        with pyodbc.connect(conn_str, timeout=5) as conn:
            with conn.cursor() as cursor:
                users = User.query.filter_by(company_id=1).all()
                for user in users:
                    cursor.execute('SELECT Username FROM SystemUsers WHERE Username = ?', (user.username,))
                    if not cursor.fetchone():
                        sys_role = 'SUPERADMIN' if user.role_id == 11 else 'ADMIN'
                        cursor.execute(
                            'INSERT INTO SystemUsers (Username, PasswordHash, FullName, Role) VALUES (?, ?, ?, ?)',
                            (user.username, user.password_hash, user.name, sys_role)
                        )
                        print(f'Synced: {user.username}')
                conn.commit()
                print('Sync completed.')
    except Exception as e:
        print(f'Error: {e}')

