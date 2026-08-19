from app import app, db
from models import Company

with app.app_context():
    companies = Company.query.all()
    for company in companies:
        t = company.contract_template
        if t and '{' in t:
            print(f"Company {company.id} has JSON: {t[:100]}")
        else:
            print(f"Company {company.id} has plain text or none.")
