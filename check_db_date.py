import pyodbc

db_address = r"localhost\SQLEXPRESS"
sys_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_address};DATABASE=master;Trusted_Connection=yes;"

try:
    conn = pyodbc.connect(sys_conn_str)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, create_date FROM sys.databases WHERE name = 'zyronova'")
    db_info = cursor.fetchone()
    
    if db_info:
        print(f"Database '{db_info.name}' was created on: {db_info.create_date}")
    else:
        print("Database 'zyronova' not found.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
