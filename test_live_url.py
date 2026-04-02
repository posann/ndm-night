import requests
from urllib.parse import urlparse, unquote

url = "https://drive.google.com/file/d/1uinIey0wuHSO86TixUYWhkOL6Uf2j152/view?usp=drive_link"

# Conversion logic
import re
patterns = [
    r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)',
    r'drive\.google\.com/open\?id=([a-zA-Z0-9_-]+)',
    r'docs\.google\.com/uc\?id=([a-zA-Z0-9_-]+)',
    r'drive\.google\.com/uc\?id=([a-zA-Z0-9_-]+)'
]
for p in patterns:
    match = re.search(p, url)
    if match:
        file_id = match.group(1)
        url = f"https://drive.google.com/uc?export=download&id={file_id}"
        break

print(f"Converted URL: {url}")

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
session = requests.Session()
response = session.get(url, stream=True, allow_redirects=True, timeout=10)

confirm_token = None
for key, value in response.cookies.items():
    if key.startswith('download_warning'):
        confirm_token = value
        break

if confirm_token:
    print(f"Found confirm token! {confirm_token}")
    separator = "&" if "?" in url else "?"
    url += f"{separator}confirm={confirm_token}"
    response = session.get(url, stream=True, allow_redirects=True, timeout=10)

print("Status:", response.status_code)
print("Headers:", response.headers)

cd = response.headers.get('content-disposition', '')
print("CD:", cd)
