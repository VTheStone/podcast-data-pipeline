# Phase 8 — Identification Optimization

## Overview

Post-MVP phase focused on refining speaker identification quality after the
initial RAG pipeline is delivered. This phase enables speaker-aware queries
in the existing interface.

## Components

### 1. Diarization Fine-Tuning
- Experiment with clustering thresholds and segmentation parameters
- Test alternative diarization models
- Per-episode parameter optimization based on audio characteristics

### 2. Enrollment Refinement
- Improve self-introduction regex patterns
- Expand known hosts dictionary
- Handle speaker collisions when diarization groups multiple voices

### 3. Cross-Episode Speaker Consolidation
- Aggregate speaker embeddings across all episodes
- Detect recurring guests via embedding similarity
- Build robust voice profiles for hosts using progressive enrollment
- Use weighted average of embeddings based on confidence scores

## Database Schema

The schema for this phase is already in place (Speaker and SpeakerEmbedding
tables) since Phase 3, allowing incremental refinement without migrations.

## Success Criteria

- Hosts (Alexandre Ottoni, Azaghal) correctly identified in 95%+ of their episodes
- Recurring guests automatically grouped across episodes
- Speaker-aware queries enabled in the Phase 7 interface