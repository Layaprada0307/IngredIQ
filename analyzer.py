import os
import json
import traceback
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def analyze_ingredients(ingredients: list[str]) -> list[dict]:
    if not ingredients:
        raise ValueError("Ingredient list is empty.")
    
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return _analyze_with_database(ingredients)
    
    try:
        client = Groq(api_key=api_key)
        ingredients_text = ", ".join(ingredients)
        
        prompt = f"""You are a food safety expert.
Analyze these ingredients: {ingredients_text}

Return a JSON array. Each object must have:
- name: ingredient name (string)
- classification: exactly one of "safe", "moderate", or "harmful" (string)
- category: type like sweetener, preservative, fat, mineral, vitamin, color, flavoring, emulsifier, dairy, grain, spice (string)
- notes: one sentence about health effects (string)

Classification rules:
- safe: natural ingredients, vitamins, minerals, spices
- moderate: refined/processed, some additives
- harmful: carcinogens, banned substances, artificial colors, TBHQ, BHA, BHT, sodium benzoate, aspartame

Example output format:
[
  {{"name": "Sugar", "classification": "harmful", "category": "sweetener", "notes": "High glycemic index linked to obesity."}},
  {{"name": "Salt", "classification": "moderate", "category": "mineral", "notes": "Essential mineral but harmful in excess."}}
]

Return ONLY the JSON array. No explanation. No markdown."""

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=2000,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean markdown if present
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        # Find JSON array in response
        start = result_text.find('[')
        end = result_text.rfind(']') + 1
        if start != -1 and end > start:
            result_text = result_text[start:end]
        
        analyzed = json.loads(result_text)
        
        # Validate each item
        valid_results = []
        for item in analyzed:
            if isinstance(item, dict):
                valid_results.append({
                    "name": str(item.get("name", "Unknown")),
                    "classification": str(item.get("classification", "unknown")).lower(),
                    "category": str(item.get("category", "uncategorised")),
                    "notes": str(item.get("notes", "No information available."))
                })
        
        return valid_results if valid_results else _analyze_with_database(ingredients)
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {str(e)}")
        print(f"Raw response: {result_text}")
        return _analyze_with_database(ingredients)
    except Exception as e:
        print(f"AI Analysis ERROR: {str(e)}")
        print(traceback.format_exc())
        return _analyze_with_database(ingredients)


def _analyze_with_database(ingredients: list[str]) -> list[dict]:
    import os
    data_path = os.path.join(
        os.path.dirname(__file__), "data", "ingredients.json"
    )
    try:
        with open(data_path, "r") as f:
            dataset = {
                entry["name"].lower(): entry 
                for entry in json.load(f)
            }
    except:
        dataset = {}
    
    results = []
    for name in ingredients:
        key = name.lower()
        entry = dataset.get(key)
        if entry:
            results.append({
                "name": name,
                "classification": entry["classification"],
                "category": entry["category"],
                "notes": entry["notes"]
            })
        else:
            results.append({
                "name": name,
                "classification": "unknown",
                "category": "uncategorised",
                "notes": "Not found in database."
            })
    return results
