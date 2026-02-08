"""
Process script for GitHub Actions - scrapes and processes announcements.
"""
import pandas as pd
from pathlib import Path

from pdf_scraper import fetch_announcements, download_pdf
from pdf_extractor import extract_text_from_pdf
from sentiment_analyzer import analyze_sentiment

def main():
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    results = fetch_announcements(days=7)
    print(f"Found {len(results)} announcements")
    
    processed = []
    for ann in results[:20]:  # Limit to 20 for speed
        text = ""
        if ann.get("pdf_url"):
            print(f"  Processing: {ann['title'][:40]}...")
            pdf_bytes = download_pdf(ann["pdf_url"])
            if pdf_bytes:
                text = extract_text_from_pdf(pdf_bytes)
        
        combined = f"{ann['title']} {text}"
        sentiment = analyze_sentiment(combined)
        
        processed.append({
            **ann,
            "extracted_text": text[:500] if text else "",
            "sentiment_score": sentiment["score"],
            "sentiment_impact": sentiment["impact"],
            "sentiment_signals": ", ".join(sentiment["signals"])
        })
    
    if processed:
        df = pd.DataFrame(processed)
        df.to_csv("data/announcements.csv", index=False)
        print(f"Saved {len(processed)} announcements to data/announcements.csv")
    else:
        print("No announcements to process")

if __name__ == "__main__":
    main()
