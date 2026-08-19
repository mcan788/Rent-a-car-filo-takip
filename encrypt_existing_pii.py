import os
import pyodbc
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import uuid

# Load existing .env
load_dotenv()

def generate_key():
    key = Fernet.generate_key().decode('utf-8')
    with open('.env', 'a') as f:
        f.write(f"\nENCRYPTION_KEY={key}\n")
    print(f"Generated new ENCRYPTION_KEY: {key}")
    return key

from sqlalchemy import text
from app import app
from extensions import get_tenant_session

def encrypt_data():
    key_str = os.getenv('ENCRYPTION_KEY')
    if not key_str:
        key_str = generate_key()
    
    fernet = Fernet(key_str.encode('utf-8'))
    
    with app.app_context():
        # Get all subdomains from companies
        from models import Company
        companies = Company.query.all()
        subdomains = [c.subdomain for c in companies if c.subdomain not in ['sa', 'master', 'admin', 'www']]
        # add RentACarDemo manually if not in list
        if 'RentACarDemo' not in subdomains:
            subdomains.append('RentACarDemo')
            
        for subdomain in subdomains:
            print(f"Processing tenant: {subdomain}")
            ts = get_tenant_session(subdomain)
            if not ts:
                print(f"Failed to get session for {subdomain}")
                continue
                
            try:
                # Alter columns to hold encrypted string
                ts.execute(text("ALTER TABLE rentals ALTER COLUMN tcKimlik VARCHAR(255)"))
                ts.execute(text("ALTER TABLE rentals ALTER COLUMN ehliyetNo VARCHAR(255)"))
                ts.commit()
            except Exception as e:
                print(f"Alter failed (might already be large enough): {e}")
                ts.rollback()
                
            try:
                rows = ts.execute(text("SELECT id, tcKimlik, ehliyetNo FROM rentals")).fetchall()
                update_count = 0
                for row in rows:
                    r_id, tc_kimlik, ehliyet_no = row
                    updates = {}
                    
                    if tc_kimlik and len(tc_kimlik) < 50:
                        enc_tc = fernet.encrypt(tc_kimlik.encode('utf-8')).decode('utf-8')
                        updates["tcKimlik"] = enc_tc
                        
                    if ehliyet_no and len(ehliyet_no) < 50:
                        enc_ehliyet = fernet.encrypt(ehliyet_no.encode('utf-8')).decode('utf-8')
                        updates["ehliyetNo"] = enc_ehliyet
                        
                    if updates:
                        set_clause = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                        updates["id"] = r_id
                        ts.execute(text(f"UPDATE rentals SET {set_clause} WHERE id = :id"), updates)
                        update_count += 1
                        
                ts.commit()
                print(f"Updated {update_count} rows in {subdomain}")
            except Exception as e:
                print(f"Update failed for {subdomain}: {e}")
                ts.rollback()
            finally:
                ts.close()
                
    print("Migration complete.")

if __name__ == '__main__':
    encrypt_data()
