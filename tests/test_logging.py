import logging

from observability.logger.logging_config import InterceptHandler, setup_logging


def test_framework_loggers_are_forwarded_to_loguru(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_JSON", "false")

    setup_logging()

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        framework_logger = logging.getLogger(logger_name)
        assert len(framework_logger.handlers) == 1
        assert isinstance(framework_logger.handlers[0], InterceptHandler)
        assert framework_logger.propagate is False
