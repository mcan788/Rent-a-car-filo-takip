from app import app
from extensions import get_tenant_engine
from sqlalchemy.orm import sessionmaker
from models import Company, Vehicle

with app.app_context():
    company = Company.query.get(16)
    engine = get_tenant_engine(company.subdomain)
    Session = sessionmaker(bind=engine)
    ts = Session()
    vehicles = ts.query(Vehicle).all()
    print(f"Company {company.name} has {len(vehicles)} vehicles.")
    for v in vehicles:
        print(f" - ID: {v.id}, Plaka: {v.plaka}, Marka: {v.marka}")
