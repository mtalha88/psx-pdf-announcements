"""
Process script for GitHub Actions - scrapes announcements and pushes to HF Dataset.
"""
import pandas as pd
from datetime import datetime, timezone
from datasets import load_dataset, Dataset
import os
import time

from pdf_scraper import fetch_announcements
from config import HF_TOKEN, HF_DATASET_ID

def main():
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN environment variable not set")

    print(f"Loading/Initializing dataset: {HF_DATASET_ID}")
    existing_df = pd.DataFrame()
    last_date = None
    
    try:
        # Try to load existing dataset
        dataset = load_dataset(HF_DATASET_ID, split="train")
        existing_df = dataset.to_pandas()
        print(f"Loaded existing dataset with {len(existing_df)} rows")
        
        # Calculate last scraped date
        if not existing_df.empty and "date" in existing_df.columns:
            # Convert to datetime to find max
            # Format in DB is usually "Feb 6, 2026 4:24 PM" string
            # We need to parse it robustly
            dates = pd.to_datetime(existing_df['date'], errors='coerce', utc=True)
            last_date = dates.max()
            print(f"Latest date in dataset: {last_date}")
            
    except Exception as e:
        print(f"Dataset load error (expected if first run/empty): {e}")
        # Initialize empty schema if needed, or just let concat handle it
        pass

    # Determine Scrape Parameters
    if last_date and pd.notna(last_date):
        # Incremental Scrape
        # Calculate days gap
        now_utc = datetime.now(timezone.utc)
        diff = now_utc - last_date
        days_to_scrape = diff.days + 2 # +2 buffer for timezone/partial days
        max_items = None # Fetch all new items
        print(f"Incremental mode: Scraping last {days_to_scrape} days.")
    else:
        # Initial Scrape / Backfill
        days_to_scrape = 60 # Look back 2 months to find data
        max_items = 300     # User requested at least 300 items
        print(f"Backfill mode: Scraping up to {max_items} items (approx {days_to_scrape} days).")

    # Fetch announcements
    try:
        new_results = fetch_announcements(days=days_to_scrape, max_items=max_items)
        print(f"Fetched {len(new_results)} announcements.")
    except Exception as e:
        print(f"Scraping failed: {e}")
        return

    if not new_results:
        print("No new announcements found.")
        return

    # Convert to DataFrame
    new_df = pd.DataFrame(new_results)
    
    # Ensure all columns exist
    # (Columns expected by App schema)
    for col in ["extracted_text", "sentiment_score", "sentiment_impact", "sentiment_signals"]:
        if col not in new_df.columns:
            new_df[col] = "" 
            if col == "sentiment_score": new_df[col] = 0.0
            if col == "sentiment_signals": new_df[col] = "[]" 

    # Filter out duplicates
    if not existing_df.empty:
        # Use simple URL check if available, or composite key?
        # pdf_url is good
        current_urls = set(existing_df.get("pdf_url", []).tolist())
        # Also check title+date collision?
        
        unique_new = []
        for _, row in new_df.iterrows():
            if row["pdf_url"] and row["pdf_url"] not in current_urls:
                unique_new.append(row)
            elif not row["pdf_url"]:
                # If no URL, check title+date
                # Simplified check for now: only allow unique pdf_url if present
                pass
        
        if not unique_new:
            print("No unique new announcements to add (duplicates).")
            return
        
        print(f"Adding {len(unique_new)} new unique announcements.")
        new_df = pd.DataFrame(unique_new)
    
    # Combine and Push
    if not existing_df.empty:
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    # Fix data types
    # Ensure date is string (as originally scraped)
    updated_df["sentiment_score"] = pd.to_numeric(updated_df["sentiment_score"], errors='coerce').fillna(0.0)
    updated_df["extracted_text"] = updated_df["extracted_text"].astype(str).replace("nan", "")
    updated_df["date"] = updated_df["date"].astype(str)

    print(f"Pushing updated dataset ({len(updated_df)} rows) to Hub...")
    try:
        updated_dataset = Dataset.from_pandas(updated_df)
        updated_dataset.push_to_hub(HF_DATASET_ID, token=HF_TOKEN)
        print("Push successful!")
    except Exception as e:
        print(f"Push failed: {e}")

if __name__ == "__main__":
    main()
