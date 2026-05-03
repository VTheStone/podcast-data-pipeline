# {Phase Name} Setup

## Requirements

### Software

| Component | Version | Purpose |
|---|---|---|
| Python | 3.13 | Main language |
| {Lib} | X.Y | What it does |

### External Services

{If the phase requires accounts, API keys, or external services.}

- **Service Name** — What for, how to get access

### Hardware

{Recommended hardware specs and minimums.}

| Component | Minimum | Recommended | This project used |
|---|---|---|---|
| GPU | {x} | {y} | {z} |
| RAM | {x} | {y} | {z} |

## Installation

```bash
# Step-by-step installation
pip install ...
```

## Configuration

### Environment Variables

```env
VARIABLE_NAME=description
```

### Podcast-Specific Configuration

{What in this phase varies by podcast and where it lives.}

See `config/podcasts/{name}.py` for podcast-specific values.

## Validation

{How to verify the setup is working before running the pipeline.}

```bash
python tests/explore_{tool}.py
```

Expected output:

{Show what successful validation looks like}

## Decision Log

{If decisions were made during setup that affect future work, document here.
Format: Decision → Context → Options considered → Consequence.}

**Decision:** {What was decided}
**Context:** {Why this decision was needed}
**Options considered:**
- Option A — pros/cons
- Option B — pros/cons
**Outcome:** {What was chosen and why}

## Known Issues

{Setup-specific issues encountered and their resolutions or workarounds.}

## Language/Platform Considerations

{Anything specific that changes by OS, language, or environment.}