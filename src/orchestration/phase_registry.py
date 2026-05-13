"""
Phase registry — declarative definition of pipeline phases.

Each phase has:
- A name and display name
- A reference to its run function
- The episode flag it sets on completion
- The flags it requires to be True before running
- A flag for whether it uses GPU (for resource management)
"""

from dataclasses import dataclass, field
from typing import Callable

from src.ingestion import feed_parser, downloader
from src.transcription import transcriber, diarizer, aligner, speaker_enrollment
from src.processing import chunker, indexer


@dataclass
class PhaseDefinition:
    """Definition of a single pipeline phase."""
    id: int
    name: str
    display_name: str
    run_fn: Callable
    completion_flag: str            # Flag to check/set on episodes table
    requires_flags: list[str] = field(default_factory=list)
    uses_gpu: bool = False
    sub_phases: list[Callable] = field(default_factory=list)


# Phase 1: Ingestion (download)
# Note: feed parsing happens first, then downloading.
# Both write to the episodes table.
def _run_ingestion(max_episodes=None):
    """Runs feed parsing followed by audio download."""
    feed_parser.run()
    downloader.run(max_episodes=max_episodes)


# Phase 3: Diarization with all sub-pipelines in sequence
def _run_diarization(max_episodes=None):
    """Runs diarization, alignment, and speaker enrollment in sequence."""
    diarizer.run(max_episodes=max_episodes)
    aligner.run(max_episodes=max_episodes)
    speaker_enrollment.run(max_episodes=max_episodes)


PHASES: list[PhaseDefinition] = [
    PhaseDefinition(
        id=1,
        name="ingestion",
        display_name="Data Collection",
        run_fn=_run_ingestion,
        completion_flag="downloaded",
        requires_flags=[],
        uses_gpu=False,
    ),
    PhaseDefinition(
        id=2,
        name="transcription",
        display_name="Transcription",
        run_fn=transcriber.run,
        completion_flag="transcribed",
        requires_flags=["downloaded"],
        uses_gpu=True,
    ),
    PhaseDefinition(
        id=3,
        name="diarization",
        display_name="Diarization & Enrollment",
        run_fn=_run_diarization,
        completion_flag="diarized",
        requires_flags=["transcribed"],
        uses_gpu=True,
    ),
    PhaseDefinition(
        id=4,
        name="chunking",
        display_name="Chunking",
        run_fn=chunker.run,
        completion_flag="chunked",
        requires_flags=["transcribed", "diarized"],
        uses_gpu=False,
    ),
    PhaseDefinition(
        id=5,
        name="indexing",
        display_name="Vector Indexing",
        run_fn=indexer.run,
        completion_flag="indexed",
        requires_flags=["chunked"],
        uses_gpu=True,
    ),
]


def get_phase_by_id(phase_id: int) -> PhaseDefinition:
    """Returns the phase definition for a given ID."""
    for phase in PHASES:
        if phase.id == phase_id:
            return phase
    raise ValueError(f"Phase {phase_id} not found")


def get_phases_by_ids(phase_ids: list[int]) -> list[PhaseDefinition]:
    """Returns phase definitions for given IDs, in order."""
    return [get_phase_by_id(pid) for pid in sorted(phase_ids)]