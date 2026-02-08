# PSX PDF Announcements API

Public HuggingFace Space that scrapes PSX PDF announcements, extracts text, and provides sentiment analysis.

## Features
- 📄 Scrapes PDF announcements from PSX
- 🔍 Extracts text using pdfplumber + TrOCR OCR
- 📊 Sentiment analysis with keyword scoring
- 🔌 REST API for integration

## API Endpoints

### Get Announcements
```python
from gradio_client import Client
client = Client("rafaytalha23/psx-pdf-announcements")

result = client.predict(
    ticker="LUCK",  # Optional, empty for all
    days=7,
    api_name="/process_announcements"
)
```

### Get Sentiment Summary
```python
sentiment = client.predict(
    ticker="LUCK",
    api_name="/get_sentiment_summary"
)
```

## Response Format
```json
{
  "ticker": "LUCK",
  "title": "Final Cash Dividend",
  "date": "2026-02-08",
  "extracted_text": "The Board of Directors...",
  "sentiment": {
    "score": 25,
    "impact": "strong_bullish",
    "signals": ["Final Dividend"]
  }
}
```
