
from gradio_client import Client, handle_file
import time

def test_new_ocr(image_url):
    print(f"Testing OCR with URL: {image_url}")
    
    try:
        client = Client("prithivMLmods/Multimodal-OCR")
        
        # Test olmOCR-7B-0725
        print(f"Testing model: olmOCR-7B-0725")
        start = time.time()
        result_olm = client.predict(
            model_name="olmOCR-7B-0725",
            text="",
            image=handle_file(image_url),
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.1,
            api_name="/generate_image"
        )
        end = time.time()
        print(f"olmOCR-7B-0725 Time: {end - start:.2f}s")
        print("olmOCR-7B-0725 Result:", result_olm)

        # Test RolmOCR-7B
        print(f"\nTesting model: RolmOCR-7B")
        start = time.time()
        result_rolm = client.predict(
            model_name="RolmOCR-7B",
            text="",
            image=handle_file(image_url),
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.9,
            top_k=50,
            repetition_penalty=1.1,
            api_name="/generate_image"
        )
        end = time.time()
        print(f"RolmOCR-7B Time: {end - start:.2f}s")
        print("RolmOCR-7B Result:", result_rolm)
        
        return result_olm, result_rolm
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    # URL from test_image_ocr.py
    url = "https://dps.psx.com.pk/download/attachment/269816-1.gif"
    test_new_ocr(url)
