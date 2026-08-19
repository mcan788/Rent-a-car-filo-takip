import pyodbc

db_address = r"localhost\SQLEXPRESS"
sys_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_address};DATABASE=model;Trusted_Connection=yes;"

try:
    print(f"Connecting to model database at {db_address} ...")
    conn = pyodbc.connect(sys_conn_str)
    cursor = conn.cursor()
    
    # Check if 'vehicles' table exists in model DB
    cursor.execute("SELECT count(*) FROM sys.tables WHERE name = 'vehicles'")
    has_vehicles_table = cursor.fetchone()[0] > 0
    
    if has_vehicles_table:
        print("Table 'vehicles' exists in model database!")
        cursor.execute("SELECT count(*) FROM vehicles")
        count = cursor.fetchone()[0]
        print(f"There are {count} vehicles in the model database.")
    else:
        print("Table 'vehicles' DOES NOT exist in model database.")
        
    # Check if 'Vehicles' table exists (capitalized, TurTakip schema)
    cursor.execute("SELECT count(*) FROM sys.tables WHERE name = 'Vehicles'")
    has_Vehicles_table = cursor.fetchone()[0] > 0
    
    if has_Vehicles_table:
        print("Table 'Vehicles' exists in model database!")
        cursor.execute("SELECT count(*) FROM Vehicles")
        count = cursor.fetchone()[0]
        print(f"There are {count} Vehicles in the model database.")

    conn.close()
    print("Check complete.")
except Exception as e:
    print(f"Error: {e}")
