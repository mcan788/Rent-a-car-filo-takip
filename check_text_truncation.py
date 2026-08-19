from app import app
from extensions import get_tenant_engine
from sqlalchemy.orm import sessionmaker
from models import Company, Rental

with app.app_context():
    company = Company.query.get(15)
    engine = get_tenant_engine(company.subdomain)
    Session = sessionmaker(bind=engine)
    ts = Session()
    rental = ts.query(Rental).order_by(Rental.id.desc()).first()
    if rental:
        print(f"Rental ID: {rental.id}")
        print(f"sozlesmeMetni length: {len(rental.sozlesmeMetni) if rental.sozlesmeMetni else 0}")
        print(f"sozlesmeMetni content: {rental.sozlesmeMetni}")
