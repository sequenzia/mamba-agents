# AgentConfig

Configuration options for agent behavior.

## Quick Example

```python
from mamba_agents import Agent, AgentConfig, CompactionConfig

config = AgentConfig(
    system_prompt="You are a helpful assistant.",
    max_iterations=15,
    track_context=True,
    auto_compact=True,
    context=CompactionConfig(
        strategy="hybrid",
        trigger_threshold_tokens=50000,
    ),
)

agent = Agent("gpt-4o", config=config)
```

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `system_prompt` | str | None | System prompt for the agent |
| `max_iterations` | int | 10 | Maximum tool-calling iterations |
| `track_context` | bool | True | Enable message tracking |
| `auto_compact` | bool | True | Auto-compact when threshold reached |
| `graceful_tool_errors` | bool | True | Convert tool exceptions to ModelRetry |
| `context` | CompactionConfig | None | Custom compaction settings |
| `tokenizer` | TokenizerConfig | None | Custom tokenizer settings |

## API Reference

::: mamba_agents.agent.config.AgentConfig
    options:
      show_root_heading: true
      show_source: true
