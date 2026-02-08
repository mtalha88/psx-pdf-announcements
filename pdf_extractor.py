"""
PDF/Image Text Extractor - Uses pdfplumber + HuggingFace TrOCR.
Supports both PDF documents and direct Image files (GIF, JPG, etc).
"""
import io
import pdfplumber
from PIL import Image

# Lazy load OCR model
# OCR Model (Lazy Load)
_ocr_model = None

def _get_ocr_model():
    global _ocr_model
    if _ocr_model is None:
        try:
            from paddleocr import PaddleOCR
            print("Loading PaddleOCR model...")
            # utilize CPU for Spaces (unless GPU available)
            # lang='en' covers English and numbers
            _ocr_model = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False, show_log=False)
        except Exception as e:
            print(f"Failed to load PaddleOCR: {e}")
            return None
    return _ocr_model

def _run_ocr(image):
    """Run PaddleOCR on a PIL Image."""
    ocr = _get_ocr_model()
    if not ocr:
        return ""
    
    try:
        import numpy as np
        # Convert PIL to Numpy (RGB)
        img_np = np.array(image.convert("RGB"))
        
        # Run OCR
        result = ocr.ocr(img_np, cls=True)
        
        # Parse results
        # Result structure: [[[[x1,y1],[x2,y2]...], ("text", conf)], ...]
        text_lines = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                text_lines.append(text)
        
        return "\n".join(text_lines)
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF or Image file bytes."""
    if not file_bytes:
        return ""
    
    # Detect if PDF
    if file_bytes.startswith(b"%PDF"):
        return _extract_from_pdf_bytes(file_bytes)
    else:
        # Assume Image
        return _extract_from_image_bytes(file_bytes)

def _extract_from_image_bytes(img_bytes: bytes) -> str:
    """Extract text from image bytes."""
    try:
        image = Image.open(io.BytesIO(img_bytes))
        print("Detected Image file, running OCR...")
        return _run_ocr(image)
    except Exception as e:
        print(f"Image extraction error: {e}")
        return ""

def _extract_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes."""
    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                # Try direct text extraction first
                page_text = page.extract_text() or ""
                
                if len(page_text.strip()) > 50:
                    text_parts.append(page_text)
                else:
                    # Fallback: OCR on page image
                    # pdfplumber to_image returns a PageImage, .original gives PIL Image
                    # Higher resolution (300 DPI) for better OCR accuracy
                    api = page.to_image(resolution=300)
                    ocr_text = _run_ocr(api.original)
                    if ocr_text:
                        text_parts.append(ocr_text)
    except Exception as e:
        print(f"PDF extraction error: {e}")
    
    return "\n".join(text_parts)

if __name__ == "__main__":
    # Test
    # Mocking file bytes would be needed
    print("PDF Extractor Module with Image Support")
