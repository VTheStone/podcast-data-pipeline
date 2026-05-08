"""
UI translations loader.

Loads strings from the language module specified in settings.LANGUAGE,
substituting podcast-specific placeholders.
"""

import importlib
from config import settings


_SUPPORTED_LANGUAGES = {"pt_br", "en"}


def _load_translations_module():
    """Loads the translations module for the active language."""
    lang = settings.LANGUAGE.lower()

    if lang not in _SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Language '{lang}' not supported in UI. "
            f"Available: {sorted(_SUPPORTED_LANGUAGES)}. "
            f"Add a new module in src/ui/translations/."
        )

    return importlib.import_module(f"src.ui.translations.{lang}")


def t(key: str, **kwargs) -> str:
    """
    Returns the translated string for the given key,
    formatted with podcast-specific placeholders.

    Args:
        key: The translation key (e.g., "HEADER_TITLE")
        **kwargs: Additional format arguments

    Returns:
        The translated and formatted string.
    """
    module = _load_translations_module()
    template = getattr(module, key)

    # Always make podcast_name available
    format_args = {
        "podcast_name": settings.PODCAST_DISPLAY_NAME,
        **kwargs,
    }

    try:
        return template.format(**format_args)
    except (KeyError, IndexError):
        # Template doesn't use placeholders, return as-is
        return template