"""
IngredIQ - FastAPI Backend
Entry point: defines the app, middleware, and API routes.

Full pipeline per request:
    POST /analyze
        │
        ├── ocr.py      extract_text_from_image(bytes)  → raw text
        ├── parser.py   extract_ingredients(text)        → ingredient names
        ├── analyzer.py analyze_ingredients(names)       → classified items
        └── scoring.py  score_ingredients(analyzed)      → score + grade
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq
import os
from PIL import Image
import io

from ocr      import extract_text_from_image
from parser   import extract_ingredients
from analyzer import analyze_ingredients
from scoring  import score_ingredients

# ---------------------------------------------------------------------------
# App initialisation
# ---------------------------------------------------------------------------

app = FastAPI(
    title="IngredIQ API",
    description="AI-powered ingredient analysis from product label images.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

# Allow all origins during development; tighten in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("\n=== DEBUG: 422 VALIDATION ERROR ===")
    print(f"Request URL: {request.url}")
    print(f"Error Details: {exc.errors()}")
    if hasattr(exc, 'body'):
        print(f"Body: {exc.body}")
    print("=====================================\n")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

@app.get("/health")
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok"}


@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")


@app.get("/index.html")
async def serve_index():
    return FileResponse("index.html")


def resize_image(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    max_size = 1024
    if max_size < max(img.size):
        ratio = max_size / max(img.size)
        new_size = (
            int(img.width * ratio), 
            int(img.height * ratio)
        )
        img = img.resize(new_size, Image.LANCZOS)
    
    # Convert back to bytes as JPEG
    buffer = io.BytesIO()
    # If the original image was PNG/WEBP with transparency, 
    # convert to RGB before saving as JPEG.
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Accept a product-label image and return a full ingredient analysis.

    Pipeline:
        1. OCR      – extract raw text from the image bytes
        2. Parser   – clean and split into an ingredient list
        3. Analyzer – classify each ingredient (safe / moderate / harmful)
        4. Scoring  – compute a 0–10 health score and letter grade

    Returns:
        JSON with filename, ingredients (with risk levels), and safety score.

    Raises:
        400 – invalid file type or unreadable content
        422 – pipeline validation error (empty text, no ingredients found)
        500 – unexpected internal error
    """

    # --- Validate file type -----------------------------------------------
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Please upload an image.",
        )

    print("\n=== DEBUG: STARTING SCAN ===")
    import os
    api_key = os.getenv("GROQ_API_KEY")
    print(f"API Key present: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
    print(f"Filename: {file.filename}")
    print("==============================\n")

    # --- Read image bytes -------------------------------------------------
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # --- Resize image to optimize processing speed -------------------------
    try:
        image_bytes = resize_image(image_bytes)
    except Exception as exc:
        # Fallback to original bytes if resizing fails
        print(f"Warning: Image resizing failed: {str(exc)}")

    try:
        # --- Step 1: OCR --------------------------------------------------
        raw_text = extract_text_from_image(image_bytes)

        # --- Step 2: Parse ------------------------------------------------
        ingredient_names = extract_ingredients(raw_text)
        
        print(f"\n=== DEBUG: OCR/PARSER RESULT ===")
        print(f"Extracted Ingredients: {ingredient_names}")
        print("==================================\n")

        # --- Step 3: Analyze ----------------------------------------------
        analyzed = analyze_ingredients(ingredient_names)

        # --- Step 4: Score ------------------------------------------------
        result = score_ingredients(analyzed)

    except ValueError as exc:
        # Pipeline validation errors (empty text, no ingredients, etc.)
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        # Catch-all for unexpected failures — log in production.
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(exc)}")

    # --- Build response ---------------------------------------------------
    return {
        "filename": file.filename,
        "status": "success",
        "ingredients": [
            {
                "name":     item["name"],
                "risk":     item["classification"],   # safe | moderate | harmful | unknown
                "category": item["category"],
                "notes":    item["notes"],
            }
            for item in analyzed
        ],
        "score": {
            "overall":   result["score"],      # 0.0 – 10.0
            "grade":     result["grade"],       # A | B | C | D | F
            "summary":   result["summary"],
            "breakdown": result["breakdown"],   # counts per classification
            "flags":     result["flags"],       # names of harmful ingredients
        },
    }

class ChatRequest(BaseModel):
    message: str
    context: str = ""

@app.post("/chat")
async def chat_assistant(request: ChatRequest):
    """
    AI Chat Assistant endpoint. 
    Accepts user message and optional scan context.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    try:
        client = Groq(api_key=api_key)
        
        system_prompt = (
            "You are IngredIQ assistant, a helpful food safety expert. "
            "Answer questions about ingredients, health effects, and safer alternatives. "
            "Be concise and friendly. Use the scan context provided to give specific answers. "
            "Context: " + (request.context if request.context else "No scan has been performed yet.")
        )

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content.strip()
        return {"reply": reply}
        
    except Exception as e:
        print(f"Chat AI Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Assistant failed: {str(e)}")

class IngredientSearchRequest(BaseModel):
    ingredient: str

@app.post("/ingredient-search")
async def ingredient_search(request: IngredientSearchRequest):
    """
    AI Ingredient Search endpoint.
    Provides detailed safety information for a single ingredient.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")

    try:
        client = Groq(api_key=api_key)
        
        prompt = f"""You are a food safety expert. Analyze the ingredient: "{request.ingredient}"

Return a JSON object with this exact structure:
{{
  "name": "ingredient name",
  "classification": "safe" or "moderate" or "harmful",
  "category": "category like sweetener/preservative/fat/mineral/etc",
  "health_effects": "detailed explanation of health impact",
  "safer_alternatives": "suggested healthier alternatives",
  "notes": "one sentence safety summary"
}}

Return ONLY the JSON object, no other text."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean JSON if wrapped in markdown
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
            
        import json
        data = json.loads(result_text)
        return data
        
    except Exception as e:
        print(f"Search AI Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
