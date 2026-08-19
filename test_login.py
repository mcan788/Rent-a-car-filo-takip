import urllib.request
import json

req = urllib.request.Request('http://localhost:5000/api/auth/login', 
                             data=json.dumps({"username": "Enes_d", "password": "123"}).encode('utf-8'),
                             headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(e)
