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
            # enable_mkldnn=False to avoid OneDNN errors on some systems (Paddle 3.x issue)
            _ocr_model = PaddleOCR(use_angle_cls=True, lang='en', enable_mkldnn=False)
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
            from transformers import AutoProcessor, AutoModelForCausalLM, AutoConfig
            print("Loading Florence-2-base model...")
            # Use 'microsoft/Florence-2-base' which is lighter and faster
            model_id = 'microsoft/Florence-2-base'
            
            # Load config first to fix potential attribute errors with newer transformers
            config = AutoConfig.from_pretrained(model_id, trust_remote_code=True)
            # Fix for 'Florence2LanguageConfig' object has no attribute 'forced_bos_token_id'
            # If the attribute is missing in the class/object but present in JSON, or vice versa causing issues.
            # Usually ignoring it in kwargs might help, or explicitly setting it if model expects it.
            # But here we pass config object.
            
            _florence_model = AutoModelForCausalLM.from_pretrained(model_id, config=config, trust_remote_code=True)
            _florence_processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
            
            # Move to device if available (optional optimization, keep CPU default for broad compat)
            # _florence_model.to("cuda" if torch.cuda.is_available() else "cpu")
            _florence_model.eval()
        except Exception as e:
            print(f"Failed to load Florence-2: {e}")
            # Try fallback loading without config if first attempt failed
            try:
                 print("Retrying Florence-2 load without explicit config...")
                 from transformers import AutoModelForCausalLM, AutoProcessor
                 model_id = 'microsoft/Florence-2-base'
                 _florence_model = AutoModelForCausalLM.from_pretrained(model_id, trust_remote_code=True)
                 _florence_processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
                 _florence_model.eval()
            except Exception as e2:
                 print(f"Failed to load Florence-2 again: {e2}")
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

def _run_multimodal_ocr(image_path_or_url):
    """Run Multimodal OCR using Hugging Face Space (olmOCR-7B-0725)."""
    try:
        from gradio_client import Client, handle_file
        print("Initializing Multimodal OCR (olmOCR-7B-0725)...")
        
        # Initialize client
        client = Client("prithivMLmods/Multimodal-OCR")
        
        print(f"Sending image to OCR API...")
        result = client.predict(
            model_name="olmOCR-7B-0725",
            text="",
            image=handle_file(image_path_or_url),
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.1,
            api_name="/generate_image"
        )
        # Result is a tuple, access the first element (text)
        if isinstance(result, tuple):
             return result[0]
        return str(result)
        
    except Exception as e:
        print(f"Multimodal OCR Error: {e}")
        return None

def _run_ocr(image):
    """Run PaddleOCR on a PIL Image, fallback to Multimodal OCR, then Florence-2."""
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
    # If text is empty or very short, try Multimodal OCR
    if len(text_result.strip()) < 10:
        print("PaddleOCR result poor/empty. Trying Multimodal OCR (olmOCR-7B-0725)...")
        
        # Save temp image for Gradio Client (needs file path or URL)
        import tempfile
        import os
        
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                image.save(temp_file, format="PNG")
                temp_file_path = temp_file.name
            
            multimodal_text = _run_multimodal_ocr(temp_file_path)
            if multimodal_text:
                text_result = multimodal_text
            else:
                print("Multimodal OCR failed or returned empty.")
                raise Exception("Multimodal OCR failed") # Trigger Florence fallback

        except Exception as e:
            print(f"Multimodal OCR fallback failed: {e}")
            print("Trying Florence-2 (Local Fallback)...")
            
            # 3. Final Fallback: Florence-2
            if image:
                 florence_text = _run_florence_ocr(image)
                 if florence_text:
                     text_result = florence_text
            else:
                 print("Florence-2 skipped: Image is None")
        finally:
            # Cleanup temp file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            
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
