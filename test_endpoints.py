import requests

endpoints = [
    "https://dps.psx.com.pk/web/api/announcements",
    "https://dps.psx.com.pk/api/announcements",
    "https://dps.psx.com.pk/data/announcements",
    "https://dps.psx.com.pk/announcements/data",
    "https://tsapi.psx.com.pk/announcements",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://dps.psx.com.pk/announcements",
    "X-Requested-With": "XMLHttpRequest"
}

for ep in endpoints:
    try:
        print(f"Testing {ep}...")
        resp = requests.get(ep, headers=headers, timeout=5)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print(f"SUCCESS! Content: {str(resp.json())[:200]}")
            break
        elif resp.status_code == 405: # Method Not Allowed, try POST
            print("Trying POST...")
            resp = requests.post(ep, headers=headers, timeout=5)
            print(f"POST Status: {resp.status_code}")
            if resp.status_code == 200:
                 print(f"SUCCESS (POST)! Content: {str(resp.json())[:200]}")
                 break
    except Exception as e:
        print(f"Error: {e}")
