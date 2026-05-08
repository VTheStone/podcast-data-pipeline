"""
Intro patterns loader — selects regex set based on settings.LANGUAGE.
"""

import importlib
from config import settings


_SUPPORTED_LANGUAGES = {"pt_br", "en"}


def _load_patterns_module():
    """Loads the patterns module for the active language."""
    lang = settings.LANGUAGE.lower()

    if lang not in _SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Language '{lang}' not supported for intro patterns. "
            f"Available: {sorted(_SUPPORTED_LANGUAGES)}. "
            f"Add a new module in src/transcription/intro_patterns/."
        )

    return importlib.import_module(f"src.transcription.intro_patterns.{lang}")


_module = _load_patterns_module()
INTRODUCTION_PATTERNS = _module.INTRODUCTION_PATTERNS