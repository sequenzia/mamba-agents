# Observability

Pydantic Agent provides comprehensive observability through structured logging, tracing, and OpenTelemetry integration.

## Overview

The observability system includes:

- **Structured logging** - JSON and text formats with sensitive data redaction
- **Request tracing** - Track agent execution with spans
- **OpenTelemetry** - Export traces and metrics to external systems

## Logging

### Basic Setup

```python
from pydantic_agent.observability import setup_logging
from pydantic_agent.config import LoggingConfig

# Configure logging
config = LoggingConfig(
    level="INFO",
    format="json",  # or "text"
    redact_sensitive=True,
)

logger = setup_logging(config)
```

### Logging Formats

#### Text Format

```python
config = LoggingConfig(level="INFO", format="text")
# Output: 2024-01-15 10:30:00 INFO [agent] Starting agent run
```

#### JSON Format

```python
config = LoggingConfig(level="INFO", format="json")
# Output: {"timestamp": "2024-01-15T10:30:00", "level": "INFO", "module": "agent", "message": "Starting agent run"}
```

### Sensitive Data Redaction

API keys and secrets are automatically redacted:

```python
config = LoggingConfig(redact_sensitive=True)

# API keys are replaced with [REDACTED]
logger.info(f"Using API key: {api_key}")
# Output: Using API key: [REDACTED]
```

### Log Levels

| Level | Description |
|-------|-------------|
| DEBUG | Detailed debugging information |
| INFO | General operational messages |
| WARNING | Warning messages |
| ERROR | Error messages |
| CRITICAL | Critical failures |

### Configuration

```python
from pydantic_agent.config import LoggingConfig

config = LoggingConfig(
    level="INFO",
    format="json",
    redact_sensitive=True,
    include_timestamp=True,
    include_module=True,
)
```

Or via environment:

```bash
AGENTS_LOGGING__LEVEL=INFO
AGENTS_LOGGING__FORMAT=json
AGENTS_LOGGING__REDACT_SENSITIVE=true
```

## Request Tracing

### Basic Tracing

```python
from pydantic_agent.observability import RequestTracer

tracer = RequestTracer()

# Start a trace
tracer.start_trace()

# Create spans for operations
with tracer.start_span("agent.run") as span:
    span.set_attribute("prompt_length", len(prompt))
    result = await agent.run(prompt)
    span.set_attribute("output_length", len(result.output))

# End trace and get data
trace = tracer.end_trace()
print(f"Duration: {trace.duration_seconds}s")
```

### Nested Spans

```python
tracer.start_trace()

with tracer.start_span("workflow") as workflow_span:
    workflow_span.set_attribute("workflow_type", "react")

    with tracer.start_span("planning") as plan_span:
        plan_span.set_attribute("step", "plan")
        # Planning logic...

    with tracer.start_span("execution") as exec_span:
        exec_span.set_attribute("step", "execute")
        # Execution logic...

trace = tracer.end_trace()
```

### Span Attributes

```python
with tracer.start_span("api_call") as span:
    span.set_attribute("model", "gpt-4o")
    span.set_attribute("tokens", 1500)
    span.set_attribute("success", True)
    span.set_attribute("error", None)
```

### Accessing Trace Data

```python
trace = tracer.end_trace()

print(f"Trace ID: {trace.trace_id}")
print(f"Duration: {trace.duration_seconds}s")
print(f"Spans: {len(trace.spans)}")

for span in trace.spans:
    print(f"  {span.name}: {span.duration_ms}ms")
    for key, value in span.attributes.items():
        print(f"    {key}: {value}")
```

## OpenTelemetry Integration

### Installation

```bash
uv add pydantic-agent[otel]
# or
pip install pydantic-agent[otel]
```

### Basic Setup

```python
from pydantic_agent.observability import get_otel_integration

otel = get_otel_integration()

# Initialize with default settings
if otel.initialize():
    print("OpenTelemetry initialized")
```

