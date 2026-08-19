"""Debug SSO flow: check companies, users, and simulate token decode."""
import os, sys
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app
app = create_app()

with app.app_context():
    from models import User, Company
    from extensions import db
    
    print("=" * 60)
    print("ALL COMPANIES IN ZYRONOVA_MASTER:")
    print("=" * 60)
    companies = Company.query.all()
    for c in companies:
        print(f"  ID={c.id}, name={c.name}, subdomain={c.subdomain}, active={c.is_active}")
    
    print(f"\nTotal companies: {len(companies)}")
    
    print("\n" + "=" * 60)
    print("ALL USERS IN ZYRONOVA_MASTER:")
    print("=" * 60)
    users = User.query.all()
    for u in users:
        print(f"  ID={u.id}, username={u.username}, company_id={u.company_id}, role_id={u.role_id}, company_name={u.company_name}")
    
    print(f"\nTotal users: {len(users)}")
    
    # Now simulate what api_auth_login returns
    print("\n" + "=" * 60)
    print("SIMULATING API AUTH LOGIN (what token would contain):")
    print("=" * 60)
    
    # Find the user that would be used for demo/test
    demo_user = User.query.filter_by(username='RentACarDemo').first()
    if not demo_user:
        demo_user = User.query.filter_by(username='admin').first()
    
    if demo_user:
        company_subdomain = demo_user.company.subdomain if demo_user.company else demo_user.username
        print(f"  User: {demo_user.username}")
        print(f"  Company ID: {demo_user.company_id}")
        print(f"  Company: {demo_user.company}")
        if demo_user.company:
            print(f"  Company name: {demo_user.company.name}")
            print(f"  Company subdomain: {demo_user.company.subdomain}")
        print(f"  Token subdomain would be: '{company_subdomain}'")
        
        # Now check if this subdomain resolves
        resolved = Company.query.filter_by(subdomain=company_subdomain).first()
        print(f"\n  Company.query.filter_by(subdomain='{company_subdomain}').first() = {resolved}")
        if resolved:
            print(f"    -> ID={resolved.id}, name={resolved.name}, active={resolved.is_active}")
        else:
            print(f"    -> NOT FOUND! This is the root cause of SSO failure!")
    else:
        print("  No demo user found!")
