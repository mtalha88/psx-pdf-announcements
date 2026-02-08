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
            # use_gpu argument might be deprecated/invalid in newer versions?
            # It seems so. Removing it.
            _ocr_model = PaddleOCR(use_angle_cls=True, lang='en')
        except Exception as e:
            print(f"Failed to load PaddleOCR: {e}")
            return None
    return _ocr_model

# GOT-OCR Model (Lazy Load)
_got_model = None
_got_tokenizer = None

def _get_got_model():
    global _got_model, _got_tokenizer
    if _got_model is None:
        try:
            from transformers import AutoModel, AutoTokenizer
            print("Loading GOT-OCR 2.0 model...")
            # trust_remote_code=True is essential
            _got_tokenizer = AutoTokenizer.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True)
            _got_model = AutoModel.from_pretrained('stepfun-ai/GOT-OCR2_0', trust_remote_code=True, low_cpu_mem_usage=True, use_safetensors=True)
            _got_model = _got_model.eval()
        except Exception as e:
            print(f"Failed to load GOT-OCR: {e}")
            return None, None
    return _got_model, _got_tokenizer

def _run_got_ocr(image):
    """Run GOT-OCR 2.0 on a PIL Image."""
    model, tokenizer = _get_got_model()
    if not model: return ""
    try:
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp.name)
            tmp_path = tmp.name
        
        res = model.chat(tokenizer, tmp_path, ocr_type='ocr')
        
        try: os.unlink(tmp_path) 
        except: pass
        
        return res
    except Exception as e:
        print(f"GOT-OCR Error: {e}")
        return ""

def _run_ocr(image):
    """Run PaddleOCR on a PIL Image, fallback to GOT-OCR."""
    text_result = ""
    
    # 1. Try PaddleOCR (Fast, Structured)
    ocr = _get_ocr_model()
    if ocr:
        try:
            import numpy as np
            img_np = np.array(image.convert("RGB"))
            result = ocr.ocr(img_np, cls=True)
            
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    text_lines.append(line[1][0])
            text_result = "\n".join(text_lines)
        except Exception as e:
            print(f"PaddleOCR Error: {e}")

    # 2. Fallback check
    # If text is empty or very short, try GOT-OCR
    if len(text_result.strip()) < 10:
        print("PaddleOCR result poor/empty. Trying GOT-OCR (Generative)...")
        got_text = _run_got_ocr(image)
        if got_text:
            text_result = got_text
            
    return text_result

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
