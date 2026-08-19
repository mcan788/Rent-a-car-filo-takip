import pyodbc

db_address = r"localhost\SQLEXPRESS"
rent_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_address};DATABASE=ZYRONOVA_MASTER;Trusted_Connection=yes;"

try:
    print(f"Connecting to ZYRONOVA_MASTER...")
    conn = pyodbc.connect(rent_conn_str)
    cursor = conn.cursor()
    
    # Get the company ID for user '35'
    cursor.execute("SELECT id, username, company_id FROM users WHERE username = '35'")
    user = cursor.fetchone()
    if not user:
        print("User '35' not found in ZYRONOVA_MASTER.users")
    else:
        print(f"Found user '35': UserID={user.id}, CompanyID={user.company_id}")
        
        # Get the company subdomain
        cursor.execute("SELECT id, name, subdomain FROM companies WHERE id = ?", user.company_id)
        company = cursor.fetchone()
        if not company:
            print("Company not found for this user!")
        else:
            print(f"Company Found: Name='{company.name}', Subdomain='{company.subdomain}'")
            db_name = company.subdomain.lower()
            
            # Connect to the tenant database
            tenant_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={db_address};DATABASE={db_name};Trusted_Connection=yes;"
            try:
                t_conn = pyodbc.connect(tenant_conn_str)
                t_cursor = t_conn.cursor()
                
                # Count vehicles
                t_cursor.execute("SELECT count(*) FROM vehicles")
                v_count = t_cursor.fetchone()[0]
                print(f"\nThere are {v_count} vehicles in {db_name}.vehicles")
                
                if v_count > 0:
                    # Print first 5 vehicles to see if they look like dummy data
                    t_cursor.execute("SELECT TOP 5 plaka, marka, model, yil FROM vehicles")
                    print("Sample vehicles:")
                    for v in t_cursor.fetchall():
                        print(f"  {v.plaka} - {v.marka} {v.model} ({v.yil})")
                        
                t_conn.close()
            except Exception as e:
                print(f"Failed to connect to tenant DB {db_name}: {e}")

    conn.close()
except Exception as e:
    print(f"Error: {e}")
