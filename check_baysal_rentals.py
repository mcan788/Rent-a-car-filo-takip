from app import app
from extensions import get_tenant_engine
from sqlalchemy.orm import sessionmaker
from models import Company, Rental

with app.app_context():
    company = Company.query.get(16)
    engine = get_tenant_engine(company.subdomain)
    Session = sessionmaker(bind=engine)
    ts = Session()
    rentals = ts.query(Rental).all()
    print(f"Company {company.name} has {len(rentals)} rentals.")
