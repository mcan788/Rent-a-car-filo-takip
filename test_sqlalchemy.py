import urllib.parse
from sqlalchemy import create_engine

conn_strs = [
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes",
    r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=(local)\SQLEXPRESS;DATABASE=TurMasterDB;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes"
]

for cs in conn_strs:
    print(f"Testing: {cs}")
    try:
        params = urllib.parse.quote_plus(cs)
        engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
        with engine.connect() as conn:
            print("Success!")
    except Exception as e:
        print(f"Failed: {e}")
