# Phase 2 — Transcription

## Executive Summary

Phase 2 transcribes the downloaded audio files into text using OpenAI's
Whisper large-v3 model with optimized parameters for podcast content.
Each transcription is saved with timestamped segments to support downstream
diarization and chunking.

| Metric | Value |
|---|---|
| Total episodes transcribed | 357 / 1052 (in progress) |
| Coverage | 33.9% |
| Avg confidence (logprob) | -0.1381 |
| Avg repetition rate | 1.0 |
| Hallucination flagged | 0 |
| Avg words per episode | ~20,000 |
| Model used | large-v3 |
| Device | CUDA (RTX 3050 Ti) |
| Avg transcription time | ~12 min per episode |
| Estimated full dataset time | ~210 hours |

## Objectives

- Convert all downloaded audio files to text with sentence-level timestamps
- Detect and flag potentially low-quality transcriptions
- Produce a baseline of quality metrics for monitoring

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Transcriber | `src/transcription/transcriber.py` | ✅ Complete |
| Validator | `src/transcription/validator.py` | ✅ Complete |
| Database Schema | `src/ingestion/database.py` | ✅ Updated |
| Migration | `migrations/versions/` | ✅ Applied |

## Architectural Decisions

### Model selection: large-v3 over medium

Initially considered `medium` for speed, but it lost 26 seconds of audio
content when `initial_prompt` was added. `large-v3` with optimized parameters
recovered all lost segments and correctly transcribed proper nouns
(e.g., "Alottoni" instead of "Hello Tony").

For a RAG pipeline, coverage and accuracy outweigh speed.

### Quantization: int8_float16

Used to fit `large-v3` in 4GB VRAM. Quality impact is minimal compared to
the memory savings achieved.

### Permissive thresholds for music handling

`vad_filter=False` and relaxed `no_speech_threshold` (0.8) prevent the model
from discarding segments that contain music or sound effects, common in
podcast intros and transitions.

### Per-segment storage

Each transcribed segment is saved with `start_time`, `end_time`, and metrics
(logprob, no_speech_prob). This granularity is required by Phase 3 alignment.

### Quality flagging

Episodes with `repetition_rate < 0.5` are automatically flagged as potential
hallucination loops. Flagged episodes should be reviewed before downstream
processing.

## Quality Validation

Validated metrics across the transcribed corpus:

- Average log probability: -0.1381 (excellent confidence)
- Repetition rate: 1.0 (no hallucination loops detected)
- Characters per minute: ~1070 (consistent with normal Portuguese conversation)
- Language confidence: 1.0 (clear language identification)

See [pipeline.md](./pipeline.md) for the full quality metrics reference.

## Configuration

| Parameter | Default | Where to configure |
|---|---|---|
| `WHISPER_MODEL` | large-v3 | `config/podcasts/{name}.py` |
| `WHISPER_LANGUAGE` | pt | `config/podcasts/{name}.py` |
| `WHISPER_INITIAL_PROMPT` | Portuguese with NerdCast names | `config/podcasts/{name}.py` |
| `WHISPER_DEVICE` | cuda | `src/transcription/config.py` |
| `WHISPER_COMPUTE_TYPE` | int8_float16 | `src/transcription/config.py` |
| `WHISPER_VAD_FILTER` | False | `src/transcription/config.py` |
| `WHISPER_NO_SPEECH_THRESHOLD` | 0.8 | `src/transcription/config.py` |

See [REPLICATION_GUIDE.md](../REPLICATION_GUIDE.md) for adapting to a different
podcast.

## Known Limitations

- **OOV errors:** Uncommon proper nouns may be transcribed incorrectly. The
  `initial_prompt` mitigates this for known names but cannot cover all cases
- **Music segments:** May generate noise, but the permissive parameters
  prevent loss of valid speech
- **Processing time:** Full dataset takes ~210 hours on RTX 3050 Ti.
  Cloud GPUs would be faster but introduce cost
- **Hallucination flagging:** Automatic flagging is based on repetition.
  Other types of hallucinations (factual errors) are not detected automatically

## Language Considerations

Transcription is highly language-dependent:

- **Whisper supports 100+ languages** but quality varies significantly.
  Best performance: English, Spanish, French, Portuguese, German, Italian
- **`initial_prompt`** must be written in the target language and include
  proper nouns specific to the podcast (host names, recurring terms, jargon)
- **`language` parameter** should be explicitly set rather than auto-detected
  for consistency
- **Punctuation conventions** vary by language. Whisper tends to use
  source-language punctuation, which is important for downstream chunking
- **For low-resource languages,** consider fine-tuning Whisper on domain
  audio or using language-specific ASR alternatives

## Next Steps

- Phase 3: Speaker diarization with pyannote
- Phase 4: Chunking the transcribed text for RAG
- Review hallucination-flagged episodes after full transcription completes
- Expand `initial_prompt` with new proper nouns identified during processing

## How to Run

```bash
# Activate environment
.\venv\Scripts\Activate.ps1

# Test with one episode
python -c "from src.transcription.transcriber import run; run(max_episodes=1)"

# Full transcription
python -m src.transcription.transcriber

# Validate quality
python -m src.transcription.validator
```