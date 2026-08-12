"""
IngredIQ - Scoring Module
Computes a 0–10 health score from the analyzed ingredient list.

Scoring logic:
    - Start at 10.0 (perfect score)
    - Each "harmful"  ingredient deducts HARMFUL_PENALTY  (2.0 pts)
    - Each "moderate" ingredient deducts MODERATE_PENALTY (0.5 pts)
    - Each "unknown"  ingredient deducts UNKNOWN_PENALTY  (0.25 pts)
    - "safe" ingredients have no deduction
    - Final score is clamped to [0.0, 10.0] and rounded to 1 decimal place
    - A letter grade (A–F) is derived from the final score
"""

from typing import TypedDict

# ---------------------------------------------------------------------------
# Tunable penalty weights
# ---------------------------------------------------------------------------

HARMFUL_PENALTY  = 2.0
MODERATE_PENALTY = 0.5
UNKNOWN_PENALTY  = 0.25

MAX_SCORE = 10.0

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class ScoreResult(TypedDict):
    score: float          # 0.0 – 10.0
    grade: str            # A | B | C | D | F
    summary: str          # Human-readable verdict
    breakdown: dict       # Count of each classification
    flags: list[str]      # Names of harmful ingredients, if any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _letter_grade(score: float) -> str:
    """Map a 0–10 score to a letter grade."""
    if score >= 8.5: return "A"
    if score >= 7.0: return "B"
    if score >= 5.0: return "C"
    if score >= 3.0: return "D"
    return "F"


def _summary(grade: str) -> str:
    """Return a one-line verdict for the grade."""
    return {
        "A": "Excellent — mostly clean ingredients.",
        "B": "Good — a few minor concerns.",
        "C": "Average — contains some questionable additives.",
        "D": "Poor — several harmful or unknown ingredients.",
        "F": "Very poor — heavily processed with harmful additives.",
    }[grade]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_ingredients(analyzed: list[dict]) -> ScoreResult:
    """
    Compute a health score from a list of analyzed ingredients.

    Args:
        analyzed: Output of analyzer.analyze_ingredients() — a list of
                  AnalyzedIngredient dicts with a "classification" field.

    Returns:
        ScoreResult with score, grade, summary, breakdown, and flags.

    Raises:
        ValueError: If the analyzed list is empty.
    """
    if not analyzed:
        raise ValueError("Analyzed ingredient list is empty. Cannot score.")

    # --- Tally classifications -------------------------------------------
    breakdown = {"safe": 0, "moderate": 0, "harmful": 0, "unknown": 0}
    flags: list[str] = []
    
    is_toxic = False

    for item in analyzed:
        classification = item.get("classification", "unknown")
        breakdown[classification] = breakdown.get(classification, 0) + 1

        if classification == "harmful":
            flags.append(item["name"])
            
        # Check rule 2: known pesticide, toxic chemical, or non-food substance
        text_check = f"{item.get('name', '')} {item.get('category', '')} {item.get('notes', '')}".lower()
        if any(kw in text_check for kw in ["pesticide", "toxic", "non-food", "non food"]):
            is_toxic = True

    # --- Compute score ----------------------------------------------------
    deduction = (
        breakdown["harmful"]  * HARMFUL_PENALTY +
        breakdown["moderate"] * MODERATE_PENALTY +
        breakdown["unknown"]  * UNKNOWN_PENALTY
    )

    score = round(max(0.0, min(MAX_SCORE, MAX_SCORE - deduction)), 1)
    
    total_ingredients = len(analyzed)
    override_summary = None
    override_grade = None
    
    if is_toxic:
        flags.append("⚠️ NOT A FOOD PRODUCT")
        score = min(score, 2.0)
        
    if breakdown["harmful"] / total_ingredients > 0.5:
        score = min(score, 3.0)
        override_grade = "F"
        override_summary = "Very poor — majority of ingredients are harmful"

    grade = override_grade if override_grade else _letter_grade(score)
    summary = override_summary if override_summary else _summary(grade)

    return ScoreResult(
        score=score,
        grade=grade,
        summary=summary,
        breakdown=breakdown,
        flags=flags,
    )
