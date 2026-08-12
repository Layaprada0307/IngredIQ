import os
import base64
import traceback
import imghdr
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def extract_text_from_image(image: bytes) -> str:
    start_time = time.time()
    print(f"[TIMING] OCR Step Start: {start_time}")
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set in .env file")
    
    if not image:
        raise ValueError("Image data is empty")
    
    # Detect actual image type
    image_type = imghdr.what(None, h=image)
    if image_type == "jpeg" or image_type is None:
        mime_type = "image/jpeg"
    elif image_type == "png":
        mime_type = "image/png"
    elif image_type == "webp":
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"
        
    try:
        client = Groq(api_key=api_key)
        
        image_b64 = base64.b64encode(image).decode("utf-8")
        
        # Groq vision models are preview-only and rotate frequently — check console.groq.com/docs/deprecations if this breaks again.
        response = client.chat.completions.create(
            model="qwen/qwen3.6-27b",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": """This is a product label. Find ONLY the ingredients list.
Respond with ONLY a JSON object containing a single key "ingredients" with an array of ingredient name strings extracted from the label. Do not include any explanation, reasoning, or commentary — only the final list.
Resolve E-numbers/INS numbers to real names (e.g. INS 508 = Potassium Chloride).
If no ingredients list found, return: {"ingredients": []}"""
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=500
        )
        
        result = response.choices[0].message.content.strip()
        import json
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "ingredients" in parsed:
                if not parsed["ingredients"]:
                    print(f"[TIMING] OCR Step End: {time.time()} (Duration: {time.time() - start_time}s)")
                    return ""
                return ", ".join(parsed["ingredients"])
        except Exception as e:
            print(f"JSON Parsing Error: {e}")
            pass

        if "NO_INGREDIENTS_FOUND" in result:
            print(f"[TIMING] OCR Step End: {time.time()} (Duration: {time.time() - start_time}s)")
            return ""
        
        print(f"[TIMING] OCR Step End: {time.time()} (Duration: {time.time() - start_time}s)")
        return result
        
    except Exception as e:
        print(f"[TIMING] OCR Step Error: {time.time()} (Duration: {time.time() - start_time}s)")
        print(f"OCR ERROR: {str(e)}")
        # If Groq returns an error, they store error details in e.response or e.body sometimes
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Error Details: {e.response.text}")
        elif hasattr(e, 'body'):
            print(f"Error Body: {e.body}")
            
        print(traceback.format_exc())
        raise
