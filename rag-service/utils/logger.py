"""
NyayaSetu RAG Service — Logging configuration.

Provides a pre-configured logger with a clean, readable format.
Import `get_logger(__name__)` in any module to get a child logger.
"""

import logging
import sys


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger for the application.

    Call once at startup (in main.py). All child loggers created via
    `get_logger` inherit this configuration automatically.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=numeric_level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Usage::

        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Something happened")
    """
    return logging.getLogger(name)
