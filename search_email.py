import pyodbc

db_address = r"localhost\SQLEXPRESS"
tur_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_address};DATABASE=TurMasterDB;Trusted_Connection=yes;"

email_to_search = '%mcan%'.strip().lower()

try:
    print(f"Connecting to {db_address} ...")
    conn = pyodbc.connect(tur_conn_str)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM SystemUsers WHERE LOWER(Username) LIKE ?", email_to_search)
    users = cursor.fetchall()
    if users:
        print("Found in SystemUsers!")
        for u in users:
            print(f"  UserID: {u.UserID}, Username: {u.Username}")

    conn.close()
    print("Search complete.")
except Exception as e:
    print(f"Error: {e}")
