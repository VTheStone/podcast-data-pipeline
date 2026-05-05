"""
Configuration loader.

Reads PODCAST_PROFILE from environment, loads the appropriate podcast
profile, and merges it with default settings.

Usage:
    from config import settings

    print(settings.RSS_URL)
    print(settings.WHISPER_MODEL)
"""

import os
import importlib
from types import ModuleType
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Unified settings object combining defaults and podcast-specific overrides.

    Attribute access works like a regular module — settings.X looks up X
    first in the podcast profile, then falls back to defaults.
    """

    def __init__(self, default_module: ModuleType, podcast_module: ModuleType):
        self._default = default_module
        self._podcast = podcast_module

    def __getattr__(self, name: str):
        # Try podcast profile first (overrides)
        if hasattr(self._podcast, name):
            return getattr(self._podcast, name)
        # Fall back to default
        if hasattr(self._default, name):
            return getattr(self._default, name)
        raise AttributeError(
            f"Setting '{name}' not found in default or podcast profile"
        )


def _load_settings() -> Settings:
    """Loads default settings and the active podcast profile."""
    profile = os.getenv("PODCAST_PROFILE", "nerdcast")

    default_module = importlib.import_module("config.default")

    try:
        podcast_module = importlib.import_module(f"config.podcasts.{profile}")
    except ImportError as exc:
        raise ImportError(
            f"Podcast profile '{profile}' not found in config/podcasts/. "
            f"Set PODCAST_PROFILE environment variable to a valid profile name."
        ) from exc

    return Settings(default_module, podcast_module)


settings = _load_settings()