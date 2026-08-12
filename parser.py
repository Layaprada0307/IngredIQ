"""
IngredIQ - Parser Module
Transforms raw OCR text into a clean, normalised list of ingredient names.

Cleaning pipeline per token:
    1. Isolate the ingredients block (text after "INGREDIENTS:")
    2. Strip the "may contain" footer and similar disclaimers
    3. Split on commas
    4. Remove parenthetical details  – e.g. "(10%)", "(Emulsifier)"
    5. Strip punctuation and whitespace
    6. Title-case for consistent downstream lookup
    7. Drop empty or junk tokens
"""

import re

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Matches the ingredient block header (case-insensitive).
_INGREDIENTS_HEADER = re.compile(r"ingredients\s*:", re.IGNORECASE)

# Disclaimer lines to drop before splitting.
_DISCLAIMER_PATTERN = re.compile(
    r"may contain.*$|contains.*allergen.*$|manufactured in.*$",
    re.IGNORECASE | re.MULTILINE,
)

# Parenthetical content to remove from each token, e.g. "(10%)", "(E211)".
_PARENTHETICAL = re.compile(r"\(.*?\)")

# Characters that are not letters, digits, spaces, or hyphens.
_JUNK_CHARS = re.compile(r"[^a-zA-Z0-9\s\-]")

# Tokens that are clearly not ingredient names after cleaning.
_SKIP_TOKENS = {"and", "or", "with", "contains", "ingredients"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_ingredients(text: str) -> list[str]:
    """
    Parse raw OCR label text into a clean list of ingredient names.

    Args:
        text: Raw string as returned by ocr.extract_text_from_image().

    Returns:
        List of normalised ingredient name strings, e.g.:
        ["Sugar", "Palm Oil", "Cocoa Powder", "Soy Lecithin", ...]

    Raises:
        ValueError: If text is empty or no ingredient block is found.
    """
    if not text or not text.strip():
        raise ValueError("Input text is empty.")

    # --- Step 1: isolate the ingredients block ----------------------------
    match = _INGREDIENTS_HEADER.search(text)
    if match:
        text = text[match.end():]   # everything after "INGREDIENTS:"
    # If no header found, attempt to parse the whole text as-is.

    # --- Step 2: drop disclaimer lines ------------------------------------
    text = _DISCLAIMER_PATTERN.sub("", text)

    # --- Step 3: split on commas ------------------------------------------
    tokens = text.split(",")

    # --- Steps 4-7: clean each token --------------------------------------
    ingredients = []
    for token in tokens:
        # Remove parenthetical details
        token = _PARENTHETICAL.sub("", token)

        # Strip non-alphabetic junk (percentages, stray punctuation)
        token = _JUNK_CHARS.sub("", token)

        # Normalise whitespace and title-case
        token = " ".join(token.split()).title()

        # Drop empty strings and known non-ingredient words
        if token and token.lower() not in _SKIP_TOKENS:
            ingredients.append(token)

    if not ingredients:
        raise ValueError("No ingredients could be extracted from the provided text.")

    return ingredients
