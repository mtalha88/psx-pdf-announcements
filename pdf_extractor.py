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

# Florence-2 Model (Lazy Load)
_florence_model = None
_florence_processor = None

def _get_florence_model():
    global _florence_model, _florence_processor
    if _florence_model is None:
        try:
            from transformers import AutoProcessor, AutoModelForCausalLM
            print("Loading Florence-2-base model...")
            # Use 'microsoft/Florence-2-base' which is lighter and faster
            model_id = 'microsoft/Florence-2-base'
            _florence_model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
            _florence_processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
            
            # Move to device if available (optional optimization, keep CPU default for broad compat)
            # _florence_model.to("cuda" if torch.cuda.is_available() else "cpu")
            _florence_model.eval()
        except Exception as e:
            print(f"Failed to load Florence-2: {e}")
            return None, None
    return _florence_model, _florence_processor

def _run_florence_ocr(image):
    """Run Florence-2 OCR on a PIL Image."""
    model, processor = _get_florence_model()
    if not model: return ""
    try:
        # Prompt for OCR
        prompt = "<OCR>"
        
        inputs = processor(text=prompt, images=image, return_tensors="pt")
        
        # Move inputs to same device as model
        # inputs = {k: v.to(model.device) for k, v in inputs.items()}
        
        generated_ids = model.generate(
            input_ids=inputs["input_ids"],
            pixel_values=inputs["pixel_values"],
            max_new_tokens=1024,
            do_sample=False,
            num_beams=3,
        )
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
        parsed_answer = processor.post_process_generation(generated_text, task=prompt, image_size=(image.width, image.height))
        
        return parsed_answer.get("<OCR>", "")
    except Exception as e:
        print(f"Florence-2 Error: {e}")
        import traceback
        traceback.print_exc()
        return ""

def _run_ocr(image):
    """Run PaddleOCR on a PIL Image, fallback to Florence-2."""
    text_result = ""
    
    # 1. Try PaddleOCR (Fast, Structured)
    ocr = _get_ocr_model()
    if ocr:
        try:
            import numpy as np
            img_np = np.array(image.convert("RGB"))
            # cls argument caused error. Removing it. Use init param use_angle_cls=True logic.
            result = ocr.ocr(img_np) 
            
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    text_lines.append(line[1][0])
            text_result = "\n".join(text_lines)
        except Exception as e:
            print(f"PaddleOCR Error: {e}")

    # 2. Fallback check
    # If text is empty or very short, try Florence-2
    if len(text_result.strip()) < 10:
        print("PaddleOCR result poor/empty. Trying Florence-2 (Generative/Multimodal)...")
        # Ensure image is valid
        if image:
             florence_text = _run_florence_ocr(image)
             if florence_text:
                 text_result = florence_text
        else:
             print("Florence-2 skipped: Image is None")
            
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
