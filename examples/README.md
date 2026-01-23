# Mamba Agents Examples

Runnable examples demonstrating key features of the mamba-agents framework.

## Prerequisites

- Python 3.12+
- Install mamba-agents: `uv add mamba-agents` or `pip install mamba-agents`
- Set up API keys (see individual examples)

## Examples by Category

### Getting Started

| Example | Description |
|---------|-------------|
| [basic_agent.py](basic/basic_agent.py) | Simple agent creation and usage |
| [multi_turn.py](basic/multi_turn.py) | Multi-turn conversation with context |

### Tools

| Example | Description |
|---------|-------------|
| [builtin_tools.py](tools/builtin_tools.py) | Using built-in filesystem, glob, grep tools |
| [graceful_errors.py](tools/graceful_errors.py) | Tool error handling and recovery (v0.1.2+) |

### MCP Integration

| Example | Description |
|---------|-------------|
| [mcp_stdio.py](mcp/mcp_stdio.py) | Connect to stdio-based MCP servers |
| [mcp_http.py](mcp/mcp_http.py) | Connect via SSE and Streamable HTTP transports (v0.1.3+) |
| [mcp_connection_test.py](mcp/mcp_connection_test.py) | Test MCP server connections (v0.1.3+) |
| [mcp_from_file.py](mcp/mcp_from_file.py) | Load MCP config from .mcp.json files |

### Workflows

| Example | Description |
|---------|-------------|
| [react_basic.py](workflows/react_basic.py) | ReAct workflow for reasoning tasks |
| [workflow_hooks.py](workflows/workflow_hooks.py) | Observing workflow execution with hooks |

### Advanced

| Example | Description |
|---------|-------------|
| [context_compaction.py](advanced/context_compaction.py) | Managing long conversations |
| [prompt_templates.py](advanced/prompt_templates.py) | Jinja2 prompt management |
| [local_models.py](advanced/local_models.py) | Using Ollama, vLLM, LM Studio |
| [token_tracking.py](advanced/token_tracking.py) | Usage and cost estimation |

## Running Examples

```bash
# Set your API key
export OPENAI_API_KEY=sk-...

# Run an example
cd examples
python basic/basic_agent.py
```

## Further Reading

- [Documentation](https://sequenzia.github.io/mamba-agents) - Full documentation
- [README](../README.md) - Project overview
- [CHANGELOG](../CHANGELOG.md) - Version history
