import requests
import re

url = "https://drive.google.com/uc?export=download&id=1uinIey0wuHSO86TixUYWhkOL6Uf2j152"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
session = requests.Session()
response = session.get(url, stream=True, allow_redirects=True, timeout=10)

print("Status:", response.status_code)
html = response.text
if "download" in html.lower():
    print("Found download in HTML")
    links = re.findall(r'href="(.*?confirm=.*?)"', html)
    if links:
        print("Found confirm link:", links[0])
    else:
        # Check all hrefs with /download or /uc
        links = re.findall(r'href="(.*?/download\?.*?)"', html)
        print("All download links:", links)
        links = re.findall(r'href="(.*?/uc\?.*?)"', html)
        print("All uc links:", links)
