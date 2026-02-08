"""
PSX PDF Announcements API - Gradio App
"""
import gradio as gr
import pandas as pd
from datetime import datetime

from pdf_scraper import fetch_announcements, download_pdf
from pdf_extractor import extract_text_from_pdf
from sentiment_analyzer import analyze_sentiment
from config import ANNOUNCEMENTS_FILE

def process_announcements(ticker: str = "", days: int = 7):
    """Fetch, extract, and analyze announcements."""
    ticker = ticker.strip().upper() if ticker else None
    
    # Fetch announcements
    announcements = fetch_announcements(days=days, ticker=ticker)
    
    if not announcements:
        return {"status": "no_data", "count": 0, "announcements": []}
    
    results = []
    for ann in announcements:
        result = {
            "ticker": ann["ticker"],
            "title": ann["title"],
            "date": ann["date"],
            "pdf_url": ann.get("pdf_url"),
            "extracted_text": "",
            "sentiment": {"score": 0, "impact": "neutral", "signals": []}
        }
        
        # Extract text from PDF if available
        if ann.get("pdf_url"):
            pdf_bytes = download_pdf(ann["pdf_url"])
            if pdf_bytes:
                result["extracted_text"] = extract_text_from_pdf(pdf_bytes)
        
        # Analyze sentiment (title + extracted text)
        combined_text = f"{ann['title']} {result['extracted_text']}"
        result["sentiment"] = analyze_sentiment(combined_text)
        
        results.append(result)
    
    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv(ANNOUNCEMENTS_FILE, index=False)
    
    return {
        "status": "success",
        "count": len(results),
        "announcements": results
    }

def get_sentiment_summary(ticker: str):
    """Get sentiment summary for a ticker."""
    ticker = ticker.strip().upper()
    if not ticker:
        return {"error": "Ticker required"}
    
    result = process_announcements(ticker=ticker, days=30)
    
    if result["count"] == 0:
        return {"ticker": ticker, "status": "no_announcements"}
    
    # Aggregate sentiment
    total_score = sum(a["sentiment"]["score"] for a in result["announcements"])
    all_signals = []
    for a in result["announcements"]:
        all_signals.extend(a["sentiment"]["signals"])
    
    avg_score = total_score / result["count"]
    
    if avg_score >= 20:
        overall = "bullish"
    elif avg_score <= -20:
        overall = "bearish"
    else:
        overall = "neutral"
    
    return {
        "ticker": ticker,
        "announcement_count": result["count"],
        "total_score": total_score,
        "average_score": round(avg_score, 1),
        "overall_sentiment": overall,
        "top_signals": list(set(all_signals))[:10]
    }

# Gradio Interface
with gr.Blocks(title="PSX PDF Announcements API") as demo:
    gr.Markdown("# 📄 PSX PDF Announcements API")
    gr.Markdown("Scrape PDF announcements, extract text, analyze sentiment.")
    
    with gr.Tab("📥 Get Announcements"):
        ticker_input = gr.Textbox(label="Ticker (optional, e.g., LUCK)", placeholder="Leave empty for all")
        days_input = gr.Slider(1, 30, value=7, step=1, label="Days to look back")
        fetch_btn = gr.Button("Fetch & Process", variant="primary")
        output_json = gr.JSON(label="Results")
        
        fetch_btn.click(process_announcements, [ticker_input, days_input], output_json)
    
    with gr.Tab("📊 Sentiment Summary"):
        ticker_input2 = gr.Textbox(label="Ticker (required)", placeholder="e.g., LUCK")
        analyze_btn = gr.Button("Analyze Sentiment", variant="primary")
        sentiment_output = gr.JSON(label="Sentiment Summary")
        
        analyze_btn.click(get_sentiment_summary, ticker_input2, sentiment_output)
    
    gr.Markdown("""
    ## API Usage
    ```python
    from gradio_client import Client
    client = Client("your-space-url")
    
    # Get announcements
    result = client.predict(ticker="LUCK", days=7, api_name="/process_announcements")
    
    # Get sentiment
    sentiment = client.predict(ticker="LUCK", api_name="/get_sentiment_summary")
    ```
    """)

if __name__ == "__main__":
    demo.launch()
