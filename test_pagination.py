from playwright.sync_api import sync_playwright
import time

def test_pagination():
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Scrape Page 1
        url_p1 = "https://dps.psx.com.pk/announcements/companies"
        print(f"Navigating to Page 1: {url_p1}")
        page.goto(url_p1)
        page.wait_for_selector("table tbody tr", timeout=20000)
        rows_p1 = page.query_selector_all("table tbody tr")
        print(f"Page 1 Rows: {len(rows_p1)}")
        first_row_p1 = rows_p1[0].inner_text().split("\t")[0] if rows_p1 else "None"
        print(f"Page 1 First Date/Row: {rows_p1[0].inner_text()[:30] if rows_p1 else 'None'}")

        # 2. Inspect candidates
        try:
            print("Searching for 'Next' candidates...")
            candidates = page.get_by_role("link").all()
            for i, link in enumerate(candidates):
                txt = link.inner_text()
                if "Next" in txt or ">" in txt or "›" in txt:
                    if "Capital" not in txt:
                        print(f"Candidate {i}: '{txt}'")
                        print(f"  Class: {link.get_attribute('class')}")
                        print(f"  Href: {link.get_attribute('href')}")
                        # print(f"  HTML: {link.evaluate('el => el.outerHTML')}")

            # Inspect "Showing" container
            showing = page.get_by_text("Showing 1 to 50")
            if showing.count() > 0:
                print("Found 'Showing' text element.")
                parent_html = showing.first.evaluate("el => el.parentElement.parentElement.outerHTML")
                print(f"Parent Container HTML (first 500 chars): {parent_html[:500]}")
            
        except Exception as e:
            print(f"Inspection failed: {e}")
        
        browser.close()

if __name__ == "__main__":
    test_pagination()
