from playwright.sync_api import sync_playwright
import time

def scrape_psx():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://dps.psx.com.pk/announcements/companies"
        print(f"Navigating to {url}...")
        page.goto(url)
        
        # Wait for table to load
        try:
            print("Waiting for table rows...")
            page.wait_for_selector("table tbody tr", timeout=10000)
            
            # Print headers
            headers = page.query_selector_all("table thread th")
            if headers:
                print("Headers:", [h.inner_text() for h in headers])

            # Extract data
            rows = page.query_selector_all("table tbody tr")
            print(f"Found {len(rows)} announcements.")
            
            if rows:
                print("First row inspection:")
                cells = rows[0].query_selector_all("td")
                print(f"Cell 5 (Attachment) HTML: {cells[5].inner_html()}")
                
                # Check for link
                link = cells[5].query_selector("a")
        # Test Page 2 directly
        url_p2 = "https://dps.psx.com.pk/announcements/companies?page=2"
        print(f"Navigating to {url_p2}...")
        page.goto(url_p2)
        try:
            page.wait_for_selector("table tbody tr", timeout=10000)
            rows_p2 = page.query_selector_all("table tbody tr")
            print(f"Page 2 found {len(rows_p2)} rows.")
            if len(rows_p2) > 0:
                print(f"Page 2 First Row: {rows_p2[0].inner_text()[:50]}...")
        except Exception as e:
            print(f"Page 2 failed: {e}")
                cells = row.query_selector_all("td")
                if len(cells) > 0:
                    symbol = cells[0].inner_text()
                    # Title is usually in the second cell, often a link
                    title_cell = cells[1]
                    title = title_cell.inner_text()
                    
                    # Look for link
                    link = title_cell.query_selector("a")
                    pdf_url = link.get_attribute("href") if link else "No link"
                    
                    date = cells[2].inner_text() if len(cells) > 2 else ""
                    print(f"{i+1}. {symbol} | {date} | {title[:30]}... | PDF: {pdf_url}")
            
        except Exception as e:
            print(f"Error waiting for content: {e}")
            # Capture content to see what's wrong
            # print(page.content()[:500])
        
        browser.close()

if __name__ == "__main__":
    scrape_psx()
