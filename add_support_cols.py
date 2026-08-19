from app import create_app
from extensions import db

app = create_app()
with app.app_context():
    try:
        db.session.execute(db.text("ALTER TABLE support_tickets ADD category VARCHAR(50) DEFAULT 'Genel Destek'"))
        print("category added")
    except Exception as e:
        print(e)
    
    try:
        db.session.execute(db.text("ALTER TABLE support_tickets ADD priority VARCHAR(20) DEFAULT 'Normal'"))
        print("priority added")
    except Exception as e:
        print(e)

    db.session.commit()
    print("Done")
