# Phase 7 — Query Interface

## Overview

End-user interface built with Streamlit that delivers the MVP value proposition:
allow users to ask questions about the entire podcast catalog and receive
answers with proper source citations.

## MVP Scope

This phase intentionally **does not** rely on speaker identification because
diarization and enrollment are not 100% accurate. The interface focuses on
content-based queries answered by the RAG pipeline from Phase 6.

## Features

- Natural language queries over the full podcast catalog
- Source citations with episode title and timestamp
- Episode metadata display (date, duration, image)
- Query history during the session

## Out of Scope

- Speaker-aware queries (deferred to Phase 8 after enrollment is refined)
- User accounts or persistent history
- Audio playback of cited segments

## Stack

- Streamlit for the web interface
- ChromaDB client for retrieval
- Ollama client for LLM responses
- SQLAlchemy for episode metadata lookup