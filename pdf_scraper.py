"""
PDF Scraper - Fetches PDF/Image announcements from PSX using Playwright.
Uses PSX website directly (browser automation) with fallback to Sarmaaya.
"""
import requests
from datetime import datetime, timezone, timedelta
import time
from config import SARMAAYA_API_URL

def fetch_announcements(days: int = 7, ticker: str = None, max_items: int = None):
    """Fetch announcements from PSX website using Playwright."""
    print(f"Fetching from PSX website using Playwright (days={days}, max_items={max_items})...")
    psx_results = []
    try:
        psx_results = scrape_psx_browser(days, ticker, max_items)
    except Exception as e:
        print(f"PSX browser scrape failed: {e}")
    
    if psx_results:
        return psx_results

    print("Trying Sarmaaya fallback...")
    # Fallback to Sarmaaya (Sarmaaya API doesn't support max_items easily, just days)
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

def scrape_psx_browser(days: int, ticker: str = None, max_items: int = None):
    """Scrape PSX announcements using Playwright with Pagination."""
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
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            print(f"Scraping until date: {cutoff_date.strftime('%Y-%m-%d')}")
            
            page_num = 1
            while True:
                rows = page.query_selector_all("table tbody tr")
                print(f"Processing Page {page_num} ({len(rows)} rows)...")
                
                rows_processed_on_page = 0
                for row in rows:
                    cells = row.query_selector_all("td")
                    if len(cells) < 6:
                        continue
                    
                    # Extract Data
                    date_str = cells[0].inner_text().strip()  # "Feb 6, 2026"
                    time_str = cells[1].inner_text().strip()
                    symbol = cells[2].inner_text().strip()
                    company = cells[3].inner_text().strip()
                    title = cells[4].inner_text().strip()
                    
                    # Date Check
                    try:
                        row_dt = datetime.strptime(date_str, "%b %d, %Y").replace(tzinfo=timezone.utc)
                        # Make row_dt end of day effectively for comparison? 
                        # Actually cutoff is X days ago.
                        if row_dt < cutoff_date:
                            if (cutoff_date - row_dt).days > 2:
                                print(f"Reached date limit: {date_str}")
                                return results
                            continue # Skip old partials but keep checking logic?
                            # If sorted desc, we can return.
                            # Assuming desc sort.
                            # return results 
                    except Exception:
                        pass

                    # Filter by Ticker
                    if ticker and symbol.upper() != ticker.upper():
                        continue

                    # Attachment Link Logic
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
                            data_img = link.get_attribute("data-images")
                            if data_img:
                                # data-images can be comma-separated like "269906,269906-1.gif"
                                # Find the part that has a file extension
                                parts = [p.strip() for p in data_img.split(",")]
                                filename = next(
                                    (p for p in parts if p.lower().endswith(('.gif', '.jpg', '.jpeg', '.png', '.bmp', '.pdf'))),
                                    parts[-1]  # Fallback to last part if no extension found
                                )
                                # Logic to distinguish /image/ vs /attachment/
                                if filename.lower().endswith(('.gif', '.jpg', '.jpeg', '.png', '.bmp')):
                                    pdf_url = f"https://dps.psx.com.pk/download/image/{filename}"
                                else:
                                    pdf_url = f"https://dps.psx.com.pk/download/attachment/{filename}"
                    
                    # Smart PDF Discovery
                    final_url = pdf_url
                    if pdf_url:
                         try:
                            import re
                            match = re.search(r'/(\d+)(?:-\d+)?\.(?:gif|pdf|jpg|png)', pdf_url, re.IGNORECASE)
                            if match:
                                doc_id = match.group(1)
                                candidate_pdf = f"https://dps.psx.com.pk/download/document/{doc_id}.pdf"
                                if "/document/" not in pdf_url:
                                    if verify_url_exists(candidate_pdf):
                                        final_url = candidate_pdf
                         except Exception:
                            pass

                    results.append({
                        "ticker": symbol,
                        "title": title,
                        "date": f"{date_str} {time_str}",
                        "pdf_url": final_url, 
                        "company": company
                    })
                    rows_processed_on_page += 1
                    
                    if max_items and len(results) >= max_items:
                        print(f"Reached max_items limit: {max_items}")
                        return results
                
                # Check if we should stop (if checked all rows and none matched date? No, assuming sorted)
                
                # Pagination
                # Use .first because there might be two Next buttons (top and bottom)
                next_btn = page.locator(".form__button.next").first 
                
                # Check if disabled
                # "form__button prev disabled" - class check?
                # or just try click
                if not next_btn.is_visible() or "disabled" in (next_btn.get_attribute("class") or ""):
                    print("No more pages (Next button disabled/hidden).")
                    break
                
                print("Clicking Next page...")
                next_btn.click()
                
                # Wait for load
                time.sleep(3) # Safe wait for AJAX
                page_num += 1
                
                # Loop safety
                if page_num > 20: # Safety limit 20 pages ~ 1000 items
                    print("Safety page limit reached.")
                    break

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
