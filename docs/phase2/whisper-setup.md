# Whisper Setup — Phase 2

## Model Selection

| Model | Test Result | Decision |
|---|---|---|
| medium | 7 segments, lost 26s of audio after initial_prompt | ❌ Rejected |
| large-v3 | 9 segments, full coverage, correct proper nouns | ✅ Selected |

## Decision Rationale

medium was initially considered for speed, but after adding initial_prompt
it started losing 26 seconds of audio content. large-v3 with optimized
parameters recovered all lost segments and correctly transcribed proper
nouns like "Alottoni" which medium transcribed as "Hello Tony".

For a RAG pipeline, coverage and accuracy are more critical than speed.

## Optimized Parameters

| Parameter | Value | Reason |
|---|---|---|
| model | large-v3 | Best coverage and accuracy |
| language | pt | Force Portuguese detection |
| beam_size | 5 | Default, good balance |
| initial_prompt | see config.py | Guides proper nouns and English terms |
| vad_filter | False | Prevents losing segments with background music |
| no_speech_threshold | 0.8 | More permissive than default 0.6 |
| compression_ratio_threshold | 3.0 | More permissive than default 2.4 |
| condition_on_previous_text | False | Prevents context bias between segments |

## Hardware Configuration

- Device: CUDA (NVIDIA GeForce RTX 3050 Ti Laptop GPU)
- VRAM: 4.0 GB
- compute_type: int8_float16
- PyTorch: 2.6.0+cu124
- CUDA: 12.4
- faster-whisper: 1.1.1

## Validation Results

| Metric | medium | large-v3 |
|---|---|---|
| Segments in 60s | 7 | 9 |
| Coverage | ❌ Lost 26s | ✅ Complete |
| "Alottoni" transcribed | ❌ "Hello Tony" | ✅ "Alottoni" |
| Transcription time | 4.6s | 7.2s |
| Estimated full dataset | 134h | 208h |

## Known Limitations

- OOV errors may still occur for uncommon proper nouns not in initial_prompt
- initial_prompt should be expanded as new proper nouns are identified
- Processing time ~208 hours for full dataset on RTX 3050 Ti