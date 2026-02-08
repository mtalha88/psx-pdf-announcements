import requests
from bs4 import BeautifulSoup
import re

url = "https://dps.psx.com.pk/announcements"
try:
    print(f"Fetching {url}...")
    resp = requests.get(url, timeout=10)
    print(f"Status Code: {resp.status_code}")
    
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for scripts that might contain data
        scripts = soup.find_all('script')
        for s in scripts:
            if s.string and ("announcements" in s.string or "api" in s.string):
                print("Found potential data script:")
                print(s.string[:200] + "...")
        
        # Look for table rows
        rows = soup.find_all('tr')
        print(f"Found {len(rows)} table rows")
        if rows:
            print("First row sample:")
            print(rows[0])
            
    # Try the API endpoint again with headers
    api_url = "https://dps.psx.com.pk/api/announcements"
    print(f"\nTesting API {api_url} with headers...")
    resp_api = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://dps.psx.com.pk/"})
    print(f"API Status: {resp_api.status_code}")
    if resp_api.status_code == 200:
        print("API Response Valid!")
        print(str(resp_api.json())[:200])
    else:
        print(f"API Response: {resp_api.text[:200]}")

except Exception as e:
    print(f"Error: {e}")
