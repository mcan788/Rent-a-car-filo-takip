import time
import pyodbc

conn_strs = [
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\SQLEXPRESS;DATABASE=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes",
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes",
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=(local)\SQLEXPRESS;DATABASE=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes"
]

for cs in conn_strs:
    print(f"Testing: {cs.split('SERVER=')[1].split(';')[0]}")
    start = time.time()
    try:
        conn = pyodbc.connect(cs, timeout=10)
        conn.close()
        print(f"Success in {time.time() - start:.3f} seconds\n")
    except Exception as e:
        print(f"Failed in {time.time() - start:.3f} seconds: {e}\n")
