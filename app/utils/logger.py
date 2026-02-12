"""Application logging helpers."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)


def log_exception(logger: logging.Logger, message: str) -> None:
    """Log the current exception with traceback."""
    logger.exception(message)
