# Phase 3 Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| pyannote.audio | 4.0.4 | Speaker diarization |
| torch | 2.6+cu124 | GPU inference |
| soundfile | 0.12+ | Audio loading (bypasses torchcodec) |

### External Services

- **HuggingFace Account** — required to download the pyannote model
  - Accept terms for `pyannote/speaker-diarization-3.1`
  - Accept terms for `pyannote/segmentation-3.0`
  - Generate a HuggingFace token at https://huggingface.co/settings/tokens

### Hardware

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| GPU | 4GB VRAM | 8GB+ VRAM | NVIDIA RTX 3050 Ti (4GB) |
| RAM | 16GB | 32GB | 16GB |

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install Phase 3 dependencies
pip install pyannote.audio==4.0.4 torch torchaudio soundfile
```

## Configuration

### Environment Variables

```env
HF_TOKEN=hf_your_token_here
```

### Podcast-Specific Configuration

The following must be customized in `config/podcasts/{name}.py`:

```python
# Maximum speakers expected per episode
MAX_SPEAKERS_PER_EPISODE = 8  # NerdCast rarely exceeds 6

# Known hosts dictionary (alias → canonical name)
KNOWN_HOSTS = {
    "alexandre ottoni": "Alexandre Ottoni",
    "alottoni": "Alexandre Ottoni",
    "azaghal": "Azaghal",
    "zagal": "Azaghal",
    "deive pazos": "Azaghal",
}

# Self-introduction patterns (regex by language)
INTRODUCTION_PATTERNS_LANGUAGE = "pt-BR"  # determines patterns used
```

## Validation

After setup, verify pyannote can load the model:

```bash
python tests/explore_pyannote.py
```

Expected output:

Pipeline parameters loaded
Audio duration tested: 3 minutes
Speakers detected: 4
Diarization time: 18s
Processing ratio: 0.1x (real-time)
Estimated full dataset: ~6h

## Decision Log

**Decision:** Use pyannote 4.x over 3.x
**Context:** Initial implementation used pyannote 3.x but version 4.x
released during development with improved API.
**Options considered:**
- Stay on 3.x — stable, more documentation
- Upgrade to 4.x — better diarization quality, breaking API changes
**Outcome:** Upgraded to 4.x for quality. Required handling new API
where `DiarizeOutput` has separate `speaker_diarization` (Annotation)
and `speaker_embeddings` (ndarray) attributes.

**Decision:** Use soundfile to load audio
**Context:** pyannote 4.x added `torchcodec` as a runtime dependency,
which doesn't work on Windows without specific FFmpeg builds (full-shared).
**Options considered:**
- Install FFmpeg full-shared — complex on Windows, version conflicts
- Pre-load audio with soundfile and pass tensor directly — bypasses
  torchcodec entirely
**Outcome:** soundfile chosen. The diarizer loads audio first, then
passes a `{waveform, sample_rate}` dict to pyannote.

## Known Issues

- **torchcodec on Windows:** The default `pyannote 4.x` install attempts
  to use torchcodec, which requires FFmpeg full-shared on Windows. The
  workaround using soundfile is documented in the diarizer code.
- **GPU memory:** RTX 3050 Ti (4GB) can run pyannote but cannot run it
  simultaneously with Whisper large-v3. Phases 2 and 3 are sequential
  on this hardware.

## Language Considerations

pyannote diarization itself is language-agnostic — it analyzes acoustic
features, not phonetic content. The model has been trained on multilingual
data and works equivalently across languages.

The language-specific parts are in the enrollment sub-pipeline (regex
patterns) and known hosts dictionary, both configured in the podcast profile.

## Platform Considerations

- **Windows:** Validated. Requires soundfile workaround for torchcodec.
- **Linux:** Should work with default pyannote install (FFmpeg available).
- **Mac:** Untested. May require similar audio loading workaround.