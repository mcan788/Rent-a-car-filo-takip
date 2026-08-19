import os
import sys
from redis import Redis
from rq import Worker, Queue
from app import create_app

# Flask uygulamasi olusturuluyor ki ORM ve eklentiler arka planda da duzgun calissin
app = create_app()

# Hangi kuyruklari dinleyecegi belirtiliyor
listen = ['default']
redis_conn = Redis(host='localhost', port=6379, db=0, protocol=2)

if __name__ == '__main__':
    # Flask app context'i icinde calistiriyoruz ki current_app'i kullanan veritabani servisleri cokmesin
    with app.app_context():
        print("[RQ WORKER] Kuyruk islemcisi baslatildi, is bekleniyor...")
        qs = [Queue(q, connection=redis_conn) for q in listen]
        worker = Worker(qs, connection=redis_conn)
        worker.work()
