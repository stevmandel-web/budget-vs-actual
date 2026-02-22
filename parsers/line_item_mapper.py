"""
Normalizes line item names between budget and actuals files.
Handles aliases, fuzzy matching, and whitespace differences.
"""
from config import LINE_ITEM_ALIASES, DATA_LINE_ITEMS


def normalize_name(name):
    """Clean up a line item name for matching."""
    if not name or not isinstance(name, str):
        return ""
    return name.strip()


def canonical_name(name):
    """Map an actuals/budget line item name to the canonical P&L name."""
    clean = normalize_name(name)
    if not clean:
        return ""

    # Direct match
    if clean in DATA_LINE_ITEMS:
        return clean

    # Alias match
    if clean in LINE_ITEM_ALIASES:
        return LINE_ITEM_ALIASES[clean]

    # Case-insensitive match
    lower = clean.lower()
    for item in DATA_LINE_ITEMS:
        if item.lower() == lower:
            return item

    # Case-insensitive alias match
    for alias, canon in LINE_ITEM_ALIASES.items():
        if alias.lower() == lower:
            return canon

    return clean  # Return as-is if no match found
