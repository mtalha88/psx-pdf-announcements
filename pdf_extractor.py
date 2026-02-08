"""
PDF/Image Text Extractor - Uses pdfplumber + HuggingFace TrOCR.
Supports both PDF documents and direct Image files (GIF, JPG, etc).
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
            import torch
            
            # Use CUDA if available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            print(f"Loading TrOCR model on {device}...")
            
            processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-printed")
            model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-printed").to(device)
            
            _ocr_pipeline = (processor, model, device)
            print("TrOCR model loaded successfully")
        except Exception as e:
            print(f"OCR load failed: {e}")
            return None
    return _ocr_pipeline

def _run_ocr(image) -> str:
    """Run OCR on a PIL Image."""
    try:
        models = load_ocr_model()
        if models:
            processor, model, device = models
            # Convert to RGB
            if image.mode != "RGB":
                image = image.convert("RGB")
                
            pixel_values = processor(images=image, return_tensors="pt").pixel_values.to(device)
            generated_ids = model.generate(pixel_values)
            generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return generated_text
    except Exception as e:
        print(f"OCR Inference error: {e}")
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
                    api = page.to_image(resolution=150)
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
