import urllib.request
import json
import zipfile
import os

url = "https://api.github.com/repos/win-acme/win-acme/releases/latest"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())

download_url = None
for asset in data['assets']:
    if asset['name'].startswith('win-acme') and 'x64.trimmed.zip' in asset['name']:
        download_url = asset['browser_download_url']
        break

if download_url:
    print(f"Downloading {download_url}...")
    zip_path = "C:\\SUNUCU_PAKETI\\win-acme.zip"
    urllib.request.urlretrieve(download_url, zip_path)
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall("C:\\win-acme")
    print("Done!")
else:
    print("Could not find win-acme zip.")
