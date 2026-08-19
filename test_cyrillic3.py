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
    if rental and rental.sozlesmeDili == 'RU':
        raw_template = company.contract_template or ''
        metni = raw_template
        if raw_template.startswith('{'):
            try:
                import json
                parsed = json.loads(raw_template)
                metni = parsed.get('RU', raw_template)
            except:
                pass
        rental.sozlesmeMetni = metni
        ts.commit()
        print("Restored original Russian text from template.")
