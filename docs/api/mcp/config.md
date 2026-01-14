# MCPServerConfig

Configuration for MCP servers.

## Quick Example

```python
from pydantic_agent.mcp import MCPServerConfig, MCPAuthConfig

# Stdio transport
config = MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
)

# SSE transport with auth
config = MCPServerConfig(
    name="api",
    transport="sse",
    url="http://localhost:8080/sse",
    auth=MCPAuthConfig(
        type="api_key",
        key_env="API_KEY",
    ),
)
```

## Configuration Options

### MCPServerConfig

| Option | Type | Description |
|--------|------|-------------|
| `name` | str | Unique server name |
| `transport` | str | `"stdio"` or `"sse"` |
| `command` | str | Command (stdio) |
| `args` | list | Arguments (stdio) |
| `url` | str | Server URL (sse) |
| `auth` | MCPAuthConfig | Authentication |
| `tool_prefix` | str | Prefix for tools |

### MCPAuthConfig

| Option | Type | Description |
|--------|------|-------------|
| `type` | str | `"api_key"` |
| `key` | str | Direct key |
| `key_env` | str | Env var name |
| `header` | str | HTTP header |

## API Reference

::: pydantic_agent.mcp.config.MCPServerConfig
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.mcp.config.MCPAuthConfig
    options:
      show_root_heading: true
