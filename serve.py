from waitress import serve
from app import create_app
import logging

# Hataları takip edebilmek için loglamayı açıyoruz
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('waitress')

app = create_app()

if __name__ == '__main__':
    print("========================================")
    print("   ZYRONOVA SaaS SERVISI BASLATILDI")
    print("   Yayin: http://127.0.0.1:8080 (IIS Proxy)")
    print("========================================")
    
    try:
        serve(app, host='127.0.0.1', port=8080, threads=32)
    except KeyboardInterrupt:
        print("\nServis durduruldu.")
