"""
PDF Text Extractor - Uses pdfplumber + HuggingFace TrOCR for fallback.
"""
import io
import pdfplumber
from PIL import Image

# Lazy load OCR model
_ocr_pipeline = None

def load_ocr_model():
    """Load TrOCR model directly for better stability."""
    global _ocr_pipeline
    if _ocr_pipeline is None:
        try:
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
            processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
            model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed")
            _ocr_pipeline = (processor, model)
            print("TrOCR model loaded successfully")
        except Exception as e:
            print(f"OCR load failed: {e}")
            return None
    return _ocr_pipeline

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber, OCR fallback for images."""
    if not pdf_bytes:
        return ""
    
    text_parts = []
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                # Try direct text extraction first
                page_text = page.extract_text() or ""
                
                if len(page_text.strip()) > 50:  # If significant text found, use it
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
    """OCR a PDF page using TrOCR direct inference."""
    try:
        # Convert page to image
        img = page.to_image(resolution=150).original.convert("RGB")
        
        models = load_ocr_model()
        if models:
            processor, model = models
            pixel_values = processor(images=img, return_tensors="pt").pixel_values
            generated_ids = model.generate(pixel_values)
            generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return generated_text
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
