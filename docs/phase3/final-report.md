# Phase 3 — Diarization, Speaker Enrollment and Alignment

## Executive Summary

Phase 3 introduces the speaker dimension to the pipeline. It runs speaker
diarization on each episode, identifies known speakers via self-introduction
patterns, and aligns the resulting speaker segments with the transcription
text from Phase 2.

| Metric | Value |
|---|---|
| Total transcribed episodes | 1 (initial test, will scale to 1052) |
| Total diarized episodes | 1 |
| Diarization coverage | 100% |
| Average speakers per episode | 8.0 |
| Total chunks generated | 705 |
| Chunks with aligned text | 325 |
| Alignment rate | 46.1% |
| Total speakers identified | 3 |
| Hosts identified | 1 |
| Guests identified | 2 |
| Diarization model | pyannote/speaker-diarization-3.1 |
| Device | CUDA |
| Average diarization time | ~6 min per episode |
| Estimated full dataset time | ~105 hours |

## Objectives

- Identify which speaker is talking at each moment of the episode
- Recognize known hosts via self-introduction patterns at the start of each
  episode
- Align speaker segments with transcribed text for downstream RAG and
  speaker-aware queries

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Diarizer | `src/transcription/diarizer.py` | ✅ Complete |
| Speaker Enrollment | `src/transcription/speaker_enrollment.py` | ✅ Complete |
| Aligner | `src/transcription/aligner.py` | ✅ Complete |
| Validator | `src/transcription/diarization_validator.py` | ✅ Complete |

## Architectural Decisions

### soundfile for audio loading

pyannote 4.x requires `torchcodec`, which has incompatibilities with
the FFmpeg version available on Windows. Using `soundfile` to pre-load
audio as a tensor bypasses this dependency.

### 0.5 overlap ratio threshold for alignment

When mapping transcription segments to diarization chunks, a segment is
attributed to a chunk only if at least 50% of the segment's duration overlaps.
This balances coverage with attribution accuracy.

### Speaker collision warnings

When the same diarization speaker is mapped to multiple names (a sign that
diarization grouped distinct voices), the system logs a warning and keeps
the first mapping. This documents diarization errors without overwriting.

### Self-introduction enrollment

Rather than building a voice-print database upfront, speakers are identified
by parsing self-introduction phrases ("aqui é o X", "eu sou X") in the
opening minutes of each episode. This works without prior knowledge of who
participates in each episode.

## Quality Validation

Manual validation on test episode (NerdCast 1026):

- 5 of 8 detected speakers were correctly identified by name
- 2 hosts were misclassified due to diarization grouping artifacts
- Phase 8 backlog includes per-episode diarization tuning to address this

## Architecture: Single-Pass vs Chunked Diarization

The pipeline supports two diarization modes selected automatically based
on episode length:

| Mode | When | VRAM Use | Quality |
|---|---|---|---|
| Single-pass | Episodes < 90 min | Higher peak | Best (unified embeddings) |
| Temporal chunking | Episodes ≥ 90 min | Bounded by chunk size | Good (re-identification) |

The threshold and chunk parameters are configurable. See
[subpipeline-diarization.md](./subpipeline-diarization.md) for details
on the chunking strategy and speaker re-identification.

## Configuration

| Parameter | Default | Where to configure |
|---|---|---|
| Diarization model | pyannote/speaker-diarization-3.1 | `src/transcription/config.py` |
| Min overlap ratio for alignment | 0.5 | `src/transcription/aligner.py` |
| Known hosts dictionary | NerdCast hosts | `config/podcasts/{name}.py` |
| Self-introduction patterns | Portuguese | `config/podcasts/{name}.py` |
| Max speakers per episode | 8 | `config/podcasts/{name}.py` |

See [REPLICATION_GUIDE.md](../REPLICATION_GUIDE.md) for adapting to a different
podcast.

## Known Limitations

- **Voice grouping artifacts:** Diarization may group different voices as
  the same speaker in episodes with similar acoustic characteristics or
  background music
- **OOV proper nouns:** Names not in the known hosts dictionary may not be
  extracted correctly by the regex patterns
- **Re-identification edge cases:** For very long episodes processed with
  chunking, speakers appearing briefly in only one chunk may not be
  reliably re-identified if their embedding is noisy

## Language Considerations

This phase has significant language-specific components:

- **Diarization itself is language-agnostic** — pyannote analyzes audio,
  not transcribed text
- **Self-introduction regex patterns are language-specific:**
  - Portuguese: "aqui é o/a X", "eu sou X"
  - English: "this is X", "I'm X", "my name is X"
  - Spanish: "aquí es X", "soy X"
- **Tolerance windows may need tuning:** Languages with different speaking
  rhythms may require adjusting the 2-second tolerance for finding the
  nearest diarization chunk

## Next Steps

- Phase 4 (Chunking) consumes the aligned speaker-text data for RAG-optimized
  chunk generation
- Continue diarization on remaining transcribed episodes overnight

## How to Run

```bash
# Sequence after Phase 2 completes
python -m src.transcription.diarizer
python -m src.transcription.aligner
python -m src.transcription.speaker_enrollment

# Validation
python -m src.transcription.diarization_validator
```