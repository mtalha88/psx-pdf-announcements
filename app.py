"""
PSX PDF Announcements API - Gradio App with Dataset Integration
"""
import gradio as gr
import pandas as pd
from datetime import datetime
from datasets import load_dataset, Dataset
import os

from pdf_scraper import download_pdf
from pdf_extractor import extract_text_from_pdf
from sentiment_analyzer import analyze_sentiment
from config import HF_DATASET_ID, HF_TOKEN

def load_data():
    try:
        dataset = load_dataset(HF_DATASET_ID, split="train", token=HF_TOKEN)
        return dataset.to_pandas()
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return pd.DataFrame()

def process_announcements(ticker: str = "", days: int = 7):
    """Fetch from dataset, extract text if missing, and update."""
    ticker = ticker.strip().upper() if ticker else None
    
    # Reload dataset to get latest
    df = load_data()
    if df.empty:
        return {"status": "no_data", "count": 0, "announcements": []}
    
    # Filter by date and ticker
    # (Simplified filtering logic for example)
    # TODO: Implement robust date filtering
    
    filtered_df = df.copy()
    if ticker:
        filtered_df = filtered_df[filtered_df["ticker"] == ticker]
    
    # Sort by date desc
    filtered_df = filtered_df.sort_values(by="date", ascending=False).head(20) # Limit to 20
    
    updates_made = False
    results = []
    
    for index, row in filtered_df.iterrows():
        result = row.to_dict()
        
        # Check if text is missing
        text = str(row.get("extracted_text", ""))
        if (not text or text == "nan") and row.get("pdf_url"):
            print(f"Running OCR for {row['ticker']} - {row['date']}")
            try:
                pdf_bytes = download_pdf(row["pdf_url"])
                if pdf_bytes:
                    extracted = extract_text_from_pdf(pdf_bytes)
                    if extracted:
                        # Analyze sentiment
                        combined = f"{row['title']} {extracted}"
                        sentiment = analyze_sentiment(combined)
                        
                        # Update result
                        result["extracted_text"] = extracted
                        result["sentiment_score"] = sentiment["score"]
                        result["sentiment_impact"] = sentiment["impact"]
                        result["sentiment_signals"] = str(sentiment["signals"])
                        
                        # Update DataFrame
                        df.at[index, "extracted_text"] = extracted
                        df.at[index, "sentiment_score"] = sentiment["score"]
                        df.at[index, "sentiment_impact"] = sentiment["impact"]
                        df.at[index, "sentiment_signals"] = str(sentiment["signals"])
                        updates_made = True
            except Exception as e:
                print(f"Error processing {row['pdf_url']}: {e}")
        
        results.append(result)

    # If we updated any rows (performed OCR), push back to Hub
    if updates_made:
        print("Pushing updated OCR results to Hub...")
        try:
            updated_dataset = Dataset.from_pandas(df)
            updated_dataset.push_to_hub(HF_DATASET_ID, token=HF_TOKEN)
            print("Dataset updated successfully.")
        except Exception as e:
            print(f"Failed to push updates: {e}")

    return {
        "status": "success",
        "count": len(results),
        "announcements": results
    }

def get_sentiment_summary(ticker: str):
    # Reuse process_announcements logic but for summary
    result = process_announcements(ticker=ticker, days=30)
    # ... (existing summary logic) ...
    return {"message": "Summary logic to be implemented based on new structure"}

# Gradio Interface
with gr.Blocks(title="PSX PDF Announcements API") as demo:
    gr.Markdown(f"# 📄 PSX PDF Announcements API (Dataset: {HF_DATASET_ID})")
    
    with gr.Tab("📥 Get Announcements"):
        ticker_input = gr.Textbox(label="Ticker (optional)", placeholder="Leave empty for all")
        days_input = gr.Slider(1, 30, value=7, label="Days")
        fetch_btn = gr.Button("Fetch & Process", variant="primary")
        output_json = gr.JSON(label="Results")
        
        fetch_btn.click(process_announcements, [ticker_input, days_input], output_json)

if __name__ == "__main__":
    demo.launch()
