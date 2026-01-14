# ModelProfile

Model capability information.

## Quick Example

```python
from pydantic_agent.backends import get_profile, ModelProfile

# Get profile
profile = get_profile("gpt-4o")

print(f"Context window: {profile.context_window}")
print(f"Max output: {profile.max_output_tokens}")
print(f"Supports tools: {profile.supports_tools}")
print(f"Supports vision: {profile.supports_vision}")
print(f"Provider: {profile.provider}")
```

## Available Profiles

| Model | Context | Tools | Vision |
|-------|---------|-------|--------|
| gpt-4o | 128k | Yes | Yes |
| gpt-4o-mini | 128k | Yes | Yes |
| gpt-4-turbo | 128k | Yes | Yes |
| gpt-3.5-turbo | 16k | Yes | No |
| claude-3-5-sonnet | 200k | Yes | Yes |
| claude-3-opus | 200k | Yes | Yes |
| llama3.2 | 8k | No | No |

## API Reference

::: pydantic_agent.backends.profiles.ModelProfile
    options:
      show_root_heading: true

::: pydantic_agent.backends.profiles.get_profile
    options:
      show_root_heading: true
