import requests
import json

url = "http://localhost:5001/api/auth/login?username=RentACarDemo&password=123"
print(f"Requesting {url}")
try:
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
