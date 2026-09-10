import inspect
import logging
import os
import sys

from loguru import logger

LOG_FORMAT = (
    "<green>{time:DD-MM-YYYY HH:mm:ss.SSS}</green> "
    "<dim>|</dim> <level>{level: <8}</level> "
    "<dim>|</dim> <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "<dim>|</dim> <level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """Forward records from the standard library to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    """Configure one Loguru sink for application and framework logs."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    json_logs = os.getenv("LOG_JSON", "false").casefold() in {"1", "true", "yes", "on"}

    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format=LOG_FORMAT,
        colorize=None,
        serialize=json_logs,
        enqueue=True,
        backtrace=False,
        diagnose=False,
    )

    intercept_handler = InterceptHandler()
    logging.basicConfig(handlers=[intercept_handler], level=0, force=True)
    logging.captureWarnings(True)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        standard_logger = logging.getLogger(logger_name)
        standard_logger.handlers = [intercept_handler]
        standard_logger.propagate = False
