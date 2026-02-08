"""
PDF Text Extractor - Uses pdfplumber + HuggingFace TrOCR for fallback.
"""
import io
import pdfplumber
from PIL import Image

# Lazy load OCR model
_ocr_pipeline = None

def load_ocr_model():
    """Load TrOCR model from HuggingFace (free)."""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        try:
            from transformers import pipeline
            _ocr_pipeline = pipeline("image-to-text", model="microsoft/trocr-base-printed")
            print("TrOCR model loaded")
        except Exception as e:
            print(f"OCR load failed: {e}")
    return _ocr_pipeline

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber, OCR fallback for images."""
    if not pdf_bytes:
        return ""
    
    text_parts = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                # Try direct text extraction
                page_text = page.extract_text() or ""
                
                if page_text.strip():
                    text_parts.append(page_text)
                else:
                    # Fallback: OCR on page image
                    ocr_text = ocr_page_image(page)
                    if ocr_text:
                        text_parts.append(ocr_text)
    except Exception as e:
        print(f"PDF extraction error: {e}")
    
    return "\n".join(text_parts)

def ocr_page_image(page) -> str:
    """OCR a PDF page using TrOCR."""
    try:
        # Convert page to image
        img = page.to_image(resolution=150).original
        
        pipeline = load_ocr_model()
        if pipeline:
            result = pipeline(img)
            return result[0].get("generated_text", "") if result else ""
    except Exception as e:
        print(f"OCR error: {e}")
    return ""

if __name__ == "__main__":
    # Test with a sample
    from pdf_scraper import fetch_announcements, download_pdf
    
    results = fetch_announcements(days=30, ticker="LUCK")
    pdf_items = [r for r in results if r.get("pdf_url")]
    
    if pdf_items:
        print(f"Testing PDF extraction on: {pdf_items[0]['title'][:50]}...")
        pdf_bytes = download_pdf(pdf_items[0]["pdf_url"])
        text = extract_text_from_pdf(pdf_bytes)
        print(f"Extracted {len(text)} chars")
        print(text[:500] if text else "No text extracted")
