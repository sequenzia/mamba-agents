"""Logging and observability.

This module provides logging utilities and experimental observability features.

Stable exports (recommended for production use):
- AgentLogger, SensitiveDataFilter, StructuredFormatter, setup_logging

Experimental exports (API may change):
- RequestTracer, Span, SpanData, TraceContext, get_current_trace
- OTelIntegration, get_otel_integration
"""

from mamba_agents.observability.logging import (
    AgentLogger,
    SensitiveDataFilter,
    StructuredFormatter,
    setup_logging,
)

# Experimental: OpenTelemetry integration (requires additional setup)
from mamba_agents.observability.otel import OTelIntegration, get_otel_integration

# Experimental: Custom tracing (not integrated into core agent loop)
from mamba_agents.observability.tracing import (
    RequestTracer,
    Span,
    SpanData,
    TraceContext,
    get_current_trace,
)

__all__ = [
    "AgentLogger",
    "OTelIntegration",
    "RequestTracer",
    "SensitiveDataFilter",
    "Span",
    "SpanData",
    "StructuredFormatter",
    "TraceContext",
    "get_current_trace",
    "get_otel_integration",
    "setup_logging",
]
