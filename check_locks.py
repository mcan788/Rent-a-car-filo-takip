import pyodbc
import sys

print("Connecting to master database...")
conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=(local)\\SQLEXPRESS;Database=master;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    print("Connected to master successfully!")
except Exception as e:
    print("Connection to master failed:", e)
    sys.exit(1)

print("\n--- ACTIVE BLOCKED / BLOCKING PROCESSES ---")
try:
    cursor.execute("""
        SELECT 
            spid, 
            blocked, 
            waittime, 
            lastwaittype, 
            status, 
            db_name(dbid) as dbname, 
            cmd 
        FROM sys.sysprocesses 
        WHERE blocked <> 0 OR spid IN (SELECT blocked FROM sys.sysprocesses WHERE blocked <> 0);
    """)
    rows = cursor.fetchall()
    if not rows:
        print("No blocking processes detected.")
    else:
        for r in rows:
            print(f"SPID: {r.spid} | Blocked By: {r.blocked} | Wait Time: {r.waittime} ms | Wait Type: {r.lastwaittype} | Status: {r.status} | DB: {r.dbname} | Cmd: {r.cmd}")
except Exception as e:
    print("Query failed:", e)

print("\n--- DATABASE STATUSES ---")
try:
    cursor.execute("SELECT name, state_desc, user_access_desc FROM sys.databases;")
    for r in cursor.fetchall():
        print(f"Database: {r.name} | State: {r.state_desc} | Access: {r.user_access_desc}")
except Exception as e:
    print("Query failed:", e)

cursor.close()
conn.close()
