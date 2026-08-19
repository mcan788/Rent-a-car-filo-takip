import urllib.request
import json

req = urllib.request.Request('https://zyronova.com/api/auth/demo-login', data=json.dumps({"requestedModule": "TOUR_TRACKING", "type": "TOUR_TRACKING"}).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req) as response:
    res = json.loads(response.read().decode())
    token = res['token']

req = urllib.request.Request('https://zyronova.com/api/agency/stats/1', headers={'Authorization': 'Bearer ' + token})
try:
    with urllib.request.urlopen(req) as response:
        stats = json.loads(response.read().decode())
        print(json.dumps(stats, indent=2))
except Exception as e:
    print("Error:", getattr(e, 'read', lambda: str(e))().decode() if hasattr(e, 'read') else str(e))
