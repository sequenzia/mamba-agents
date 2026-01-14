# Installation

## Requirements

- Python 3.12 or later
- An API key for your model provider (or a local model server)

## Basic Installation

=== "uv (recommended)"

    ```bash
    uv add pydantic-agent
    ```

=== "pip"

    ```bash
    pip install pydantic-agent
    ```

=== "From source"

    ```bash
    git clone https://github.com/sequenzia/pydantic-agent.git
    cd pydantic-agent
    uv sync
    ```

## Optional Dependencies

### OpenTelemetry Support

For OpenTelemetry integration (tracing and metrics export):

=== "uv"

    ```bash
    uv add pydantic-agent[otel]
    ```

=== "pip"

    ```bash
    pip install pydantic-agent[otel]
    ```

This installs:

- `opentelemetry-api`
- `opentelemetry-sdk`

## Dependencies

Pydantic Agent automatically installs the following core dependencies:

| Package | Purpose |
|---------|---------|
| `pydantic-ai` | Core agent framework |
| `pydantic` | Data validation |
| `pydantic-settings` | Configuration management |
| `httpx` | HTTP client |
| `tenacity` | Retry logic |
| `tiktoken` | Token counting |
| `python-dotenv` | Environment variable loading |
| `pyyaml` | YAML configuration support |

## Verifying Installation

After installation, verify everything is working:

```python
from pydantic_agent import Agent, AgentSettings

# Check version
import pydantic_agent
print(f"Pydantic Agent version: {pydantic_agent.__version__}")

# Create a simple agent (requires OPENAI_API_KEY)
agent = Agent("gpt-4o")
result = agent.run_sync("Say hello!")
print(result.output)
```

## Development Installation

For contributing to Pydantic Agent:

```bash
# Clone the repository
git clone https://github.com/sequenzia/pydantic-agent.git
cd pydantic-agent

# Install with dev dependencies
uv sync --group dev

# Run tests
uv run pytest

# Run linting
uv run ruff check
uv run ruff format --check
```

## Documentation Development

To build and preview the documentation locally:

```bash
# Install docs dependencies
uv sync --group docs

# Serve docs locally
uv run mkdocs serve

# Build docs
uv run mkdocs build
```

## Next Steps

- [Quick Start](quickstart.md) - Create your first agent
- [Configuration](configuration.md) - Set up your environment
