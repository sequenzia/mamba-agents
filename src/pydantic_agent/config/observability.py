"""Observability configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RequestIdFormat = Literal["uuid4", "ulid"]


class ObservabilityConfig(BaseModel):
    """Configuration for observability features.

    Controls request ID generation, trace context propagation,
    and OpenTelemetry integration.

    Attributes:
        request_id_format: Format for generated request IDs.
        propagate_trace_context: Propagate trace headers.
        enable_otel_instrumentation: Enable OpenTelemetry hooks.
        metrics_enabled: Expose duration metrics.
    """

    request_id_format: RequestIdFormat = Field(
        default="uuid4",
        description="Format for request ID generation (uuid4 or ulid)",
    )
    propagate_trace_context: bool = Field(
        default=True,
        description="Propagate trace context headers",
    )
    enable_otel_instrumentation: bool = Field(
        default=False,
        description="Enable OpenTelemetry instrumentation",
    )
    metrics_enabled: bool = Field(
        default=True,
        description="Enable metrics collection",
    )
