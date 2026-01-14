# Backends Module

Model backend adapters for OpenAI-compatible APIs.

## Classes

| Class | Description |
|-------|-------------|
| [OpenAICompatibleBackend](openai-compat.md) | Base backend class |
| [ModelProfile](profiles.md) | Model capability info |

## Quick Example

```python
from pydantic_agent.backends import (
    create_ollama_backend,
    create_vllm_backend,
    create_lmstudio_backend,
    get_profile,
)

# Factory functions
backend = create_ollama_backend("llama3.2")
backend = create_vllm_backend("meta-llama/Llama-3.2-3B-Instruct")
backend = create_lmstudio_backend()

# Get model info
profile = get_profile("gpt-4o")
print(f"Context: {profile.context_window}")
```

## Imports

```python
from pydantic_agent.backends import (
    OpenAICompatibleBackend,
    create_ollama_backend,
    create_vllm_backend,
    create_lmstudio_backend,
    get_profile,
    ModelProfile,
)
```
