"""
Portuguese (Brazil) self-introduction regex patterns.
Used by speaker enrollment to identify hosts and guests.
"""

# Patterns capture name until comma, "e ", or preposition.
# Designed for Brazilian Portuguese podcast intros.
INTRODUCTION_PATTERNS = [
    r"aqui [eé] [oa] ([^,]+?)(?:,|\s+e\s|$)",
    r"eu sou [oa]? ?([^,]+?)(?:,|\s+e\s|$)",
    r"aqui quem vos fala [eé] [oa] ([^,]+?)(?:,|\s+e\s|$)",
]