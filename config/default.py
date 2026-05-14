"""
Default configuration shared across all podcasts.
These values rarely change and are not podcast-specific.
"""
import os
import torch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# Infrastructure (environment-dependent)
# ============================================================================

def get_device() -> str:
    """Detects the best available device for inference."""
    return "cuda" if torch.cuda.is_available() else "cpu"


def get_compute_type(device: str) -> str:
    """Returns the optimal compute type for the given device."""
    if device == "cuda":
        return "int8_float16"  # best for 4GB VRAM GPUs
    return "int8"


DEVICE = get_device()
COMPUTE_TYPE = get_compute_type(DEVICE)

HF_TOKEN = os.getenv("HF_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ============================================================================
# Paths
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

RAW_AUDIO_DIR = str(DATA_DIR / "raw")
METADATA_DIR = str(DATA_DIR / "metadata")
TRANSCRIPTS_DIR = str(DATA_DIR / "transcripts")
DIARIZATION_DIR = str(DATA_DIR / "diarization")
CHROMA_DB_PATH = str(DATA_DIR / "chroma_db")


# ============================================================================
# Phase 2: Transcription (technical defaults)
# ============================================================================

WHISPER_MODEL = "large-v3"
WHISPER_BEAM_SIZE = 5
WHISPER_VAD_FILTER = False
WHISPER_NO_SPEECH_THRESHOLD = 0.8
WHISPER_COMPRESSION_RATIO_THRESHOLD = 3.0
WHISPER_CONDITION_ON_PREVIOUS_TEXT = False
WHISPER_CHUNK_LENGTH = 30  # seconds, prevents OOM on long episodes


# ============================================================================
# Phase 3: Diarization (technical defaults)
# ============================================================================

DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
DIARIZATION_MIN_SPEAKERS = 2
SPEAKER_EMBEDDING_MODEL = "pyannote/embedding"
SPEAKER_SIMILARITY_THRESHOLD = 0.85

# Embedding batch size during diarization.
# Lower values use less VRAM but are slower.
# Default in pyannote 4.x is 32. Use 8 for 4GB VRAM cards.
DIARIZATION_EMBEDDING_BATCH_SIZE = 8

# Long-episode handling via temporal chunking.
# Episodes longer than the threshold are split into overlapping chunks
# and processed separately. Speakers are then re-identified across chunks
# using embedding similarity.
LONG_EPISODE_THRESHOLD_SECONDS = 5400       # 90 minutes
CHUNK_DURATION_SECONDS = 1800               # 30 minutes per chunk
CHUNK_OVERLAP_SECONDS = 30                  # overlap for context continuity
REID_SIMILARITY_THRESHOLD = 0.75            # cosine similarity to match speakers

# ============================================================================
# Phase 4: Chunking (technical defaults)
# ============================================================================

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]


# ============================================================================
# Phase 5: Vector Indexing (technical defaults)
# ============================================================================

EMBEDDING_DIMENSIONS = 768
CHROMA_COLLECTION_NAME = "podcast_chunks"
DISTANCE_METRIC = "cosine"


# ============================================================================
# Phase 6: RAG (technical defaults)
# ============================================================================

LLM_TEMPERATURE = 0.3
LLM_MAX_TOKENS = 1024
RAG_MIN_SIMILARITY = 0.5
RAG_N_CHUNKS = 5