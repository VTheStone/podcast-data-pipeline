"""
Pipeline orchestrator — runs all phases in dependency order.

Idempotent: skips episodes that have already completed each phase.
Resilient: per-episode failures don't stop the pipeline.

Usage:
    python -m src.orchestration.run_pipeline
"""

from datetime import datetime
from loguru import logger

from src.orchestration.logger import setup_logging
from src.orchestration.dashboard import print_dashboard
from src.orchestration.phase_registry import PHASES, PhaseDefinition


def run_phase(phase: PhaseDefinition) -> dict:
    """
    Executes a single phase.

    Args:
        phase: The phase definition to run.

    Returns:
        Dict with execution metadata (start, end, status, error).
    """
    logger.info("=" * 70)
    logger.info(f"Phase {phase.id}: {phase.display_name}")
    logger.info("=" * 70)

    start = datetime.now()
    result = {
        "phase_id": phase.id,
        "phase_name": phase.name,
        "start": start,
        "end": None,
        "status": "running",
        "error": None,
    }

    try:
        phase.run_fn()
        result["status"] = "complete"
        logger.success(f"Phase {phase.id} ({phase.name}) completed successfully")
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"Phase {phase.id} ({phase.name}) failed: {e}")
        logger.exception(e)

    result["end"] = datetime.now()
    elapsed = (result["end"] - result["start"]).total_seconds()
    logger.info(f"Phase {phase.id} duration: {elapsed:.1f}s")

    return result


def run_pipeline():
    """
    Runs the complete pipeline in dependency order.
    Sequential execution — parallelization comes in M4.3.
    """
    log_path = setup_logging()

    start_time = datetime.now()
    logger.info("╔══════════════════════════════════════════════════════════════╗")
    logger.info("║              PIPELINE ORCHESTRATION STARTED                   ║")
    logger.info("╚══════════════════════════════════════════════════════════════╝")
    logger.info(f"Log file: {log_path}")

    # Initial dashboard
    print_dashboard(start_time)

    # Execute each phase in order
    results = []
    for phase in PHASES:
        print_dashboard(start_time, current_phase_id=phase.id)
        result = run_phase(phase)
        results.append(result)

        if result["status"] == "failed":
            logger.warning(
                f"Phase {phase.id} failed — continuing to next phase "
                "(per-episode failures are handled within each phase)"
            )

    # Final dashboard
    end_time = datetime.now()
    total_elapsed = (end_time - start_time).total_seconds()

    logger.info("=" * 70)
    logger.info("PIPELINE ORCHESTRATION SUMMARY")
    logger.info("=" * 70)

    for result in results:
        duration = (result["end"] - result["start"]).total_seconds()
        status_icon = "✅" if result["status"] == "complete" else "❌"
        logger.info(
            f"{status_icon} Phase {result['phase_id']} ({result['phase_name']}): "
            f"{result['status']} in {duration:.1f}s"
        )

    logger.info(f"Total elapsed: {total_elapsed:.1f}s ({total_elapsed/60:.1f} min)")
    print_dashboard(start_time)


if __name__ == "__main__":
    run_pipeline()