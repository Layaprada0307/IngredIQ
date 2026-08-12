# IngredIQ — Product Requirements Document

## Project Overview
IngredIQ web app that lets users scan product 
labels to get AI-powered ingredient analysis and health scores.

## Tech Stack
- Backend: FastAPI (Python) running at http://127.0.0.1:8000
- Frontend: Single index.html (vanilla HTML/CSS/JS)
- No frameworks, no build tools

## Backend API
Endpoint: POST http://127.0.0.1:8000/analyze
- Input: image file (multipart/form-data, field name = "file")
- Output:
{
  "filename": "label.jpg",
  "status": "success",
  "ingredients": [
    {
      "name": "Sugar",
      "risk": "harmful",
      "category": "sweetener",
      "notes": "High glycaemic index, linked to obesity"
    }
  ],
  "score": {
    "overall": 4.5,
    "grade": "C",
    "summary": "Average — contains some questionable additives.",
    "breakdown": {"safe": 3, "moderate": 3, "harmful": 3},
    "flags": ["Sugar", "Sodium Benzoate"]
  }
}

## Frontend Requirements

### Screen 1 — Home
- IngredIQ logo and brand name at top
- Hero text: "Scan. Understand. Choose Better."
- Subtitle: "Unlock the hidden truth behind your food ingredients."
- Large green circular camera/upload button labeled "Camera Scan"
- Bottom navigation: Scan, History, Insights, Settings

### Screen 2 — Analyzing
- Header: "Analyzing Ingredients"
- Subtitle: "Our AI is deciding labels for safety and allergens"
- 3 animated progress steps shown one by one:
  1. Scanning Image (checkmark when done)
  2. Extracting Ingredients (checkmark when done)
  3. Analyzing Safety (spinner while active)

### Screen 3 — Results
- Circular score gauge (0-10), color: green=high, orange=mid, red=low
- Grade label: A/B="Excellent Choice", C="Good Choice", D/F="Poor Choice"
- Orange allergen warning banner if harmful ingredients exist
- Ingredient cards with:
  - Green dot + SAFE badge
  - Orange dot + MODERATE badge  
  - Red dot + HARMFUL badge
  - Ingredient name + notes
- "Scan Another Product" green button that resets to Screen 1

## Design
- Primary color: #22C55E (green)
- White background, rounded cards, soft shadows
- Smooth transitions between screens
- Match the Stitch UI screenshots exactly