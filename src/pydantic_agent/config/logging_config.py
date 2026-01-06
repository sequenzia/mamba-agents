"""Logging configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class LoggingConfig(BaseModel):
    """Configuration for logging behavior.

    Supports structured JSON logging, request/response body logging,
    and automatic redaction of sensitive data.

    Attributes:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        structured: Enable JSON format logging.
        include_request_body: Log request bodies (opt-in for privacy).
        include_response_body: Log response bodies (opt-in for privacy).
        body_size_limit: Maximum bytes to log for bodies.
        include_correlation_id: Include correlation IDs in logs.
        redact_authorization: Redact Authorization headers.
        redact_api_keys: Redact API keys in query params.
        sensitive_patterns: Custom regex patterns to redact.
    """

    level: LogLevel = Field(
        default="INFO",
        description="Log level",
    )
    structured: bool = Field(
        default=False,
        description="Enable JSON format logging",
    )
    include_request_body: bool = Field(
        default=False,
        description="Log request bodies",
    )
    include_response_body: bool = Field(
        default=False,
        description="Log response bodies",
    )
    body_size_limit: int = Field(
        default=1024,
        gt=0,
        description="Maximum bytes to log for bodies",
    )
    include_correlation_id: bool = Field(
        default=True,
        description="Include correlation IDs in logs",
    )
    redact_authorization: bool = Field(
        default=True,
        description="Redact Authorization headers",
    )
    redact_api_keys: bool = Field(
        default=True,
        description="Redact API keys in query params",
    )
    sensitive_patterns: list[str] = Field(
        default_factory=list,
        description="Custom regex patterns to redact",
    )
