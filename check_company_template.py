from app import app
from models import Company

with app.app_context():
    company = Company.query.get(15)
    print(f"Company 15 template length: {len(company.contract_template) if company.contract_template else 0}")
    print(f"Content preview: {company.contract_template[:200]}")
