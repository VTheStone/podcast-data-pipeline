# Environment Setup

## Python Version

Python 3.13 (system installed)

## Virtual Environment

Tool: venv (built-in)  
Activation (Windows): `.\venv\Scripts\Activate.ps1`

> **Note:** PowerShell requires execution policy adjustment before activating:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

## Dependencies

| File | Purpose |
|---|---|
| `requirements.txt` | Direct dependencies organized by phase |
| `requirements-lock.txt` | Full frozen environment for exact reproduction |

## Project Structure
podcast-data-pipeline/
├── data/
│   ├── raw/           # downloaded audio files
│   ├── metadata/      # episode catalog and logs
│   ├── transcripts/   # phase 2 output
│   └── chunks/        # phase 4 output
├── src/
│   ├── ingestion/     # phase 1
│   ├── transcription/ # phase 2
│   ├── processing/    # phase 4
│   └── rag/           # phase 6
├── docs/              # phase documentation
├── notebooks/         # exploratory analysis
└── tests/             # automated tests

## Known Issues

- Python 3.13 may have compatibility issues with some ML libraries (pyannote, faster-whisper)
- To be validated in Phase 2 before transcription setup