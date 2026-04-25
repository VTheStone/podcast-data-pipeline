# 🎙️ Podcast Data Pipeline

> End-to-end pipeline for podcast audio ingestion, transcription, and semantic search
> using Whisper, ChromaDB and local LLMs.

## Architecture

```mermaid
graph LR
    A[RSS Feed] --> B[Audio Download]
    B --> C[Whisper Transcription]
    C --> D[Chunking + Embeddings]
    D --> E[ChromaDB]
    E --> F[RAG + LLM]
    F --> G[Query Interface]
```

## Stack

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Whisper](https://img.shields.io/badge/ASR-Whisper-green)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-orange)
![Ollama](https://img.shields.io/badge/LLM-Ollama-purple)

## Project Status

| Phase | Status | Description |
|---|---|---|
| 1. Data Collection | ✅ Complete | 1052 episodes, 55.6GB, 1734h of audio |
| 2. Transcription | 🔄 In Progress | large-v3, GPU, ~208h processing time |
| 3. Diarization | ⏳ Planned | pyannote/audio |
| 4. Chunking | ⏳ Planned | LlamaIndex |
| 5. Vector Indexing | ⏳ Planned | ChromaDB |
| 6. RAG + LLM | ⏳ Planned | Ollama + llama3 |

## Getting Started

```bash
git clone https://github.com/VTheStone/podcast-data-pipeline
cd podcast-data-pipeline
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your environment variables in .env
```

## Documentation

Each phase has detailed documentation in `/docs`:
- [Phase 1 — Data Collection](docs/phase1/)

## Key Learnings

Project developed with focus on:
- Data Engineering (pipelines, idempotency, orchestration)
- MLOps (ASR, embeddings, RAG)
- Best practices (versioning, documentation, testing)