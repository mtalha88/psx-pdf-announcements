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
                
                # Check if we can find a better PDF URL
                final_url = pdf_url
                if pdf_url:
                    # Extract ID
                    # Patterns: 
                    # .../download/attachment/269812-1.gif
                    # .../download/attachment/269822.pdf
                    try:
                        import re
                        match = re.search(r'/(\d+)(?:-\d+)?\.(?:gif|pdf|jpg|png)', pdf_url, re.IGNORECASE)
                        if match:
                            doc_id = match.group(1)
                            # Construct potential document URL
                            # User noticed: download/document/{id}.pdf is often the correct full file
                            candidate_pdf = f"https://dps.psx.com.pk/download/document/{doc_id}.pdf"
                            
                            # Only check if the original is NOT already a document PDF
                            # (If it's an attachment GIF/PDF, it might be a preview or old link)
                            if "/document/" not in pdf_url:
                                if verify_url_exists(candidate_pdf):
                                    final_url = candidate_pdf
                                    # Update title or log?
                                    # print(f"Upgraded {pdf_url} -> {final_url}")
                    except Exception as e:
                        print(f"URL upgrade check failed: {e}")

                # Filter by Date
                try:
                    # ... existing date logic ...
                    row_dt = datetime.strptime(date_str, "%b %d, %Y").replace(tzinfo=timezone.utc)
                    if row_dt < cutoff_date:
                        if (cutoff_date - row_dt).days > 2:
                            break 
                        continue
                except Exception:
                    pass 

                results.append({
                    "ticker": symbol,
                    "title": title,
                    "date": f"{date_str} {time_str}",
                    "pdf_url": final_url, 
                    "company": company
                })
                
        except Exception as e:
            print(f"Browser scraping error: {e}")
        finally:
            browser.close()
            
    return results

def verify_url_exists(url: str) -> bool:
    """Check if a URL exists (HEAD request)."""
    try:
        resp = requests.head(url, timeout=5)
        return resp.status_code == 200
    except:
        return False

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
