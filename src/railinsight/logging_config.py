"""Logging configuration for RailInsight.

Idempotent: safe to call multiple times. Streamlit re-executes the script on
every user interaction, so this guard prevents duplicate handlers accumulating.
"""

import logging
import logging.handlers

from railinsight.config import LOGS_DIR

_CONFIGURED = False


def setup_logging(level: int = logging.DEBUG) -> None:
    """Configure rotating file handlers: debug.log (all) and errors.log (ERROR+).

    Args:
        level: Minimum level for the root railinsight logger. Defaults to DEBUG.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("railinsight")
    if logger.handlers:
        # Already configured in this process (e.g., during testing).
        return
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    debug_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "debug.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.setFormatter(fmt)

    error_handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / "errors.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(fmt)

    logger.addHandler(debug_handler)
    logger.addHandler(error_handler)
