"""
NerdCast-specific configuration profile.

To use a different podcast, copy _template.py and adjust the values.
"""

# ============================================================================
# Identity
# ============================================================================

PODCAST_NAME = "nerdcast"
PODCAST_DISPLAY_NAME = "NerdCast"
LANGUAGE = "pt_br"


# ============================================================================
# Phase 1: Data Source
# ============================================================================

RSS_URL = "https://jn-feed.vercel.app/api/filter?podcast=nerdcast"

# Maps internal field names to RSS feed field names
# Different podcast hosts use different field structures
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
# Phase 2: Transcription (language and content-specific)
# ============================================================================

WHISPER_LANGUAGE = "pt"

# Initial prompt steers Whisper toward correct transcription of:
# - Proper nouns (host names, recurring guests)
# - Domain jargon (RPG, anime, etc)
# - English loanwords pronounced in Portuguese
WHISPER_INITIAL_PROMPT = (
    "Transcrição de podcast brasileiro de cultura pop. "
    "Preserve nomes próprios, termos técnicos e palavras em inglês "
    "exatamente como são falados. Exemplos: Alexandre Ottoni, Alottoni, "
    "Azaghal, NerdCast, Jovem Nerd, RPG, cosplay, anime, manga."
)


# ============================================================================
# Phase 3: Diarization (podcast-specific)
# ============================================================================

# NerdCast rarely has over 6 participants per episode
DIARIZATION_MAX_SPEAKERS = 8

# Aliases mapping (lowercase variations → canonical name)
# Used by speaker_enrollment.py to identify hosts
KNOWN_HOSTS = {
    "alexandre ottoni": "Alexandre Ottoni",
    "alottoni": "Alexandre Ottoni",
    "azaghal": "Azaghal",
    "zagal": "Azaghal",
    "deive pazos": "Azaghal",
}


# ============================================================================
# Phase 5: Vector Indexing (language-dependent)
# ============================================================================

# Multilingual model — works for Portuguese among 50+ languages
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"


# ============================================================================
# Phase 6: RAG (language-dependent)
# ============================================================================

# Llama 3.3 has good Portuguese support
LLM_MODEL = "llama-3.3-70b-versatile"


# ============================================================================
# Phase 7: UI (podcast-specific)
# ============================================================================

# Example queries shown on the welcome screen
EXAMPLE_QUERIES = [
    "Quais astronautas participaram da Artemis II?",
    "Qual a diferença entre Artemis I e Artemis II?",
    "O que falaram sobre o Senhor dos Anéis?",
    "Por que voltar à Lua é importante?",
]