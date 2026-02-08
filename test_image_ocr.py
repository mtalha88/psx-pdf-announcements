from pdf_scraper import download_pdf
from pdf_extractor import extract_text_from_pdf
import time

url = "https://dps.psx.com.pk/download/attachment/269816-1.gif"
print(f"Downloading {url}...")
file_bytes = download_pdf(url)

if file_bytes:
    print(f"Downloaded {len(file_bytes)} bytes.")
    print("Testing extraction (this might take time to load models)...")
    start = time.time()
    text = extract_text_from_pdf(file_bytes)
    end = time.time()
    
    print(f"Extraction took {end - start:.2f} seconds.")
    print(f"Extracted Text: {text[:200]}...")
else:
    print("Download failed.")
