"""
Prompts package — loads language-appropriate prompt strings.

Uses settings.LANGUAGE to determine which prompt module to load.
Currently supported: pt_br, en.

Usage:
    from src.rag.prompts import SYSTEM_PROMPT, build_user_prompt
"""

import importlib
from config import settings


_SUPPORTED_LANGUAGES = {"pt_br", "en"}


def _load_prompts_module():
    """Loads the prompt module for the active language."""
    lang = settings.LANGUAGE.lower()

    if lang not in _SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Language '{lang}' not supported. "
            f"Available: {sorted(_SUPPORTED_LANGUAGES)}. "
            f"Add a new module in src/rag/prompts/."
        )

    return importlib.import_module(f"src.rag.prompts.{lang}")


# Load prompt strings from the active language module
_prompts = _load_prompts_module()

CHUNK_LABEL = _prompts.CHUNK_LABEL
EPISODE_LABEL = _prompts.EPISODE_LABEL
TIME_LABEL = _prompts.TIME_LABEL
CONTENT_LABEL = _prompts.CONTENT_LABEL
NO_CHUNKS_FOUND = _prompts.NO_CHUNKS_FOUND
SYSTEM_PROMPT = _prompts.SYSTEM_PROMPT
USER_PROMPT_TEMPLATE = _prompts.USER_PROMPT_TEMPLATE
NO_RESULTS_RESPONSE = _prompts.NO_RESULTS_RESPONSE


# Re-export formatting functions for backward compatibility
from src.rag.prompts.formatters import (
    format_chunk_for_context,
    build_context,
    build_user_prompt,
)


def build_no_results_response() -> str:
    """Returns the language-appropriate no-results response."""
    return NO_RESULTS_RESPONSE