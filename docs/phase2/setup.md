# Phase 2 Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| faster-whisper | 1.1+ | Whisper inference (CTranslate2) |
| torch | 2.6+cu124 | GPU inference |
| CTranslate2 | 4.4+ | Optimized transformer inference |

### External Services

None — Whisper models are downloaded automatically on first use from
HuggingFace Hub.

### Hardware

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| GPU | 4GB VRAM (large-v3 with int8) | 10GB+ VRAM | NVIDIA RTX 3050 Ti (4GB) |
| RAM | 16GB | 32GB | 16GB |
| Disk | 5GB free for models | — | — |

## Installation

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install Phase 2 dependencies
pip install faster-whisper
```

The first run downloads the model weights (~3GB for large-v3) into
`~/.cache/huggingface/hub/`.

## Configuration

### Environment Variables

None required for Phase 2. Uses defaults from `config/podcasts/{name}.py`.

### Podcast-Specific Configuration

In `config/podcasts/{name}.py`:

```python
WHISPER_LANGUAGE = "pt"  # ISO language code
WHISPER_INITIAL_PROMPT = (
    "Transcrição de podcast brasileiro de cultura pop. "
    "Exemplos: Alexandre Ottoni, Alottoni, Azaghal, NerdCast, Jovem Nerd..."
)
```

The `initial_prompt` should:
- Be written in the target language
- Include proper nouns specific to the podcast (hosts, recurring guests)
- Include jargon and domain terms that may be misrecognized
- Stay under 200 characters to avoid context dilution

## Validation

After setup, verify transcription works on a short audio sample:

```bash
python tests/explore_whisper.py
```

Expected output:

Model loaded: large-v3
Device: CUDA (NVIDIA GeForce RTX 3050 Ti Laptop GPU)
Test audio duration: 60s
Segments transcribed: 9
Transcription time: 7.2s
Real-time factor: 0.12x
Sample text: "Você está ouvindo NerdCast..."

## Decision Log

**Decision:** large-v3 over medium
**Context:** medium was tested first for speed but lost audio content when
adding `initial_prompt`.
**Options considered:**
- medium — 134h estimated total, but lost 26s in test
- large-v3 — 208h estimated, complete coverage and better proper nouns
**Outcome:** large-v3 chosen. Coverage and accuracy outweigh time savings.

**Decision:** int8_float16 quantization
**Context:** large-v3 in fp16 requires ~10GB VRAM, exceeding the available 4GB.
**Options considered:**
- Use medium model — lower quality
- Use cloud GPU — adds cost
- Quantize large-v3 — fits in 4GB with minor quality impact
**Outcome:** int8_float16 chosen. Quality difference is negligible vs cost
of alternatives.

**Decision:** Permissive VAD and silence thresholds
**Context:** Default Whisper parameters were dropping segments with background
music or sound effects, losing podcast intros.
**Options considered:**
- Default parameters — high precision, low recall on music segments
- Disable VAD entirely — risk of more hallucinations
- Permissive thresholds — middle ground
**Outcome:** `vad_filter=False`, `no_speech_threshold=0.8` chosen for
recall over precision.

## Known Issues

- **Python 3.13 compatibility:** faster-whisper works but warning logs
  may appear about deprecation. Validated to function correctly
- **VRAM pressure:** Running Whisper concurrently with other GPU workloads
  (pyannote, embeddings) causes OOM. Phase orchestration must serialize
  GPU operations
- **First load slow:** Model download on first run takes 3-5 minutes
  depending on network

## Language Considerations

Whisper has different quality tiers per language:

- **Tier 1 (highest quality):** English, Spanish, French, Portuguese, German,
  Italian, Chinese, Japanese
- **Tier 2 (good quality):** Most European languages, Korean, Arabic, Russian
- **Tier 3 (lower quality):** Low-resource languages may produce poor results

For Tier 3 languages, consider:

- Fine-tuning Whisper on domain audio
- Using language-specific ASR alternatives (e.g., Wav2Vec2 fine-tuned models)
- Manually crafting a more detailed `initial_prompt`

## Platform Considerations

- **Windows:** Validated. Uses CUDA via PyTorch
- **Linux:** Should work identically with CUDA installed
- **Mac (Apple Silicon):** faster-whisper supports MPS but quality and
  speed may differ. Untested in this project
- **CPU-only:** Possible but extremely slow (~50x slower than GPU)