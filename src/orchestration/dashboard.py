"""
Dashboard for pipeline orchestration status reporting.
Renders a visual snapshot of pipeline progress.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.ingestion.database import Episode, get_engine
from src.orchestration.phase_registry import PHASES, PhaseDefinition
from config import settings


PHASE_STATUS_PENDING = "⏸  Pending"
PHASE_STATUS_RUNNING = "🔄 Running"
PHASE_STATUS_COMPLETE = "✅ Complete"
PHASE_STATUS_FAILED = "❌ Failed"
PHASE_STATUS_SKIPPED = "⏭  Skipped"


def get_phase_counts(phase: PhaseDefinition) -> tuple[int, int]:
    """
    Returns (pending, done) counts for a phase.

    Pending = episodes meeting prerequisites but not completed
    Done = episodes that have completed this phase
    """
    engine = get_engine()
    with Session(engine) as session:
        # Count episodes that have completed prerequisites
        eligible_query = session.query(Episode)
        for required_flag in phase.requires_flags:
            eligible_query = eligible_query.filter(
                getattr(Episode, required_flag) == True
            )

        # Done: completed this phase
        done = eligible_query.filter(
            getattr(Episode, phase.completion_flag) == True
        ).count()

        # Pending: meets prerequisites but hasn't completed this phase
        pending = eligible_query.filter(
            getattr(Episode, phase.completion_flag) == False
        ).count()

    return pending, done


def determine_phase_status(
    phase: PhaseDefinition,
    pending: int,
    current_phase_id: int | None,
) -> str:
    """Determines the status emoji+text for a phase."""
    if pending == 0:
        return PHASE_STATUS_COMPLETE
    if current_phase_id == phase.id:
        return PHASE_STATUS_RUNNING
    if any(
        any(p.completion_flag == flag for p in PHASES)
        for flag in phase.requires_flags
    ):
        return PHASE_STATUS_PENDING
    return PHASE_STATUS_PENDING


def format_elapsed(start: datetime) -> str:
    """Formats elapsed time since start as HH:MM:SS."""
    delta = datetime.now() - start
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def render_dashboard(
    start_time: datetime,
    current_phase_id: int | None = None,
    failed_counts: dict[int, int] | None = None,
) -> str:
    """
    Renders the orchestration dashboard as a formatted string.

    Args:
        start_time: When the orchestration started.
        current_phase_id: ID of the currently executing phase, if any.
        failed_counts: Dict mapping phase_id to count of failed episodes.

    Returns:
        Multi-line string with the formatted dashboard.
    """
    failed_counts = failed_counts or {}

    lines = []
    lines.append("╔════════════════════════════════════════════════════════════════╗")
    lines.append("║              PIPELINE ORCHESTRATION STATUS                      ║")
    lines.append("╠════════════════════════════════════════════════════════════════╣")
    lines.append(f"║  Podcast: {settings.PODCAST_DISPLAY_NAME:<53}║")
    lines.append(f"║  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S'):<53}║")
    lines.append(f"║  Elapsed: {format_elapsed(start_time):<53}║")
    lines.append("╠════════════════════════════════════════════════════════════════╣")
    lines.append("║  Phase                       Pending    Done    Failed  Status      ║")

    for phase in PHASES:
        pending, done = get_phase_counts(phase)
        total = pending + done
        failed = failed_counts.get(phase.id, 0)
        status = determine_phase_status(phase, pending, current_phase_id)

        phase_label = f"{phase.id}. {phase.display_name}"
        pending_str = f"{pending}/{total}"

        lines.append(
            f"║  {phase_label:<27} {pending_str:>9}  {done:>5}    {failed:>5}   {status:<11}║"
        )

    lines.append("╚════════════════════════════════════════════════════════════════╝")

    return "\n".join(lines)


def print_dashboard(start_time: datetime, current_phase_id: int | None = None):
    """Prints the dashboard to stdout."""
    print()
    print(render_dashboard(start_time, current_phase_id))
    print()