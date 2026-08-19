from sqlalchemy import text
from app import app, db
import json

with app.app_context():
    res = db.session.execute(text("SELECT DATA_TYPE, CHARACTER_SET_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='companies' AND COLUMN_NAME='contract_template'"))
    for row in res:
        print(f"Master DB column type: {row}")
