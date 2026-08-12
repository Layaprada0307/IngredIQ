import sys
import os
import time

# Ensure we're in the right directory
sys.path.append(r"D:\projects\IngredIQ-version1")

from ocr import extract_text_from_image
from analyzer import analyze_ingredients

images = [
    r"D:\projects\IngredIQ\IngredIQ\gheedemo.jpeg",
    r"D:\projects\IngredIQ\IngredIQ\lakshman_rekha.jpg",
    r"D:\projects\IngredIQ\IngredIQ\perfume.jpg",
    r"D:\projects\IngredIQ\IngredIQ\tata_salt_2mb.jpg"
]

for img_path in images:
    print(f"==================================================")
    print(f"Testing image: {os.path.basename(img_path)}")
    try:
        with open(img_path, "rb") as f:
            file_bytes = f.read()
        print(f"File size: {len(file_bytes)} bytes")
        
        print("Running OCR...")
        start_time = time.time()
        raw_ocr = extract_text_from_image(file_bytes)
        print(f"RAW OCR OUTPUT:\n{raw_ocr}\n")
        print(f"OCR Duration: {time.time() - start_time:.2f}s")
        
        if "NO_INGREDIENTS_FOUND" in raw_ocr or "ILLEGIBLE_IMAGE" in raw_ocr:
            print(f"Edge case triggered in OCR: {raw_ocr}")
            continue
            
        print("Parsing to list...")
        from parser import extract_ingredients
        ingredients_list = extract_ingredients(raw_ocr)
        print(f"PARSED LIST: {ingredients_list}\n")
        
        print("Running Analyzer...")
        analysis = analyze_ingredients(ingredients_list)
        print("ANALYSIS RESULTS:")
        for item in analysis:
            print(f" - {item.get('name')}: {item.get('risk')} ({item.get('category')})")
            
        print("\nCalculating Score...")
        from scoring import score_ingredients
        score = score_ingredients(analysis)
        print(f"SCORE: {score.get('score')}/10 (Grade {score.get('grade')}) - {score.get('summary')}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
print("==================================================")
