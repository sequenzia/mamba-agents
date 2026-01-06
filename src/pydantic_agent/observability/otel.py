"""OpenTelemetry integration hooks.

This module provides optional OpenTelemetry integration.
Requires opentelemetry-api and opentelemetry-sdk to be installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Generator


class SpanProtocol(Protocol):
    """Protocol for OpenTelemetry-like span."""

    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        ...

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add event to span."""
        ...

    def set_status(self, status: Any) -> None:
        """Set span status."""
        ...

    def end(self) -> None:
        """End the span."""
        ...


class TracerProtocol(Protocol):
    """Protocol for OpenTelemetry-like tracer."""

    def start_span(self, name: str, **kwargs: Any) -> SpanProtocol:
        """Start a new span."""
        ...


class NoOpSpan:
    """No-op span when OpenTelemetry is not available."""

    def set_attribute(self, key: str, value: Any) -> None:
        """No-op."""
        pass

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """No-op."""
        pass

    def set_status(self, status: Any) -> None:
        """No-op."""
        pass

    def end(self) -> None:
        """No-op."""
        pass

    def __enter__(self) -> NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class NoOpTracer:
    """No-op tracer when OpenTelemetry is not available."""

    def start_span(self, name: str, **kwargs: Any) -> NoOpSpan:
        """Return no-op span."""
        return NoOpSpan()


class OTelIntegration:
    """OpenTelemetry integration for the agent.

    Provides hooks for tracing agent operations when
    OpenTelemetry is available.
    """

    def __init__(self, service_name: str = "pydantic-agent") -> None:
        """Initialize OpenTelemetry integration.

        Args:
            service_name: Service name for tracing.
        """
        self._service_name = service_name
        self._tracer: TracerProtocol | NoOpTracer = NoOpTracer()
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize OpenTelemetry if available.

        Returns:
            True if OpenTelemetry was initialized.
        """
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider

            provider = TracerProvider()
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self._service_name)
            self._initialized = True
            return True
        except ImportError:
            self._initialized = False
            return False

    @property
    def is_initialized(self) -> bool:
        """Check if OpenTelemetry is initialized."""
        return self._initialized

    def trace_agent_run(
        self,
        prompt: str,
        model: str | None = None,
    ) -> Generator[SpanProtocol | NoOpSpan, None, None]:
        """Create a span for an agent run.

        Args:
            prompt: The user prompt.
            model: Model being used.

        Yields:
            Span for the agent run.
        """
        span = self._tracer.start_span("agent.run")
        try:
            span.set_attribute("agent.prompt_length", len(prompt))
            if model:
                span.set_attribute("agent.model", model)
            yield span
        finally:
            span.end()

    def trace_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any] | None = None,
    ) -> Generator[SpanProtocol | NoOpSpan, None, None]:
        """Create a span for a tool call.

        Args:
            tool_name: Name of the tool.
            args: Tool arguments.

        Yields:
            Span for the tool call.
        """
        span = self._tracer.start_span(f"tool.{tool_name}")
        try:
            span.set_attribute("tool.name", tool_name)
            if args:
                span.set_attribute("tool.arg_count", len(args))
            yield span
        finally:
            span.end()

    def trace_model_request(
        self,
        model: str,
        token_count: int | None = None,
    ) -> Generator[SpanProtocol | NoOpSpan, None, None]:
        """Create a span for a model request.

        Args:
            model: Model name.
            token_count: Input token count.

        Yields:
            Span for the model request.
        """
        span = self._tracer.start_span("model.request")
        try:
            span.set_attribute("model.name", model)
            if token_count:
                span.set_attribute("model.input_tokens", token_count)
            yield span
        finally:
            span.end()

    def record_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str | None = None,
    ) -> None:
        """Record token usage as metrics.

        Args:
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            model: Model used.
        """
        if not self._initialized:
            return

        try:
            from opentelemetry import metrics

            meter = metrics.get_meter(self._service_name)

            input_counter = meter.create_counter(
                "agent.tokens.input",
                description="Input tokens used",
            )
            output_counter = meter.create_counter(
                "agent.tokens.output",
                description="Output tokens used",
            )

            attributes = {"model": model} if model else {}
            input_counter.add(input_tokens, attributes)
            output_counter.add(output_tokens, attributes)
        except ImportError:
            pass


# Global instance
_otel_integration: OTelIntegration | None = None


def get_otel_integration() -> OTelIntegration:
    """Get the global OpenTelemetry integration.

    Returns:
        OTelIntegration instance.
    """
    global _otel_integration
    if _otel_integration is None:
        _otel_integration = OTelIntegration()
    return _otel_integration
