# Changelog

## [0.6.0] - 2026-05-01

### Added
- RAG pipeline integrating semantic search with LLM
- Groq API integration with llama-3.3-70b-versatile
- Prompt engineering module with citation enforcement
- Interactive Q&A terminal interface
- Evaluation suite with 11 queries across 5 categories
- Manual evaluation report with quality metrics

### Configuration
- LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
- RAG_MIN_SIMILARITY (0.5), RAG_N_CHUNKS (5)

## [0.5.0] - 2026-04-29

### Added
- ChromaDB vector indexing pipeline
- Semantic search with metadata filtering
- 16,343 chunks indexed (initial)
- Sync between SQLite and ChromaDB

## [0.4.0] - 2026-04-27

### Added
- Recursive chunking pipeline with tiktoken
- RAGChunk schema with timestamps and speaker metadata
- Position-based timestamp tracking with overlap handling

## [0.3.0] - 2026-04-26

### Added
- pyannote diarization pipeline
- Speaker enrollment via self-introduction patterns
- Whisper + pyannote alignment

## [0.2.0] - 2026-04-25

### Added
- Whisper large-v3 transcription pipeline
- Per-segment timestamps
- Quality validation metrics

## [0.1.0] - 2026-04-24

### Added
- RSS feed ingestion
- Audio download for 1052 episodes
- SQLite metadata catalog