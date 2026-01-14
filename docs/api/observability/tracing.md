# Tracing

Request tracing utilities.

## Quick Example

```python
from pydantic_agent.observability import RequestTracer

tracer = RequestTracer()

# Start trace
tracer.start_trace()

# Create spans
with tracer.start_span("operation") as span:
    span.set_attribute("model", "gpt-4o")
    span.set_attribute("tokens", 1500)
    # Do work...

# Nested spans
with tracer.start_span("parent") as parent:
    with tracer.start_span("child") as child:
        child.set_attribute("step", 1)

# End trace
trace = tracer.end_trace()
print(f"Duration: {trace.duration_seconds}s")
```

## Trace Data

```python
trace = tracer.end_trace()

print(f"Trace ID: {trace.trace_id}")
print(f"Duration: {trace.duration_seconds}s")

for span in trace.spans:
    print(f"{span.name}: {span.duration_ms}ms")
    for key, value in span.attributes.items():
        print(f"  {key}: {value}")
```

## API Reference

::: pydantic_agent.observability.tracing.RequestTracer
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.observability.tracing.Span
    options:
      show_root_heading: true
