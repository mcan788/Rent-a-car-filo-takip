import pyodbc
import sys

print("Connecting to ZYRONOVA_MASTER database with autocommit=True...")
conn_str = "Driver={ODBC Driver 17 for SQL Server};Server=localhost\\SQLEXPRESS;Database=ZYRONOVA_MASTER;Trusted_Connection=yes;Encrypt=no;TrustServerCertificate=yes;"

try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    print("Connected successfully!")
except Exception as e:
    print("Connection failed:", e)
    sys.exit(1)

# Helper function to check if column exists
def column_exists(table, column):
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM sys.columns 
        WHERE object_id = OBJECT_ID('{table}') AND name = '{column}';
    """)
    return cursor.fetchone()[0] > 0

# 1. Check and add tax_no
print("Checking column 'tax_no'...")
if not column_exists('companies', 'tax_no'):
    print("Adding column 'tax_no'...")
    cursor.execute("ALTER TABLE companies ADD tax_no VARCHAR(20) NULL;")
    print("Column 'tax_no' added successfully.")
else:
    print("Column 'tax_no' already exists.")

# 2. Check and add contract_template
print("Checking column 'contract_template'...")
if not column_exists('companies', 'contract_template'):
    print("Adding column 'contract_template'...")
    cursor.execute("ALTER TABLE companies ADD contract_template NVARCHAR(MAX) NULL;")
    print("Column 'contract_template' added successfully.")
    
    default_text = """1. TARAFLAR VE SÖZLEŞME KONUSU
Bu sözleşme, bir tarafta aracı kiraya veren (aşağıda KİRALAYAN olarak anılacaktır) ile diğer tarafta aracı kiralayan (aşağıda KİRACI olarak anılacaktır) arasında akdedilmiştir. Sözleşmenin konusu, belirtilen şartlar dahilinde aracın kiralanmasıdır.

2. ARACIN TESLİMİ VE KULLANIMI
Kiracı, aracı karayolları trafik kanunlarına, genel ahlaka ve kiralama şartlarına uygun olarak kullanacaktır. Araç, kiralama sözleşmesinde ismi belirtilmeyen üçüncü kişiler tarafından kullanılamaz. Aracın kullanımı sırasında oluşabilecek her türlü hukuki, cezai ve mali sorumluluk kiracıya aittir.

3. KİRA SÜRESİ VE İADE
Kiracı, aracı sözleşmede belirtilen yer ve tarihte eksiksiz ve hasarsız teslim etmekle yükümlüdür. Gecikme durumunda ek ücret yansıtılacaktır.

4. SİGORTA VE HASAR DURUMU
Araç kasko ve sigorta kapsamında olup, kural ihlalleri, alkollü kullanım veya yetkisiz sürücü kullanımı gibi durumlarda sigorta geçersiz kalacak ve tüm hasar maliyeti kiracıdan tahsil edilecektir.

5. UYUŞMAZLIKLARIN ÇÖZÜMÜ
Bu sözleşmeden doğan her türlü uyuşmazlığın çözümünde, kiralayan şirketin merkezinin bulunduğu yerdeki Mahkemeler ve İcra Daireleri yetkilidir."""
    cursor.execute("UPDATE companies SET contract_template = ? WHERE contract_template IS NULL;", (default_text,))
    print("Default contract templates populated.")
else:
    print("Column 'contract_template' already exists.")

# 3. Check and add KABIS columns
kabis_cols = ['kabis_username', 'kabis_password', 'kabis_sirket_kodu']
kabis_types = ['VARCHAR(100) NULL', 'VARCHAR(255) NULL', 'VARCHAR(50) NULL']

for col, col_type in zip(kabis_cols, kabis_types):
    print(f"Checking column '{col}'...")
    if not column_exists('companies', col):
        print(f"Adding column '{col}'...")
        cursor.execute(f"ALTER TABLE companies ADD {col} {col_type};")
        print(f"Column '{col}' added successfully.")
    else:
        print(f"Column '{col}' already exists.")

print("All migrations completed successfully!")
cursor.close()
conn.close()
