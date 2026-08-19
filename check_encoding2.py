from app import app, db
from models import Company

with app.app_context():
    company = Company.query.first()
    t = company.contract_template
    if t:
        print(f"Stored text: {t[:200]}")
        import json
        try:
            parsed = json.loads(t)
            print(f"RU tab: {parsed.get('RU')[:100]}")
        except:
            print("Not JSON")
