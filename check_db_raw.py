from app import app
from extensions import get_tenant_session
from sqlalchemy import text

with app.app_context():
    ts = get_tenant_session('RentACarDemo')
    rows = ts.execute(text('SELECT tcKimlik, ehliyetNo FROM rentals WHERE tcKimlik IS NOT NULL')).fetchall()
    print('Raw Data:', rows[:5])
