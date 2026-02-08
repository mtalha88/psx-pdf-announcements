"""
PDF Scraper - Fetches PDF announcements from PSX.
Uses PSX DPS API with fallback to Sarmaaya.
"""
import requests
from datetime import datetime, timezone, timedelta
from config import SARMAAYA_API_URL, DATA_DIR

# PSX Endpoints
PSX_API_URL = "https://dps.psx.com.pk/api/announcements"

def fetch_announcements(days: int = 7, ticker: str = None):
    """Fetch announcements from PSX API."""
    now = datetime.now(timezone.utc) + timedelta(hours=5)  # PKT
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://dps.psx.com.pk/announcements"
    }
    
    # Try PSX API first
    try:
        resp = requests.get(PSX_API_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return parse_psx_response(data, ticker, days)
    except Exception as e:
        print(f"PSX API failed: {e}, trying Sarmaaya...")
    
    # Fallback to Sarmaaya
    try:
        params = {
            "from": (now - timedelta(days=days)).strftime("%Y-%m-%d"),
            "to": now.strftime("%Y-%m-%d")
        }
        resp = requests.get(SARMAAYA_API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if not data.get("success"):
            return []
        
        return parse_sarmaaya_response(data.get("response", []), ticker)
    except Exception as e:
        print(f"Sarmaaya API failed: {e}")
        return []

def parse_psx_response(data, ticker, days):
    """Parse PSX API response."""
    processed = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    for item in data if isinstance(data, list) else data.get("data", []):
        symbol = item.get("symbol", "").strip()
        
        if ticker and symbol.upper() != ticker.upper():
            continue
        
        # Find PDF attachment
        pdf_url = None
        for att in item.get("attachments", []):
            url = att.get("url", str(att)) if isinstance(att, dict) else str(att)
            if url.lower().endswith('.pdf'):
                pdf_url = url
                break
        
        processed.append({
            "ticker": symbol,
            "title": item.get("title", item.get("announcementTitle", "")).strip(),
            "date": item.get("date", item.get("postingDate")),
            "pdf_url": pdf_url,
            "dividend": item.get("dividend"),
            "period_ended": item.get("periodEnded")
        })
    
    return processed

def parse_sarmaaya_response(results, ticker):
    """Parse Sarmaaya API response."""
    processed = []
    for item in results:
        symbol = item.get("symbol", "").strip()
        
        if ticker and symbol.upper() != ticker.upper():
            continue
        
        pdf_url = None
        for att in item.get("attachments", []):
            if str(att).lower().endswith('.pdf'):
                pdf_url = att
                break
        
        processed.append({
            "ticker": symbol,
            "title": item.get("announcementTitle", "").strip(),
            "date": item.get("postingDate"),
            "pdf_url": pdf_url,
            "dividend": item.get("dividend"),
            "period_ended": item.get("periodEnded")
        })
    
    return processed

def download_pdf(url: str) -> bytes:
    """Download PDF and return bytes."""
    if not url:
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        print(f"Download failed: {e}")
        return None

if __name__ == "__main__":
    print("Testing PDF scraper...")
    results = fetch_announcements(days=30, ticker="LUCK")
    print(f"Found {len(results)} announcements")
    for r in results[:3]:
        title = r.get('title', '')[:50] if r.get('title') else 'No title'
        print(f"  - {title}... PDF: {bool(r.get('pdf_url'))}")
