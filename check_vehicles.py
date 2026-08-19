from app import app
from extensions import get_tenant_engine
from sqlalchemy.orm import sessionmaker
from models import Company, Vehicle

with app.app_context():
    company = Company.query.get(15)
    engine = get_tenant_engine(company.subdomain)
    Session = sessionmaker(bind=engine)
    ts = Session()
    vehicles = ts.query(Vehicle).all()
    print(f"Company {company.name} has {len(vehicles)} vehicles.")
    for v in vehicles[:5]:
        print(f" - {v.id}: {v.plaka} {v.marka} {v.model}")
