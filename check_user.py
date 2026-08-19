import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import User

with app.app_context():
    u = User.query.filter_by(username='RentACarDemo').first()
    if u:
        print(f"User: {u.username}, Role: {u.role_id}")
        print(f"Permissions: {u.get_permissions()}")
    else:
        print("User not found!")
