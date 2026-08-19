from app import app
from models import Company

with app.app_context():
    companies = Company.query.all()
    for c in companies:
        print(f"ID: {c.id}, Name: {c.name}, Subdomain: {c.subdomain}")
