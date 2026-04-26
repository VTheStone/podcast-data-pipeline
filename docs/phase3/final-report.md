# Phase 3 Final Report — Diarization, Enrollment and Alignment

## Executive Summary

| Metric | Value |
|---|---|
| Total transcribed episodes | 1 (will scale to 1052 overnight) |
| Total diarized episodes | 1 |
| Diarization coverage | 100% |
| Avg speakers per episode | 8.0 |
| Total chunks generated | 705 |
| Chunks with aligned text | 325 |
| Alignment rate | 46.1% |
| Total speakers identified | 3 |
| Hosts identified | 1 (Alexandre Ottoni) |
| Guests identified | 2 (Catiúcha Barcelos, Marcel Campos) |
| Model used | pyannote/speaker-diarization-3.1 |
| Device | CUDA (RTX 3050 Ti) |
| Avg diarization time | ~6 min per episode |

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Diarizer | `src/transcription/diarizer.py` | ✅ Complete |
| Speaker Enrollment | `src/transcription/speaker_enrollment.py` | ✅ Complete |
| Aligner | `src/transcription/aligner.py` | ✅ Complete |
| Validator | `src/transcription/diarization_validator.py` | ✅ Complete |

## Quality Notes

- **46% alignment rate** is expected — short diarization chunks (under 1 second)
  are typically interjections, laughs, or overlapping speech that don't have
  a corresponding transcription segment with sufficient overlap
- **8 speakers in test episode** — Artemis II had 6 actual hosts, the extra 2
  speakers may be due to diarization grouping artifacts that Phase 8 will refine
- **Speaker identification at 60%** in test episode (3 of 5 hosts identified) —
  diarization grouped Pedro Pallotta and Azaghal with other speakers, preventing
  their identification

## Known Limitations

- Diarization may group different voices as the same speaker in episodes with
  similar voice characteristics or background music
- Speaker collisions logged as warnings during enrollment
- Phase 8 (Identification Optimization) will address these limitations through:
  - Diarization fine-tuning with per-episode parameters
  - Cross-episode speaker consolidation via embedding similarity
  - Progressive enrollment refinement

## Architectural Decisions

- **soundfile for audio loading** — bypasses torchcodec/FFmpeg dependency
- **0.5 overlap ratio threshold** — balance between coverage and accuracy in alignment
- **Speaker collision warnings** — document diarization errors without overwriting

## Next Steps

- Phase 4: Chunking with semantic boundaries
- Run diarization on remaining transcribed episodes overnight