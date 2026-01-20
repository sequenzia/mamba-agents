"""Structured logging setup."""

from __future__ import annotations

import logging
import sys
from typing import Any, ClassVar

from mamba_agents.config.logging_config import LoggingConfig


class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from log messages."""

    SENSITIVE_PATTERNS: ClassVar[list[str]] = [
        "api_key",
        "api-key",
        "apikey",
        "secret",
        "password",
        "token",
        "authorization",
        "bearer",
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact sensitive data from log record."""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in msg_lower:
                    record.msg = self._redact_message(record.msg)
                    break
        return True

    def _redact_message(self, msg: str) -> str:
        """Redact sensitive values from a message."""
        import re

        for pattern in self.SENSITIVE_PATTERNS:
            regex = rf'({pattern}["\']?\s*[:=]\s*["\']?)([^"\'\s,}}]+)'
            msg = re.sub(regex, r"\1[REDACTED]", msg, flags=re.IGNORECASE)
        return msg


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured log messages."""

    def __init__(self, include_extras: bool = True) -> None:
        """Initialize the formatter.

        Args:
            include_extras: Whether to include extra fields.
        """
        super().__init__()
        self._include_extras = include_extras

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record.

        Args:
            record: Log record to format.

        Returns:
            Formatted log message.
        """
        base = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            base["exception"] = self.formatException(record.exc_info)

        if self._include_extras:
            extras = {
                k: v
                for k, v in record.__dict__.items()
                if k not in logging.LogRecord.__dict__
                and not k.startswith("_")
                and k not in ("message", "args", "msg")
            }
            if extras:
                base["extra"] = extras

        import json

        return json.dumps(base)


class AgentLogger:
    """Wrapper around logging.Logger with structured logging support."""

    def __init__(self, logger: logging.Logger) -> None:
        """Initialize the agent logger.

        Args:
            logger: Underlying logger.
        """
        self._logger = logger

    def debug(self, msg: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, msg, kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, msg, kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, msg, kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, msg, kwargs)

    def exception(self, msg: str, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log(logging.ERROR, msg, kwargs, exc_info=True)

    def _log(
        self,
        level: int,
        msg: str,
        extra: dict[str, Any],
        exc_info: bool = False,
    ) -> None:
        """Log a message with extra context."""
        self._logger.log(level, msg, extra=extra, exc_info=exc_info)


def setup_logging(
    config: LoggingConfig | None = None,
    name: str = "mamba_agents",
) -> AgentLogger:
    """Set up logging with the given configuration.

    Args:
        config: Logging configuration.
        name: Logger name.

    Returns:
        Configured AgentLogger instance.
    """
    if config is None:
        config = LoggingConfig()

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    if config.file:
        handler: logging.Handler = logging.FileHandler(config.file)
    else:
        handler = logging.StreamHandler(sys.stderr)

    handler.setLevel(getattr(logging, config.level.upper()))

    # Set formatter
    if config.format == "json":
        formatter: logging.Formatter = StructuredFormatter(include_extras=config.include_timestamps)
    else:
        fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        formatter = logging.Formatter(fmt)

    handler.setFormatter(formatter)

    # Add sensitive data filter if redaction is enabled
    if config.redact_sensitive:
        handler.addFilter(SensitiveDataFilter())

    logger.addHandler(handler)

    return AgentLogger(logger)
