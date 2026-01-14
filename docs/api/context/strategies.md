# Compaction Strategies

The 5 available compaction strategies.

## Overview

| Strategy | Speed | LLM Calls | Best For |
|----------|-------|-----------|----------|
| `sliding_window` | Fast | None | Simple chats |
| `summarize_older` | Slow | Yes | Long research |
| `selective_pruning` | Fast | None | Tool-heavy |
| `importance_scoring` | Slow | Yes | Mixed content |
| `hybrid` | Medium | Maybe | General use |

## Usage

```python
from pydantic_agent import CompactionConfig

# Select strategy via config
config = CompactionConfig(strategy="sliding_window")
config = CompactionConfig(strategy="summarize_older")
config = CompactionConfig(strategy="selective_pruning")
config = CompactionConfig(strategy="importance_scoring")
config = CompactionConfig(strategy="hybrid")
```

## API Reference

::: pydantic_agent.context.compaction.SlidingWindowStrategy
    options:
      show_root_heading: true

::: pydantic_agent.context.compaction.SummarizeOlderStrategy
    options:
      show_root_heading: true

::: pydantic_agent.context.compaction.SelectivePruningStrategy
    options:
      show_root_heading: true

::: pydantic_agent.context.compaction.ImportanceScoringStrategy
    options:
      show_root_heading: true

::: pydantic_agent.context.compaction.HybridStrategy
    options:
      show_root_heading: true
