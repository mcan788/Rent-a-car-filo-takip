import pyodbc

conn_str = 'Driver={ODBC Driver 17 for SQL Server};Server=.\SQLEXPRESS;Database=ZYRONOVA_MASTER;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;'
try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute("SELECT username, role_id, company_id FROM users")
    rows = cursor.fetchall()
    for row in rows:
        print(f"User: {row[0]}, RoleID: {row[1]}, CompanyID: {row[2]}")
except Exception as e:
    print('ERROR:', e)
