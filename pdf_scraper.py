"""
PDF Scraper - Fetches PDF/Image announcements from PSX using Playwright.
Uses PSX website directly (browser automation) with fallback to Sarmaaya.
"""
import requests
from datetime import datetime, timezone, timedelta
import time
from config import SARMAAYA_API_URL

def fetch_announcements(days: int = 7, ticker: str = None):
    """Fetch announcements from PSX website using Playwright."""
    print("Fetching from PSX website using Playwright...")
    psx_results = []
    try:
        psx_results = scrape_psx_browser(days, ticker)
    except Exception as e:
        print(f"PSX browser scrape failed: {e}")
    
    if psx_results:
        return psx_results

    print("Trying Sarmaaya fallback...")
    # Fallback to Sarmaaya
    try:
        now = datetime.now(timezone.utc) + timedelta(hours=5)  # PKT
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://dps.psx.com.pk/"
        }
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

def scrape_psx_browser(days: int, ticker: str = None):
    """Scrape PSX announcements using Playwright."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Skipping browser scrape.")
        return []

    results = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to Companies Announcements
        url = "https://dps.psx.com.pk/announcements/companies"
        print(f"Navigating to {url}...")
        page.goto(url)
        
        try:
            # Wait for table
            page.wait_for_selector("table tbody tr", timeout=20000)
            
            # Select relevant rows
            # Note: Pagination is not handled here (usually unnecessary for recent days unless high volume)
            rows = page.query_selector_all("table tbody tr")
            print(f"Found {len(rows)} rows on page.")
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) < 6:
                    continue
                
                # Extract Cells
                date_str = cells[0].inner_text().strip()  # "Feb 6, 2026"
                time_str = cells[1].inner_text().strip()  # "4:24 PM"
                symbol = cells[2].inner_text().strip()    # "SYM"
                company = cells[3].inner_text().strip()   # "Symmetry Group Limited"
                title = cells[4].inner_text().strip()     # "Disclosure..."
                
                # Attachment Link logic
                pdf_url = None
                att_cell = cells[5]
                link = att_cell.query_selector("a")
                
                if link:
                    href = link.get_attribute("href")
                    if href and not href.startswith("javascript"):
                        if href.startswith("/"):
                            pdf_url = f"https://dps.psx.com.pk{href}"
                        else:
                            pdf_url = href
                    else:
                        # Check data-images for JS links
                        data_img = link.get_attribute("data-images")
                        if data_img:
                            # Construct URL for image/pdf
                            # Usually format: /download/attachment/{filename}
                            # Handling simple case:
                            filename = data_img.split(",")[0].strip() if "," in data_img else data_img
                            pdf_url = f"https://dps.psx.com.pk/download/attachment/{filename}"

                # Filter by Ticker
                if ticker and symbol.upper() != ticker.upper():
                    continue
                
                # Filter by Date
                try:
                    # Parse "Feb 6, 2026"
                    row_dt = datetime.strptime(date_str, "%b %d, %Y").replace(tzinfo=timezone.utc)
                    if row_dt < cutoff_date:
                        # Assuming rows are sorted desc, we can break?
                        # Probably safer to continue checking a bit more
                        if (cutoff_date - row_dt).days > 2:
                            break 
                        continue
                except Exception:
                    pass # Date parsing error, include it to be safe or skip?

                results.append({
                    "ticker": symbol,
                    "title": title,
                    "date": f"{date_str} {time_str}",
                    "pdf_url": pdf_url, 
                    "company": company
                })
                
        except Exception as e:
            print(f"Browser scraping error: {e}")
        finally:
            browser.close()
            
    return results

def parse_sarmaaya_response(results, ticker):
    """Parse Sarmaaya API response."""
    processed = []
    for item in results:
        symbol = item.get("symbol", "").strip()
        
        if ticker and symbol.upper() != ticker.upper():
            continue
        
        pdf_url = None
        for att in item.get("attachments", []):
            attr_str = str(att)
            if attr_str.lower().endswith('.pdf') or attr_str.lower().endswith('.gif') or attr_str.lower().endswith('.jpg'):
                 # Ensure full URL if simple filename
                 if attr_str.startswith("http"):
                     pdf_url = attr_str
                 else:
                     # Sarmaaya usually returns full URLs but sometimes need verify
                     pdf_url = attr_str
                 break
        
        processed.append({
            "ticker": symbol,
            "title": item.get("announcementTitle", "").strip(),
            "date": item.get("postingDate"),
            "pdf_url": pdf_url,
            "period_ended": item.get("periodEnded")
        })
    
    return processed

def download_pdf(url: str) -> bytes:
    """Download PDF or Image and return bytes."""
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
