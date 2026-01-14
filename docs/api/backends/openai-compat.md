# OpenAICompatibleBackend

Backend adapter for OpenAI-compatible APIs.

## Quick Example

```python
from pydantic_agent.backends import OpenAICompatibleBackend

# Direct instantiation
backend = OpenAICompatibleBackend(
    model="my-model",
    base_url="http://localhost:8000/v1",
    api_key="optional-key",
)

# Or use factory functions
from pydantic_agent.backends import (
    create_ollama_backend,
    create_vllm_backend,
    create_lmstudio_backend,
)

# Ollama
backend = create_ollama_backend("llama3.2")

# vLLM
backend = create_vllm_backend("meta-llama/Llama-3.2-3B-Instruct")

# LM Studio
backend = create_lmstudio_backend()
```

## Factory Functions

| Function | Default URL | Description |
|----------|-------------|-------------|
| `create_ollama_backend` | `localhost:11434` | Ollama |
| `create_vllm_backend` | `localhost:8000` | vLLM |
| `create_lmstudio_backend` | `localhost:1234` | LM Studio |

## API Reference

::: pydantic_agent.backends.openai_compat.OpenAICompatibleBackend
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.backends.openai_compat.create_ollama_backend
    options:
      show_root_heading: true

::: pydantic_agent.backends.openai_compat.create_vllm_backend
    options:
      show_root_heading: true

::: pydantic_agent.backends.openai_compat.create_lmstudio_backend
    options:
      show_root_heading: true
