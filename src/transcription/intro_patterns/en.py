"""
English self-introduction regex patterns.
Template for adapting to English-language podcasts.
"""

INTRODUCTION_PATTERNS = [
    r"this is ([^,]+?)(?:,|\s+from\s|\s+and\s|$)",
    r"i'?m ([^,]+?)(?:,|\s+from\s|\s+and\s|$)",
    r"my name is ([^,]+?)(?:,|\s+from\s|\s+and\s|$)",
]