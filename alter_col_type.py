from sqlalchemy import text
from app import app, db
import json

with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE companies ALTER COLUMN contract_template NVARCHAR(MAX) NULL"))
        db.session.commit()
        print("Successfully altered contract_template to NVARCHAR(MAX)")
    except Exception as e:
        print(f"Error altering table: {e}")
