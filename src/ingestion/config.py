"""
Podcast pipeline configuration.
"""
import torch

# RSS Feed
RSS_URL = "https://jn-feed.vercel.app/api/filter?podcast=nerdcast"
PODCAST_NAME = "nerdcast"

# Paths
RAW_AUDIO_DIR = "data/raw"
METADATA_DIR = "data/metadata"
TRANSCRIPTS_DIR = "data/transcripts"

# Feed fields mapping
FEED_FIELDS = {
    "id": "id",
    "title": "title",
    "published": "published",
    "duration": "itunes_duration",
    "description": "summary",
    "image": "itunes_image",
    "audio_url": "enclosure",
}

# Transcription
def get_device() -> str:
    """
    Detects the best available device for inference.
    Defaults to GPU if available, falls back to CPU.

    Returns:
        Device string: 'cuda' or 'cpu'
    """
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def get_compute_type(device: str) -> str:
    """
    Returns the optimal compute type for the given device.

    Args:
        device: Device string ('cuda' or 'cpu')

    Returns:
        Compute type string for faster-whisper
    """
    if device == "cuda":
        return "int8_float16"  # best for 4GB VRAM GPUs
    return "int8"              # best for CPU


WHISPER_MODEL = "large-v3"
WHISPER_LANGUAGE = "pt"
WHISPER_BEAM_SIZE = 5
WHISPER_INITIAL_PROMPT = (
    "Transcrição de podcast brasileiro de cultura pop. "
    "Preserve nomes próprios, termos técnicos e palavras em inglês "
    "exatamente como são falados. Exemplos: Alenxandre Ottoni, Alottoni, Azaghal, "
    "NerdCast, Jovem Nerd, RPG, cosplay, anime, manga."
)
WHISPER_VAD_FILTER = False
WHISPER_NO_SPEECH_THRESHOLD = 0.8
WHISPER_COMPRESSION_RATIO_THRESHOLD = 3.0
WHISPER_CONDITION_ON_PREVIOUS_TEXT = False
WHISPER_CHUNK_LENGTH = 30  # seconds per chunk, prevents OOM on long episodes
DEVICE = get_device()
COMPUTE_TYPE = get_compute_type(DEVICE)

import os
from dotenv import load_dotenv

load_dotenv()

# Diarization
HF_TOKEN = os.getenv("HF_TOKEN")
DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
DIARIZATION_MIN_SPEAKERS = 2
DIARIZATION_MAX_SPEAKERS = 8        # NerdCast rarely has over 6 participants
SPEAKER_EMBEDDING_MODEL = "pyannote/embedding"
SPEAKER_SIMILARITY_THRESHOLD = 0.85  # threshold to identify speaker
DIARIZATION_DIR = "data/diarization" # folder for outpus 

# Chunking (phase 4)
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNK_SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", " ", ""]

# Vector indexing (phase 5)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
EMBEDDING_DIMENSIONS = 768
CHROMA_DB_PATH = "data/chroma_db"
CHROMA_COLLECTION_NAME = "podcast_chunks"
DISTANCE_METRIC = "cosine"