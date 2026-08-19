from app import create_app
from models import Company
from utils.notifications_daemon import check_overdue_rentals

app = create_app()
with app.app_context():
    # Force reset the overdue_alert_sent flags for 'deneme' so it sends again
    from extensions import get_tenant_session
    from models import Rental
    
    print("Resetting alert flags for 'deneme'...")
    try:
        ts = get_tenant_session('deneme', app=app)
        rentals = ts.query(Rental).filter_by(overdue_alert_sent=True).all()
        for r in rentals:
            r.overdue_alert_sent = False
        ts.commit()
        print(f"Reset {len(rentals)} rentals.")
    except Exception as e:
        print(f"Error resetting flags: {e}")
        
    print("Running overdue rentals check...")
    check_overdue_rentals(app)
    print("Done.")
