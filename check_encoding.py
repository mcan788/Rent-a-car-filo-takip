from app import app, db
from sqlalchemy import text
from models import Company

with app.app_context():
    company = Company.query.first()
    print(f"Company contract_template: {company.contract_template[:100] if company.contract_template else 'None'}")
