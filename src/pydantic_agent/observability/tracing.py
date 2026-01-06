"""Request tracing and context propagation."""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any


# Context variable for request tracking
_current_trace: ContextVar[TraceContext | None] = ContextVar(
    "current_trace", default=None
)


@dataclass
class SpanData:
    """Data for a single span within a trace."""

    name: str
    span_id: str
    parent_id: str | None
    start_time: float
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    error: str | None = None

    @property
    def duration_ms(self) -> float | None:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


@dataclass
class TraceContext:
    """Context for a single trace/request."""

    trace_id: str
    spans: list[SpanData] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None

    @property
    def duration_ms(self) -> float | None:
        """Get total trace duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


class Span:
    """A span representing a unit of work within a trace."""

    def __init__(
        self,
        tracer: RequestTracer,
        name: str,
        parent_id: str | None = None,
    ) -> None:
        """Initialize the span.

        Args:
            tracer: Parent tracer.
            name: Span name.
            parent_id: Parent span ID if nested.
        """
        self._tracer = tracer
        self._data = SpanData(
            name=name,
            span_id=uuid.uuid4().hex[:16],
            parent_id=parent_id,
            start_time=time.time(),
        )

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self._data.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span."""
        self._data.events.append(
            {
                "name": name,
                "timestamp": time.time(),
                "attributes": attributes or {},
            }
        )

    def set_error(self, error: str) -> None:
        """Mark span as errored."""
        self._data.status = "error"
        self._data.error = error

    def end(self) -> None:
        """End the span."""
        self._data.end_time = time.time()
        self._tracer._add_span(self._data)

    def __enter__(self) -> Span:
        """Enter span context."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit span context."""
        if exc_val is not None:
            self.set_error(str(exc_val))
        self.end()


class RequestTracer:
    """Tracer for tracking requests through the agent."""

    def __init__(self, service_name: str = "pydantic-agent") -> None:
        """Initialize the tracer.

        Args:
            service_name: Name of the service being traced.
        """
        self._service_name = service_name
        self._context: TraceContext | None = None
        self._current_span_id: str | None = None

    @property
    def trace_id(self) -> str | None:
        """Get current trace ID."""
        return self._context.trace_id if self._context else None

    @property
    def current_span_id(self) -> str | None:
        """Get current span ID."""
        return self._current_span_id

    def start_trace(self, attributes: dict[str, Any] | None = None) -> TraceContext:
        """Start a new trace.

        Args:
            attributes: Initial trace attributes.

        Returns:
            New TraceContext.
        """
        self._context = TraceContext(
            trace_id=uuid.uuid4().hex,
            attributes=attributes or {},
        )
        _current_trace.set(self._context)
        return self._context

    def end_trace(self) -> TraceContext | None:
        """End the current trace.

        Returns:
            Completed TraceContext or None.
        """
        if self._context:
            self._context.end_time = time.time()
            ctx = self._context
            self._context = None
            self._current_span_id = None
            _current_trace.set(None)
            return ctx
        return None

    def start_span(self, name: str) -> Span:
        """Start a new span.

        Args:
            name: Span name.

        Returns:
            New Span.
        """
        if self._context is None:
            self.start_trace()

        span = Span(self, name, parent_id=self._current_span_id)
        self._current_span_id = span._data.span_id
        return span

    def _add_span(self, span_data: SpanData) -> None:
        """Add completed span to trace."""
        if self._context:
            self._context.spans.append(span_data)
            # Reset current span to parent
            self._current_span_id = span_data.parent_id

    def get_trace_context(self) -> TraceContext | None:
        """Get current trace context."""
        return self._context

    def get_trace_header(self) -> dict[str, str]:
        """Get trace context as headers for propagation.

        Returns:
            Dictionary with traceparent header.
        """
        if not self._context:
            return {}

        span_id = self._current_span_id or "0000000000000000"
        traceparent = f"00-{self._context.trace_id}-{span_id}-01"
        return {"traceparent": traceparent}

    @classmethod
    def from_header(cls, traceparent: str) -> RequestTracer:
        """Create tracer from incoming traceparent header.

        Args:
            traceparent: W3C traceparent header value.

        Returns:
            RequestTracer with context restored.
        """
        tracer = cls()

        try:
            parts = traceparent.split("-")
            if len(parts) >= 3:
                trace_id = parts[1]
                parent_span_id = parts[2]

                tracer._context = TraceContext(trace_id=trace_id)
                tracer._current_span_id = parent_span_id
                _current_trace.set(tracer._context)
        except (ValueError, IndexError):
            pass

        return tracer


def get_current_trace() -> TraceContext | None:
    """Get the current trace context.

    Returns:
        Current TraceContext or None.
    """
    return _current_trace.get()
