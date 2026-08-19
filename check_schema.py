import pyodbc

conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=ZYRONOVA_MASTER;Trusted_Connection=yes;')
cr = conn.cursor()
cr.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Users'")
print("ZYRONOVA_MASTER Users:")
for row in cr.fetchall():
    print(row)

try:
    conn_r = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=RENT_A_CAR_DEMO_DB;Trusted_Connection=yes;')
    cr_r = conn_r.cursor()
    cr_r.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Users'")
    print("RENT_A_CAR_DEMO_DB Users:")
    for row in cr_r.fetchall():
        print(row)
except Exception as e:
    pass

try:
    conn_t = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=TUR_TAKIP_DEMO_DB;Trusted_Connection=yes;')
    cr_t = conn_t.cursor()
    cr_t.execute("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'Staff'")
    print("TUR_TAKIP_DEMO_DB Staff:")
    for row in cr_t.fetchall():
        print(row)
except Exception as e:
    pass
