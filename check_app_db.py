from app import app
from models import User, db

with app.app_context():
    user = User.query.filter_by(username='demir_enes').first()
    if not user:
        user = User.query.filter_by(username='demir_Enes').first()
        
    if user:
        print(f"User Found! Username: {user.username}, Role ID: {user.role_id}, Company ID: {user.company_id}, ID: {user.id}")
    else:
        print("User NOT found in ZYRONOVA_MASTER.User table!")