### Tracing Agent Runs

```python
otel = get_otel_integration()
otel.initialize()

# Trace agent execution
with otel.trace_agent_run(prompt, model="gpt-4o") as span:
    result = await agent.run(prompt)
    span.set_attribute("tokens", result.usage().total_tokens)
```

### Custom Spans

```python
with otel.tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("custom_attribute", "value")
    # Your code here
```

### Exporting to Services

#### Jaeger

```python
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

otel = get_otel_integration()
otel.initialize()

# Add Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
otel.add_span_processor(BatchSpanProcessor(jaeger_exporter))
```

#### OTLP (Grafana, Honeycomb, etc.)

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

otel = get_otel_integration()
otel.initialize()

otlp_exporter = OTLPSpanExporter(
    endpoint="https://otlp.example.com:4317",
)
otel.add_span_processor(BatchSpanProcessor(otlp_exporter))
```

### Configuration

```python
from pydantic_agent.config import ObservabilityConfig

config = ObservabilityConfig(
    enable_tracing=True,
    enable_metrics=True,
    service_name="my-agent-service",
    service_version="1.0.0",
)
```

Or via environment:

```bash
AGENTS_OBSERVABILITY__ENABLE_TRACING=true
AGENTS_OBSERVABILITY__SERVICE_NAME=my-agent-service
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp.example.com:4317
```

## Combining All Features

```python
import asyncio
from pydantic_agent import Agent, AgentSettings
from pydantic_agent.observability import setup_logging, RequestTracer, get_otel_integration
from pydantic_agent.config import LoggingConfig

async def main():
    # Setup logging
    logging_config = LoggingConfig(level="INFO", format="json")
    logger = setup_logging(logging_config)

    # Setup OpenTelemetry
    otel = get_otel_integration()
    otel.initialize()

    # Setup request tracing
    tracer = RequestTracer()

    # Create agent
    agent = Agent("gpt-4o")

    # Execute with full observability
    tracer.start_trace()

    with otel.trace_agent_run("Hello", model="gpt-4o"):
        with tracer.start_span("agent.run") as span:
            result = await agent.run("Hello")
            span.set_attribute("tokens", result.usage().total_tokens)

    trace = tracer.end_trace()
    logger.info(f"Completed in {trace.duration_seconds}s")

asyncio.run(main())
```

## Configuration Reference

### LoggingConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `level` | str | `"INFO"` | Log level |
| `format` | str | `"text"` | Output format (`text`, `json`) |
| `redact_sensitive` | bool | `True` | Redact API keys |
| `include_timestamp` | bool | `True` | Include timestamps |
| `include_module` | bool | `True` | Include module names |

### ObservabilityConfig

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enable_tracing` | bool | `False` | Enable OpenTelemetry tracing |
| `enable_metrics` | bool | `False` | Enable OpenTelemetry metrics |
| `service_name` | str | `"pydantic-agent"` | Service name for traces |
| `service_version` | str | `"1.0.0"` | Service version |

## Best Practices

### 1. Use Structured Logging in Production

```python
config = LoggingConfig(
    level="INFO",
    format="json",  # Easy to parse by log aggregators
    redact_sensitive=True,
)
```

### 2. Add Context to Spans

```python
with tracer.start_span("operation") as span:
    span.set_attribute("user_id", user_id)
    span.set_attribute("request_id", request_id)
    span.set_attribute("model", model_name)
```

### 3. Monitor Key Metrics

```python
# Track in spans
span.set_attribute("tokens_used", usage.total_tokens)
span.set_attribute("cost_usd", cost)
span.set_attribute("latency_ms", latency)
```

## Next Steps

- [Error Handling](error-handling.md) - Handle and log errors
- [Logging API](../api/observability/logging.md) - Full reference
- [Tracing API](../api/observability/tracing.md) - Tracing reference
- [OpenTelemetry API](../api/observability/otel.md) - OTel reference
