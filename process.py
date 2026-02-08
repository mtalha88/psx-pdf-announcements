"""
Process script for GitHub Actions - scrapes announcements and pushes to HF Dataset.
"""
import pandas as pd
from datetime import datetime
from datasets import load_dataset, Dataset
from huggingface_hub import HfApi
import os
import time

from pdf_scraper import fetch_announcements
from config import HF_TOKEN, HF_DATASET_ID

def main():
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN environment variable not set")

    print(f"Loading/Initializing dataset: {HF_DATASET_ID}")
    try:
        # Try to load existing dataset
        dataset = load_dataset(HF_DATASET_ID, split="train")
        existing_df = dataset.to_pandas()
        print(f"Loaded existing dataset with {len(existing_df)} rows")
    except Exception as e:
        print(f"Dataset not found or empty ({e}), creating new one.")
        existing_df = pd.DataFrame(columns=[
            "ticker", "title", "date", "pdf_url", 
            "extracted_text", "sentiment_score", "sentiment_impact", "sentiment_signals"
        ])

    # Fetch fresh announcements
    print("Fetching new announcements...")
    new_announcements = fetch_announcements(days=3)  # Look back 3 days
    print(f"Found {len(new_announcements)} announcements")

    if not new_announcements:
        print("No new announcements found.")
        return

    # Convert to DataFrame
    new_df = pd.DataFrame(new_announcements)
    
    # Ensure all columns exist
    for col in ["extracted_text", "sentiment_score", "sentiment_impact", "sentiment_signals"]:
        if col not in new_df.columns:
            new_df[col] = "" 
            # For numeric/list columns, we might want appropriate defaults, but empty string/null is often safe for mixed
            if col == "sentiment_score": new_df[col] = 0.0
            if col == "sentiment_signals": new_df[col] = "[]" # Store as string representation or handle lists

    # Filter out duplicates
    # We use pdf_url as unique key
    current_urls = set(existing_df["pdf_url"].tolist())
    
    unique_new = []
    for _, row in new_df.iterrows():
        if row["pdf_url"] not in current_urls:
            unique_new.append(row)
    
    if not unique_new:
        print("No unique new announcements to add.")
        return
    
    print(f"Adding {len(unique_new)} new unique announcements.")
    unique_df = pd.DataFrame(unique_new)
    
    # Combine and Push
    updated_df = pd.concat([existing_df, unique_df], ignore_index=True)
    
    # Fix data types if needed (datasets can be picky)
    updated_df["sentiment_score"] = pd.to_numeric(updated_df["sentiment_score"], errors='coerce').fillna(0.0)
    updated_df["extracted_text"] = updated_df["extracted_text"].astype(str).replace("nan", "")

    print(f"Pushing updated dataset ({len(updated_df)} rows) to Hub...")
    updated_dataset = Dataset.from_pandas(updated_df)
    updated_dataset.push_to_hub(HF_DATASET_ID, token=HF_TOKEN)
    print("Push successful!")

if __name__ == "__main__":
    main()
