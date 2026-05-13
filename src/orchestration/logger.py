"""
Logging configuration for the orchestration pipeline.
Routes logs to both stdout and a timestamped file in logs/.
"""

import sys
from pathlib import Path
from datetime import datetime
from loguru import logger


def setup_logging() -> Path:
    """
    Configures loguru to log to both stdout and a timestamped file.

    Returns:
        Path to the log file created for this run.
    """
    # Remove default handler
    logger.remove()

    # Console output (human-readable, colored)
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )

    # File output (structured, full detail)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = Path("logs") / f"pipeline_{timestamp}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="100 MB",
        retention="30 days",
    )

    logger.info(f"Logging to: {log_path}")
    return log_path