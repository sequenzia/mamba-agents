# CompactionConfig

Configuration for context compaction.

## Quick Example

```python
from pydantic_agent import CompactionConfig

config = CompactionConfig(
    strategy="hybrid",
    trigger_threshold_tokens=100000,
    target_tokens=80000,
    preserve_recent_turns=10,
    preserve_system_prompt=True,
)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `strategy` | str | `"sliding_window"` | Compaction strategy |
| `trigger_threshold_tokens` | int | 100000 | Token count to trigger |
| `target_tokens` | int | 80000 | Target after compaction |
| `preserve_recent_turns` | int | 10 | Recent turns to keep |
| `preserve_system_prompt` | bool | True | Always keep system |
| `summarization_model` | str | `"same"` | Model for summaries |

## Available Strategies

- `sliding_window` - Remove oldest messages
- `summarize_older` - LLM summarization
- `selective_pruning` - Remove tool pairs
- `importance_scoring` - LLM scoring
- `hybrid` - Combine strategies

## API Reference

::: pydantic_agent.context.config.CompactionConfig
    options:
      show_root_heading: true
      show_source: true
