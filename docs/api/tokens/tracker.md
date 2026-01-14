# UsageTracker

Track token usage across requests.

## Quick Example

```python
from pydantic_agent.tokens import UsageTracker

tracker = UsageTracker()

# Record usage
tracker.record_usage(
    prompt_tokens=100,
    completion_tokens=50,
    model="gpt-4o",
)

# Get aggregate
usage = tracker.get_total_usage()
print(f"Total: {usage.total_tokens}")

# Get history
for record in tracker.get_usage_history():
    print(f"{record.timestamp}: {record.total_tokens}")

# Reset
tracker.reset()
```

## Data Classes

### TokenUsage

Aggregate usage statistics.

### UsageRecord

Single usage record.

## API Reference

::: pydantic_agent.tokens.tracker.UsageTracker
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.tokens.tracker.TokenUsage
    options:
      show_root_heading: true

::: pydantic_agent.tokens.tracker.UsageRecord
    options:
      show_root_heading: true
