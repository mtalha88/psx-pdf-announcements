import requests

def verbose_check(url):
    try:
        print(f"Checking {url}...")
        resp = requests.head(url, timeout=10)
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print(f"Content-Length: {resp.headers.get('Content-Length')}")
    except Exception as e:
        print(f"Error: {e}")

# ID from user example: 269812
base_id = "269812"

# 1. The URL scraper found
gif_url = f"https://dps.psx.com.pk/download/attachment/{base_id}-1.gif"
verbose_check(gif_url)

# 2. The URL user suggested
pdf_url = f"https://dps.psx.com.pk/download/document/{base_id}.pdf"
verbose_check(pdf_url)

# 3. Another recent ID from my logs: 269816 (SYM)
base_id_2 = "269816"
pdf_url_2 = f"https://dps.psx.com.pk/download/document/{base_id_2}.pdf"
verbose_check(pdf_url_2)
