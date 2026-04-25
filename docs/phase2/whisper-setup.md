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

## Quality Metrics Reference

### avg_logprob (Average Log Probability)
Log probability médio de todos os segmentos. Representa a confiança geral 
do modelo na transcrição gerada.

| Range | Interpretation |
|---|---|
| > -0.2 | Excellent — model very confident |
| -0.2 to -0.4 | Good — reliable transcription |
| -0.4 to -0.7 | Acceptable — some uncertain segments |
| < -0.7 | Poor — low confidence, review recommended |

**Baseline:** -0.1381

---

### repetition_rate
Proporção de chunks únicos de 50 palavras em relação ao total de chunks.
Detecta loops de alucinação onde o modelo repete a mesma frase infinitamente.

| Range | Interpretation |
|---|---|
| 1.0 | Perfect — no repetition detected |
| 0.8 to 1.0 | Good — minor repetitions |
| 0.5 to 0.8 | Warning — significant repetition |
| < 0.5 | Critical — hallucination loop detected |

**Baseline:** 1.0  
**Threshold:** Episodes with repetition_rate < 0.5 are automatically flagged 
with hallucination_flag = True

---

### chars_per_minute
Número de caracteres transcritos por minuto de áudio.
Usado como proxy para cobertura — episódios com valor muito baixo podem
ter perdido trechos significativos de áudio.

| Range | Interpretation |
|---|---|
| > 900 | Good — full coverage expected |
| 600 to 900 | Acceptable — minor gaps possible |
| 300 to 600 | Warning — significant gaps likely |
| < 300 | Poor — major content loss |

**Baseline:** 1070.2 chars/min (NerdCast 1026 - normal conversation episode)  
**Note:** Music-heavy or intro/outro-heavy episodes naturally score lower.

---

### language_confidence
Probabilidade do idioma detectado pelo modelo, de 0.0 a 1.0.
Valores baixos indicam que o modelo teve dificuldade em identificar o idioma,
o que pode afetar a qualidade da transcrição.

| Range | Interpretation |
|---|---|
| > 0.9 | Excellent — language clearly identified |
| 0.7 to 0.9 | Good — reliable detection |
| 0.5 to 0.7 | Warning — mixed language content |
| < 0.5 | Poor — language detection failed |

**Baseline:** 1.0

---

### estimated_words
Estimativa do número de palavras baseada no número de caracteres (chars / 5).
Útil para comparar volume de conteúdo entre episódios.

**Baseline:** 20.136 words (NerdCast 1026 — 94 min episode)  
**Reference:** ~214 words/min for normal Portuguese podcast conversation

---

### hallucination_flag
Flag booleano automático. Marcado como True quando repetition_rate < 0.5.
Episódios com este flag ativo devem ser revisados manualmente antes de
serem incluídos no RAG pipeline.

**Baseline:** False  
**Action when True:** Delete transcription and reprocess with adjusted parameters

---

## Quality Baseline (NerdCast 1026 - Artemis II)

| Metric | Value | Status |
|---|---|---|
| avg_logprob | -0.1381 | ✅ Excellent |
| repetition_rate | 1.0 | ✅ Perfect |
| chars_per_minute | 1070.2 | ✅ Good |
| language_confidence | 1.0 | ✅ Excellent |
| estimated_words | 20.136 | ✅ Reference |
| hallucination_flag | False | ✅ Clean |

Episodes significantly below these baselines should be reviewed manually.

## Known Limitations

- OOV errors may still occur for uncommon proper nouns not in initial_prompt
- initial_prompt should be expanded as new proper nouns are identified
- Processing time ~208 hours for full dataset on RTX 3050 Ti