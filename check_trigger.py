import pyodbc

conn = pyodbc.connect('Driver={SQL Server};Server=.\SQLEXPRESS;Database=TurMasterDB;Trusted_Connection=yes;')
cursor = conn.cursor()
cursor.execute("SELECT OBJECT_DEFINITION(OBJECT_ID('TRG_AfterAgencyInsert'))")
row = cursor.fetchone()
if row and row[0]:
    print(row[0])
else:
    print("Trigger not found.")
