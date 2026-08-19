import pyodbc

try:
    conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=ZYRONOVA_MASTER;Trusted_Connection=yes;')
    cr = conn.cursor()
    # Check if OwnerPhone exists, if not, rename OwnerEmail to OwnerPhone
    cr.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Agencies' AND COLUMN_NAME = 'OwnerPhone'")
    if not cr.fetchone():
        print("Renaming OwnerEmail to OwnerPhone in Agencies table...")
        cr.execute("EXEC sp_rename 'Agencies.OwnerEmail', 'OwnerPhone', 'COLUMN'")
        conn.commit()
        print("Column renamed successfully.")
    else:
        print("OwnerPhone column already exists.")
except Exception as e:
    print(f"Error: {e}")
