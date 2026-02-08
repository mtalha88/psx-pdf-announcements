from pdf_scraper import fetch_announcements
import time

print("Testing fetch_announcements integration...")
start = time.time()
results = fetch_announcements(days=3)
end = time.time()

print(f"Scrape completed in {end - start:.2f} seconds.")
print(f"Found {len(results)} announcements.")

for i, res in enumerate(results[:5]):
    print(f"{i+1}. {res['ticker']} | {res['date']} | {res['title'][:30]}... | PDF: {res['pdf_url']}")

if not results:
    print("WARNING: No results found!")
