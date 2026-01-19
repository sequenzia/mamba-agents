# load_mcp_json

Load MCP server configurations from `.mcp.json` files.

## Quick Example

```python
from mamba_agents.mcp import load_mcp_json, MCPClientManager

# Load configs from file
configs = load_mcp_json(".mcp.json")

# Use with manager
manager = MCPClientManager(configs)
```

## File Format

The `.mcp.json` format is compatible with Claude Desktop:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/project"],
      "env": {"NODE_ENV": "production"}
    },
    "web-search": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

## Field Mapping

| .mcp.json Field | MCPServerConfig Field |
|-----------------|----------------------|
| (object key) | `name` |
| `command` | `command` |
| `args` | `args` |
| `env` | `env_vars` |
| `url` | `url` |
| `tool_prefix` | `tool_prefix` |
| `env_file` | `env_file` |

Transport is auto-detected: `url` present → SSE, `command` present → stdio.

## Extended Fields

Mamba-agents extends the standard format with:

- `tool_prefix` - Prefix for tool names from this server
- `env_file` - Path to .env file for environment variables

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "tool_prefix": "fs",
      "env_file": ".env.local"
    }
  }
}
```

## Error Handling

```python
from mamba_agents.mcp import (
    load_mcp_json,
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
)

try:
    configs = load_mcp_json(".mcp.json")
except MCPFileNotFoundError:
    print("File not found")
except MCPFileParseError as e:
    print(f"Invalid JSON: {e}")
except MCPServerValidationError as e:
    print(f"Invalid server config: {e}")
```

## Path Expansion

The function supports `~` expansion for home directory:

```python
# Both work
configs = load_mcp_json("~/.mcp.json")
configs = load_mcp_json("/home/user/.mcp.json")
```

## API Reference

::: mamba_agents.mcp.loader.load_mcp_json
    options:
      show_root_heading: true
      show_source: true
