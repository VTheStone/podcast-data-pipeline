# Phase 7 — Query Interface (MVP Delivery)

## Executive Summary

Phase 7 delivers the MVP: a Streamlit web interface that wraps the RAG
pipeline in a usable application. End users can ask questions about
the podcast catalog through a chat-like UX without any technical knowledge.

| Aspect | Before Phase 7 | After Phase 7 |
|---|---|---|
| Access method | Terminal command | Web browser |
| User type | Developer | Any user |
| Conversation memory | None | Full session history |
| Examples | None | 4 clickable suggestions |
| Visual feedback | Plain text | Rich formatting + metrics |
| Source visibility | List only | Expandable cards with text |
| Session tracking | None | Tokens, time, question count |

## Objectives

- Wrap the RAG pipeline in an accessible interface
- Provide a chat-like UX with conversation history
- Surface system metrics (tokens, time, source quality) for transparency
- Validate the MVP with manual user-flow testing

## Pipeline Components

| Component | File | Status |
|---|---|---|
| Streamlit App | `src/ui/app.py` | ✅ Complete |
| RAG Pipeline (Phase 6) | `src/rag/pipeline.py` | ✅ Integrated |

## Architectural Decisions

### Streamlit over Flask/FastAPI

Selected for fastest time-to-MVP with zero JavaScript required.
Trade-offs accepted:
- Limited customization compared to dedicated frontend
- Single-threaded per session (acceptable for MVP scale)
- Re-runs full script per interaction (handled with caching)

### Caching Strategy

`@st.cache_resource` on `load_pipeline()` keeps the embedding model and
ChromaDB connection alive across interactions. Without this, each query
would take 10+ seconds just to initialize.

### Session State Management

Used `st.session_state` for conversation history. Includes:
- Full Q&A history with sources
- Pending query (for clickable examples)
- Implicit metrics aggregation

### UX for RAG-specific challenges

Addressed common RAG UX pitfalls:
- **Latency expectation:** spinner with descriptive text during search
- **Trust:** prominent source display with similarity color coding
- **Discoverability:** 4 example queries to guide first-time users
- **Transparency:** shows which episodes were searched even on misses

## Quality Validation

Manual testing across 5 user flows passed all checkpoints. See
[manual-test-checklist.md](./manual-test-checklist.md) for the complete
checklist.

Performance within targets:
- Cold start: ~25s (model loading)
- Query response: 1-15s (median ~5s)
- No memory issues observed in testing

## Configuration

| Parameter | Default | Where to configure |
|---|---|---|
| Page title | "{Podcast} Q&A" | `config/podcasts/{name}.py` |
| Welcome message | Portuguese | `src/ui/translations/{lang}.py` |
| Example queries | NerdCast topics | `config/podcasts/{name}.py` |
| Theme colors | Streamlit default | `.streamlit/config.toml` |

See [REPLICATION_GUIDE.md](../REPLICATION_GUIDE.md).

## Known Limitations

- **Top-K=5 limits scope:** Quantitative queries across many episodes
  underperform (e.g., "in how many episodes was Disney mentioned?")
- **Named entity searches:** Don't prioritize exact matches over semantic
  similarity, leading to weak results for proper noun queries
- **Streamlit limitations:** Limited visual customization compared to a
  dedicated frontend; single-threaded per session

These limitations are documented in the v2 backlog and don't block MVP delivery.

## Language Considerations

The interface itself is largely structural and works in any language.
What needs adaptation:

- **System prompt for the LLM:** language affects response quality
- **UI text strings:** title, captions, button labels, placeholder text
- **Example queries:** must reflect podcast content in the target language
- **Welcome message and help text:** should match the user's language

The Streamlit app loads UI strings based on the active podcast profile's
`LANGUAGE` setting.

## What This Enables

With Phase 7 complete, the project is **MVP-ready**:

- End users can ask questions without coding knowledge
- Developer or recruiter can run the demo locally
- Foundation for production deployment
- Material for portfolio demonstration

## Next Steps

The MVP is complete. Future improvements live in the v2 and v3 backlogs:

- Quality optimization based on identified limitations
- Production deployment to public URL
- Infrastructure migration (PostgreSQL, hosted vector DB)
- Advanced features (filters, exports, configuration UI)

## How to Run

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start the application
streamlit run src/ui/app.py

# Open browser at http://localhost:8501
```