# Model Backends

Pydantic Agent supports local models through OpenAI-compatible APIs like Ollama, vLLM, and LM Studio.

## Overview

The backends module provides:

- **OpenAI-compatible adapter** - Connect to any OpenAI-compatible API
- **Factory functions** - Quick setup for popular providers
- **Model profiles** - Metadata about model capabilities

## Quick Start

### Ollama

```python
from pydantic_agent import Agent, AgentSettings

# Option 1: Via settings
settings = AgentSettings(
    model_backend={
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
    }
)
agent = Agent(settings=settings)

# Option 2: Via environment
# AGENTS_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
# AGENTS_MODEL_BACKEND__MODEL=llama3.2
```

### Using Backend Factories

```python
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
backend = create_lmstudio_backend()  # Uses default model
```

## Ollama Setup

### Installation

```bash
# macOS/Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start the server
ollama serve

# Pull a model
ollama pull llama3.2
```

### Usage

```python
from pydantic_agent import Agent, AgentSettings

settings = AgentSettings(
    model_backend={
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "temperature": 0.7,
    }
)

agent = Agent(settings=settings)
result = agent.run_sync("Hello!")
```

### Environment Configuration

```bash
AGENTS_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
AGENTS_MODEL_BACKEND__MODEL=llama3.2
```

## vLLM Setup

### Installation

```bash
pip install vllm

# Start the server
vllm serve meta-llama/Llama-3.2-3B-Instruct --port 8000
```

### Usage

```python
from pydantic_agent import Agent, AgentSettings

settings = AgentSettings(
    model_backend={
        "base_url": "http://localhost:8000/v1",
        "model": "meta-llama/Llama-3.2-3B-Instruct",
    }
)

agent = Agent(settings=settings)
```

## LM Studio Setup

### Installation

1. Download LM Studio from [lmstudio.ai](https://lmstudio.ai)
2. Download a model through the app
3. Start the local server (Settings > Local Server)

### Usage

```python
from pydantic_agent import Agent, AgentSettings

settings = AgentSettings(
    model_backend={
        "base_url": "http://localhost:1234/v1",
        "model": "local-model",  # LM Studio uses the loaded model
    }
)

agent = Agent(settings=settings)
```

## OpenAI-Compatible Backend

For custom or other OpenAI-compatible servers:

```python
from pydantic_agent.backends import OpenAICompatibleBackend

backend = OpenAICompatibleBackend(
    model="my-model",
    base_url="http://localhost:8000/v1",
    api_key="optional-key",
    temperature=0.7,
    max_tokens=4096,
)
```

## Model Profiles

Get information about model capabilities:

```python
from pydantic_agent.backends import get_profile, ModelProfile

# Get profile for a model
profile = get_profile("gpt-4o")

print(f"Context window: {profile.context_window}")
print(f"Max output: {profile.max_output_tokens}")
print(f"Supports tools: {profile.supports_tools}")
print(f"Supports vision: {profile.supports_vision}")
print(f"Provider: {profile.provider}")
```

### Available Profiles

| Model | Context | Tools | Vision |
|-------|---------|-------|--------|
| gpt-4o | 128k | Yes | Yes |
| gpt-4o-mini | 128k | Yes | Yes |
| gpt-4-turbo | 128k | Yes | Yes |
| gpt-3.5-turbo | 16k | Yes | No |
| claude-3-5-sonnet | 200k | Yes | Yes |
| claude-3-opus | 200k | Yes | Yes |
| llama3.2 | 8k | No | No |
| llama3.2:70b | 128k | Yes | No |

## Configuration Reference

### ModelBackendSettings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `model` | str | `"llama3.2"` | Model identifier |
| `base_url` | str | `"http://localhost:11434/v1"` | API endpoint |
| `api_key` | SecretStr | None | API key |
| `temperature` | float | 0.7 | Sampling temperature (0.0-2.0) |
| `max_tokens` | int | None | Max tokens to generate |
| `timeout` | float | 30.0 | Request timeout |
| `max_retries` | int | 3 | Retry attempts |

## Switching Between Providers

### Using Settings Override

```python
from pydantic_agent import Agent, AgentSettings

# Load base settings
settings = AgentSettings()

# Override for local development
local_settings = AgentSettings(
    model_backend={
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
    }
)

# Use appropriate settings
agent = Agent(settings=local_settings if is_dev else settings)
```

### Using Environment Variables

```bash
# Development (.env.local)
AGENTS_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
AGENTS_MODEL_BACKEND__MODEL=llama3.2

# Production (.env.prod)
AGENTS_MODEL_BACKEND__BASE_URL=https://api.openai.com/v1
AGENTS_MODEL_BACKEND__MODEL=gpt-4o
AGENTS_MODEL_BACKEND__API_KEY=sk-...
```

## Troubleshooting

### Connection Refused

```python
# Check if server is running
import httpx

try:
    response = httpx.get("http://localhost:11434/v1/models")
    print("Server is running")
except httpx.ConnectError:
    print("Server not running - start with 'ollama serve'")
```

### Model Not Found

```bash
# List available models (Ollama)
ollama list

# Pull missing model
ollama pull llama3.2
```

### Timeout Errors

```python
settings = AgentSettings(
    model_backend={
        "timeout": 60.0,  # Increase timeout
        "max_retries": 5,
    }
)
```

## Best Practices

### 1. Use Environment-Based Configuration

```python
import os

if os.getenv("ENV") == "development":
    settings = AgentSettings(model_backend={"model": "llama3.2"})
else:
    settings = AgentSettings()  # Uses production defaults
```

### 2. Handle Model Limitations

```python
from pydantic_agent.backends import get_profile

profile = get_profile(settings.model_backend.model)

if not profile.supports_tools:
    # Use a simpler approach without tools
    agent = Agent(model, tools=[])
```

### 3. Monitor Local Server Health

```python
async def check_server_health(base_url: str) -> bool:
    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{base_url}/models", timeout=5.0)
            return True
        except Exception:
            return False
```

## Next Steps

- [Error Handling](error-handling.md) - Handle connection failures
- [Local LLM Tutorial](../tutorials/local-llm-setup.md) - Step-by-step guide
- [ModelBackendSettings API](../api/config/model-backend.md) - Full reference
