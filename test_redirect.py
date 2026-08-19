import requests
import jwt

token = jwt.encode({'subdomain': 'RentACarDemo', 'role': 'yonetici'}, 'zyronova_jwt_secret_key_7a9d8c6b2e1f4a', algorithm='HS256')
url = f"http://127.0.0.1:5001/sso-login?token={token}"

try:
    response = requests.get(url, allow_redirects=False)
    print(f"Initial request to: {url}")
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {response.headers}")
    if response.is_redirect:
        print(f"Redirects to: {response.headers.get('Location')}")
except Exception as e:
    print(f"Error: {e}")
