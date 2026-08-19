import requests
import jwt
import os

# Create a valid token
secret = 'zyronova_jwt_secret_key_7a9d8c6b2e1f4a'
token = jwt.encode({
    'username': 'RentACarDemo',
    'subdomain': 'RentACarDemo',
    'role': 'yonetici',
    'allowedModules': ['RENT_A_CAR'],
    'targetModule': 'RENT_A_CAR'
}, secret, algorithm='HS256')

session = requests.Session()
url = f"http://localhost:5001/sso-login?token={token}"

print(f"Requesting {url}")
response = session.get(url, allow_redirects=False)

print(f"Status Code: {response.status_code}")
print(f"Headers: {response.headers}")

if response.status_code == 302:
    print(f"Redirecting to: {response.headers.get('Location')}")
    redirect_url = "http://localhost:5001" + response.headers.get('Location')
    
    response2 = session.get(redirect_url)
    print(f"Second request Status Code: {response2.status_code}")
    print(f"Second request URL: {response2.url}")
    
    if "Geçersiz Şirket Adresi" in response2.text:
        print("Failed: Invalid company address")
    elif "Sisteme Giriş Yap" in response2.text or "zyronova" in response2.url.lower() or response2.url == "http://localhost:3000/":
        print("Failed: Redirected back to portal")
    else:
        print("Success! Dashboard loaded.")
else:
    print("Failed: Initial request did not redirect to dashboard.")
