import requests

url = "https://drive.google.com/uc?export=download&id=1uinIey0wuHSO86TixUYWhkOL6Uf2j152"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
}
session = requests.Session()
response = session.get(url, allow_redirects=True, headers=headers)

print(response.status_code)
print(response.headers)
print("COOKIES:", session.cookies.get_dict())
with open("gdrive_response.html", "w", encoding="utf-8") as f:
    f.write(response.text)
