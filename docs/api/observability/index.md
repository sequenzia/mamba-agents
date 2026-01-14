# Observability Module

Logging, tracing, and OpenTelemetry integration.

## Classes

| Class | Description |
|-------|-------------|
| [Logging](logging.md) | Structured logging |
| [Tracing](tracing.md) | Request tracing |
| [OpenTelemetry](otel.md) | OTel integration |

## Quick Example

```python
from pydantic_agent.observability import (
    setup_logging,
    RequestTracer,
    get_otel_integration,
)
from pydantic_agent.config import LoggingConfig

# Setup logging
config = LoggingConfig(level="INFO", format="json")
logger = setup_logging(config)

# Request tracing
tracer = RequestTracer()
tracer.start_trace()
with tracer.start_span("operation") as span:
    span.set_attribute("key", "value")
trace = tracer.end_trace()

# OpenTelemetry
otel = get_otel_integration()
otel.initialize()
```

## Imports

```python
from pydantic_agent.observability import (
    setup_logging,
    AgentLogger,
    RequestTracer,
    get_otel_integration,
    OTelIntegration,
)
```
