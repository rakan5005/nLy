"""Structured logging with file sinks for errors, results, and stats."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: str = LOG_DIR) -> None:
    os.makedirs(log_dir, exist_ok=True)

    root = logging.getLogger("by_nly")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt=DATE_FORMAT,
    )

    # Console handler (INFO+)
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(logging.WARNING)
    console.setFormatter(fmt)
    root.addHandler(console)

    # Error log
    error_fh = RotatingFileHandler(
        os.path.join(log_dir, "errors.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_fh.setLevel(logging.ERROR)
    error_fh.setFormatter(fmt)
    root.addHandler(error_fh)

    # Results log
    results_fh = RotatingFileHandler(
        os.path.join(log_dir, "results.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    results_fh.setLevel(logging.INFO)
    results_fh.setFormatter(fmt)
    root.addHandler(results_fh)

    # Stats log
    stats_fh = RotatingFileHandler(
        os.path.join(log_dir, "stats.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    stats_fh.setLevel(logging.DEBUG)
    stats_fh.setFormatter(fmt)
    root.addHandler(stats_fh)


def get_logger(name: str = "by_nly") -> logging.Logger:
    return logging.getLogger(name)


def log_result(
    logger: logging.Logger,
    platform: str,
    username: str,
    status: str,
    reason: str = "",
    response_time_ms: float = 0.0,
) -> None:
    msg = f"{platform:>10} | {status:>14} | {username}"
    if reason:
        msg += f" | {reason}"
    if response_time_ms:
        msg += f" | {response_time_ms:.0f}ms"
    logger.info(msg)


def log_stats(logger: logging.Logger, stats_text: str) -> None:
    logger.debug(f"Stats update:\n{stats_text}")
