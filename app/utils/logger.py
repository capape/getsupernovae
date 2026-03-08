"""Application logging helpers."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a module logger."""
    return logging.getLogger(name)


def setup_module_logger(
    name: str,
    level: int = logging.INFO,
    fmt: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"
) -> logging.Logger:
    """Set up and return a module logger with StreamHandler.
    
    Ensures the logger has a handler configured with the specified format.
    Only adds a handler if the logger doesn't already have one.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: INFO)
        fmt: Log message format string
    
    Returns:
        Configured Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def log_exception(logger: logging.Logger, message: str) -> None:
    """Log the current exception with traceback."""
    logger.exception(message)
