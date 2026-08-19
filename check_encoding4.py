from app import app, db
from models import Company

with app.app_context():
    company = Company.query.get(15)
    t = company.contract_template
    import json
    try:
        parsed = json.loads(t)
        print(f"RU tab: {parsed.get('RU')[:100]}")
    except Exception as e:
        print(f"Error parsing JSON: {e}")
