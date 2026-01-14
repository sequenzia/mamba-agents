# Local LLM Setup

Configure and use local language models with Ollama, vLLM, or LM Studio.

## What You'll Learn

- Install and configure Ollama
- Set up vLLM for production use
- Configure LM Studio
- Troubleshoot common issues

## Prerequisites

- Python 3.12+
- Pydantic Agent installed
- Sufficient RAM (8GB+ recommended)
- GPU recommended for faster inference

## Option 1: Ollama (Recommended for Development)

### Step 1: Install Ollama

=== "macOS/Linux"

    ```bash
    curl -fsSL https://ollama.com/install.sh | sh
    ```

=== "Windows"

    Download from [ollama.com/download](https://ollama.com/download)

### Step 2: Start the Server

```bash
ollama serve
```

The server runs on `http://localhost:11434` by default.

### Step 3: Pull a Model

```bash
# Small, fast model (3B parameters)
ollama pull llama3.2

# Larger, more capable (8B parameters)
ollama pull llama3.1

# Code-focused model
ollama pull codellama

# List available models
ollama list
```

### Step 4: Configure Pydantic Agent

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
print(result.output)
```

Or via environment variables:

```bash
export AGENTS_MODEL_BACKEND__BASE_URL=http://localhost:11434/v1
export AGENTS_MODEL_BACKEND__MODEL=llama3.2
```

## Option 2: vLLM (Production)

### Step 1: Install vLLM

```bash
pip install vllm
```

### Step 2: Start the Server

```bash
vllm serve meta-llama/Llama-3.2-3B-Instruct \
    --port 8000 \
    --max-model-len 4096
```

### Step 3: Configure Pydantic Agent

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

### vLLM Production Options

```bash
# Multi-GPU setup
vllm serve meta-llama/Llama-3.2-70B-Instruct \
    --tensor-parallel-size 4 \
    --port 8000

# With authentication
vllm serve model-name \
    --api-key your-secret-key

# Memory optimization
vllm serve model-name \
    --gpu-memory-utilization 0.9 \
    --max-num-batched-tokens 4096
```

## Option 3: LM Studio

### Step 1: Install LM Studio

Download from [lmstudio.ai](https://lmstudio.ai)

### Step 2: Download a Model

1. Open LM Studio
2. Go to the "Discover" tab
3. Search for a model (e.g., "Llama 3.2")
4. Click "Download"

### Step 3: Start the Server

1. Go to "Local Server" tab
2. Select your downloaded model
3. Click "Start Server"
4. Note the port (default: 1234)

### Step 4: Configure Pydantic Agent

```python
from pydantic_agent import Agent, AgentSettings

settings = AgentSettings(
    model_backend={
        "base_url": "http://localhost:1234/v1",
        "model": "local-model",  # LM Studio uses loaded model
    }
)

agent = Agent(settings=settings)
```

## Configuration File

Create a `config.toml` for local development:

```toml
[model_backend]
base_url = "http://localhost:11434/v1"
model = "llama3.2"
temperature = 0.7
timeout = 60.0  # Local models can be slower

[logging]
level = "DEBUG"  # Helpful for debugging

[retry]
max_retries = 2
retry_level = 1  # Conservative for local
```

## Complete Example

```python
import asyncio
from pydantic_agent import Agent, AgentSettings, AgentConfig
from pydantic_agent.tools import read_file, run_bash


async def main():
    # Configure for local model
    settings = AgentSettings(
        model_backend={
            "base_url": "http://localhost:11434/v1",
            "model": "llama3.2",
            "temperature": 0.7,
            "timeout": 60.0,
        }
    )

    # Create agent
    agent = Agent(
        settings=settings,
        tools=[read_file, run_bash],
        config=AgentConfig(
            system_prompt="You are a helpful coding assistant.",
        ),
    )

    # Run query
    result = await agent.run("List files in the current directory")
    print(result.output)

    # Check usage (local models are free!)
    print(f"Tokens used: {agent.get_usage().total_tokens}")
    print(f"Cost: ${agent.get_cost():.4f}")  # Should be $0.00


if __name__ == "__main__":
    asyncio.run(main())
```

## Troubleshooting

### Connection Refused

```python
# Check if server is running
import httpx

try:
    response = httpx.get("http://localhost:11434/v1/models")
    print("Server is running")
    print(f"Models: {response.json()}")
except httpx.ConnectError:
    print("Server not running!")
    print("Start with: ollama serve")
```

### Model Not Found

```bash
# List available models
ollama list

# Pull missing model
ollama pull llama3.2
```

### Out of Memory

```bash
# Use a smaller model
ollama pull llama3.2:1b  # 1B parameters

# Or for vLLM, reduce memory usage
vllm serve model --gpu-memory-utilization 0.8
```

### Slow Responses

```python
# Increase timeout
settings = AgentSettings(
    model_backend={
        "timeout": 120.0,  # 2 minutes
    }
)

# Or use a smaller model
settings = AgentSettings(
    model_backend={
        "model": "llama3.2:1b",  # Faster, less capable
    }
)
```

### Tool Calling Not Working

Not all local models support tool calling. Check model capabilities:

```python
from pydantic_agent.backends import get_profile

profile = get_profile("llama3.2")
if not profile.supports_tools:
    print("This model doesn't support tool calling")
    print("Try: llama3.2:70b or use without tools")
```

## Performance Tips

1. **Use GPU** - Significantly faster than CPU
2. **Smaller models** - Faster inference, less RAM
3. **Increase timeout** - Local models are slower than API
4. **Batch requests** - vLLM handles batching well
5. **Quantized models** - Less RAM, similar quality

## Model Recommendations

| Use Case | Recommended Model | Size |
|----------|------------------|------|
| Quick testing | llama3.2:1b | 1B |
| Development | llama3.2 | 3B |
| Production | llama3.1:8b | 8B |
| Code tasks | codellama | 7B+ |
| Complex reasoning | llama3.2:70b | 70B |

## Next Steps

- [Model Backends Guide](../user-guide/model-backends.md) - More configuration options
- [Configuration](../getting-started/configuration.md) - Full config reference
- [Error Handling](../user-guide/error-handling.md) - Handle connection issues
