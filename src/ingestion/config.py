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
    "exatamente como são falados. Exemplos: Alottoni, Azaghal, "
    "NerdCast, Jovem Nerd, RPG, cosplay, anime, manga."
)
WHISPER_VAD_FILTER = False
WHISPER_NO_SPEECH_THRESHOLD = 0.8
WHISPER_COMPRESSION_RATIO_THRESHOLD = 3.0
WHISPER_CONDITION_ON_PREVIOUS_TEXT = False
DEVICE = get_device()
COMPUTE_TYPE = get_compute_type(DEVICE)