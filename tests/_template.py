"""
Template for creating a new podcast profile.

To use this template:
1. Copy this file to config/podcasts/{your_podcast_name}.py
2. Fill in the values below
3. Set PODCAST_PROFILE={your_podcast_name} in your .env file
4. Validate with: python -c "from config import settings; print(settings.RSS_URL)"

For language-specific changes (prompts, UI strings, regex patterns),
also create matching modules in:
- src/rag/prompts/{language}.py
- src/ui/translations/{language}.py
- src/transcription/intro_patterns/{language}.py
"""


# ============================================================================
# Identity (REQUIRED)
# ============================================================================

# Internal name (lowercase, no spaces). Used for file paths and logging.
PODCAST_NAME = "your_podcast_name"

# Display name shown to end users (proper capitalization).
PODCAST_DISPLAY_NAME = "Your Podcast Name"

# Language code matching modules in src/rag/prompts/, src/ui/translations/,
# src/transcription/intro_patterns/
# Currently supported: "pt_br", "en"
LANGUAGE = "pt_br"


# ============================================================================
# Phase 1: Data Source (REQUIRED)
# ============================================================================

# Direct URL to the podcast's RSS feed
RSS_URL = "https://example.com/podcast.rss"

# Maps internal field names to RSS feed field names.
# Different podcast hosts use different conventions.
# Common variations:
#   - "description": "summary" or "subtitle" or "content"
#   - "audio_url": "enclosure" or custom field
#   - "image": "itunes_image" or "image"
FEED_FIELDS = {
    "id": "id",
    "title": "title",
    "published": "published",
    "duration": "itunes_duration",
    "description": "summary",
    "image": "itunes_image",
    "audio_url": "enclosure",
}


# ============================================================================
# Phase 2: Transcription (LANGUAGE-DEPENDENT)
# ============================================================================

# Whisper language code (ISO 639-1).
# See https://github.com/openai/whisper/blob/main/whisper/tokenizer.py
WHISPER_LANGUAGE = "pt"

# Initial prompt steers Whisper toward correct transcription.
# IMPORTANT: write in the target language and include:
# - Host names that may be misrecognized
# - Recurring guest names
# - Domain jargon (RPG, anime, AI, etc)
# - English loanwords pronounced in the target language
# Keep under 200 characters to avoid context dilution.
WHISPER_INITIAL_PROMPT = (
    "Transcrição de podcast brasileiro de cultura pop. "
    "Preserve nomes próprios e termos técnicos. "
    "Exemplos: Host1, Host2, NomeDoPodcast."
)


# ============================================================================
# Phase 3: Diarization (PODCAST-SPECIFIC)
# ============================================================================

# Maximum speakers expected in any single episode.
# Tighter limits help diarization quality.
# Examples:
#   - Solo podcast: 2 (host + occasional guest)
#   - Talk show: 4 (2 hosts + 2 guests)
#   - Round table: 8 (large panel discussions)
DIARIZATION_MAX_SPEAKERS = 6

# Mapping of name aliases to canonical names.
# Lowercase keys, properly capitalized values.
# Used by speaker_enrollment.py to identify recurring hosts.
KNOWN_HOSTS = {
    "host one alias": "Host One",
    "host1": "Host One",
    "host two alias": "Host Two",
}


# ============================================================================
# Phase 5: Vector Indexing (LANGUAGE-DEPENDENT)
# ============================================================================

# Embedding model. Multilingual model is the safe default.
# For better quality on specific languages:
#   - English-only: "sentence-transformers/all-mpnet-base-v2"
#   - Portuguese: consider BERTimbau-based models
#   - Chinese, Japanese, Korean: "BAAI/bge-m3"
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


# ============================================================================
# Phase 6: RAG (LANGUAGE-DEPENDENT)
# ============================================================================

# LLM model on Groq. Llama 3.3 has decent multilingual support.
# For language-specific quality:
#   - Portuguese: consider Sabia-3 (via Maritaca AI, separate provider)
#   - Chinese: consider Qwen
LLM_MODEL = "llama-3.3-70b-versatile"


# ============================================================================
# Phase 7: UI (PODCAST-SPECIFIC)
# ============================================================================

# Example queries shown on the welcome screen.
# Should reference actual content from your podcast.
# Aim for 4 queries spanning different topics.
EXAMPLE_QUERIES = [
    "What was the main topic of the most recent episode?",
    "Tell me about a specific recurring theme.",
    "What did the hosts say about [topic]?",
    "Why is [topic] important according to the show?",
]