import os
import time
import traceback
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def extract_text_from_image(image: bytes) -> str:
    start_time = time.time()
    print(f"[TIMING] OCR Step Start: {start_time}")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in .env file")
    
    if not image:
        raise ValueError("Image data is empty")
    
    client = genai.Client(api_key=api_key)
    
    for attempt in range(2):
        try:
            # We're passing the raw bytes using Part.from_bytes
            # The API can infer MIME type, or we can provide it explicitly
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=[
                    types.Part.from_bytes(
                        data=image,
                        mime_type='image/jpeg',
                    ),
                    """This is a product label. Find ONLY the ingredients list (usually starts with 'Ingredients:'). 
Return ONLY the ingredient names as a plain comma-separated list on a single line. 
Do NOT include any reasoning, explanation, thinking, or commentary in the final output. 
Do NOT use phrases like 'I see', 'Let me', 'Wait', or numbered steps.
Maximum 30 ingredients.
Ignore nutritional table, directions, warnings.
Resolve E-numbers/INS numbers to real names (e.g. INS 508 = Potassium Chloride).
If the text is too blurry or illegible to read, return exactly: ILLEGIBLE_IMAGE
If the label is in another language, translate the ingredients to English.
If no ingredients list found, return exactly: NO_INGREDIENTS_FOUND
Output ONLY the comma-separated list. Nothing else."""
                ]
            )
            
            result = response.text
            if result:
                result = result.strip()
            else:
                result = ""
            
            if "NO_INGREDIENTS_FOUND" in result or "ILLEGIBLE_IMAGE" in result:
                print(f"[TIMING] OCR Step End: {time.time()} (Duration: {time.time() - start_time}s)")
                return ""
            
            print(f"[TIMING] OCR Step End: {time.time()} (Duration: {time.time() - start_time}s)")
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
                if attempt == 0:
                    print("Rate limit reached, retrying in 2.5s...")
                    time.sleep(2.5)
                    continue
                else:
                    msg = "Rate limit reached. Please try again in a moment."
                    print(msg)
                    raise RuntimeError(msg)
            else:
                print(f"[TIMING] OCR Step Error: {time.time()} (Duration: {time.time() - start_time}s)")
                print(f"OCR ERROR: {str(e)}")
                print(traceback.format_exc())
                raise
