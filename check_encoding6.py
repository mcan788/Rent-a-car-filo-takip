from app import app
from extensions import get_tenant_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from models import Company, Rental

with app.app_context():
    company = Company.query.get(15)
    engine = get_tenant_engine(company.subdomain)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT DATA_TYPE, CHARACTER_SET_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='rentals' AND COLUMN_NAME='sozlesmeMetni'"))
        for row in res:
            print(f"Tenant DB column type: {row}")
