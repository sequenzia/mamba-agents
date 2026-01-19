# MCP Integration

Mamba Agents supports the Model Context Protocol (MCP) for connecting to external tool servers.

## Overview

MCP allows your agent to use tools provided by external servers:

- **Stdio transport** - Run MCP servers as subprocesses
- **SSE transport** - Connect to HTTP-based MCP servers
- **Authentication** - API key support for secure servers
- **Tool prefixing** - Avoid name conflicts between servers
- **File-based config** - Load from `.mcp.json` files (Claude Desktop compatible)

## Quick Start

```python
from mamba_agents import Agent
from mamba_agents.mcp import MCPServerConfig, MCPClientManager

# Configure MCP servers
configs = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/project"],
        tool_prefix="fs",  # Tools become: fs_read, fs_write, etc.
    ),
]

# Create manager and get toolsets
manager = MCPClientManager(configs)

# Pass toolsets to Agent (pydantic-ai handles server lifecycle)
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())

# Use the agent - MCP servers connect automatically
result = await agent.run("List files in the project")
```

## Loading from .mcp.json Files

Mamba Agents can load MCP server configurations from `.mcp.json` files, which is the standard format used by Claude Desktop, VS Code extensions, and other MCP tools.

### Basic Usage

```python
from mamba_agents import Agent
from mamba_agents.mcp import MCPClientManager

# Load all servers from .mcp.json
manager = MCPClientManager.from_mcp_json(".mcp.json")
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
```

### File Format

The `.mcp.json` file uses a standard format compatible with Claude Desktop:

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

### Extended Fields

Mamba Agents supports additional fields beyond the standard format:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "tool_prefix": "fs",
      "env_file": ".env.local"
    },
    "api-server": {
      "url": "http://localhost:8080/sse",
      "tool_prefix": "api"
    }
  }
}
```

| Field | Description |
|-------|-------------|
| `command` | Command to run (stdio transport) |
| `args` | Command arguments |
| `env` | Environment variables |
| `url` | Server URL (SSE transport) |
| `tool_prefix` | Prefix for tool names (mamba-agents extension) |
| `env_file` | Path to .env file (mamba-agents extension) |

### Loading Multiple Files

Merge configurations from multiple sources:

```python
from mamba_agents.mcp import MCPClientManager

# Start with project config
manager = MCPClientManager.from_mcp_json("project/.mcp.json")

# Add user defaults
manager.add_from_file("~/.mcp.json")

# Add team shared config
manager.add_from_file("/shared/team.mcp.json")

agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
```

### Combining with Programmatic Config

Mix file-based and programmatic configuration:

```python
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

# Start with file-based config
manager = MCPClientManager.from_mcp_json(".mcp.json")

# Add additional server programmatically
manager.add_server(MCPServerConfig(
    name="custom-server",
    transport="stdio",
    command="my-custom-server",
    tool_prefix="custom",
))

agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
```

### Error Handling

```python
from mamba_agents.mcp import (
    MCPClientManager,
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
)

try:
    manager = MCPClientManager.from_mcp_json(".mcp.json")
except MCPFileNotFoundError:
    print("Config file not found")
except MCPFileParseError as e:
    print(f"Invalid JSON: {e}")
except MCPServerValidationError as e:
    print(f"Invalid server config: {e}")
```

### Using load_mcp_json Directly

For more control, use the `load_mcp_json` function directly:

```python
from mamba_agents.mcp import load_mcp_json, MCPClientManager

# Load and inspect configs before creating manager
configs = load_mcp_json(".mcp.json")

# Filter or modify configs
filtered = [c for c in configs if c.name.startswith("prod-")]

manager = MCPClientManager(filtered)
```

## Transport Types

### Stdio Transport

Run MCP servers as subprocesses:

```python
MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
)

# Or with a local command
MCPServerConfig(
    name="custom",
    transport="stdio",
    command="python",
    args=["-m", "my_mcp_server"],
)
```

### SSE Transport

Connect to HTTP-based servers:

```python
MCPServerConfig(
    name="web-tools",
    transport="sse",
    url="http://localhost:8080/sse",
)
```

## Authentication

### API Key Authentication

```python
from mamba_agents.mcp import MCPServerConfig, MCPAuthConfig

MCPServerConfig(
    name="secure-server",
    transport="sse",
    url="https://api.example.com/mcp",
    auth=MCPAuthConfig(
        type="api_key",
        key="my-api-key",  # Direct key
        header="Authorization",  # Header name (default)
    ),
)
```

### Using Environment Variables

```python
MCPAuthConfig(
    type="api_key",
    key_env="MY_API_KEY",  # Read from env var
)

# Or with ${} syntax
MCPAuthConfig(
    type="api_key",
    key="${MY_API_KEY}",  # Expanded at runtime
)
```

## MCPClientManager

### Recommended Usage

```python
from mamba_agents import Agent
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

# Configure servers
configs = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/project"],
    ),
]

# Create manager
manager = MCPClientManager(configs)

# Get toolsets and pass to Agent
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())

# pydantic-ai handles MCP server lifecycle automatically
result = await agent.run("Use the MCP tools")
```

### Adding Servers Dynamically

```python
manager = MCPClientManager()

# Add servers one by one
manager.add_server(MCPServerConfig(
    name="server1",
    transport="stdio",
    command="my-server",
))

manager.add_server(MCPServerConfig(
    name="server2",
    transport="sse",
    url="http://localhost:8080/sse",
))

# Get all toolsets
toolsets = manager.as_toolsets()
agent = Agent("gpt-4o", toolsets=toolsets)
```

## Tool Prefixing

Avoid name conflicts with tool prefixes:

```python
MCPServerConfig(
    name="server1",
    transport="stdio",
    command="server1",
    tool_prefix="s1",  # Tools become: s1_read, s1_write, etc.
)

MCPServerConfig(
    name="server2",
    transport="stdio",
    command="server2",
    tool_prefix="s2",  # Tools become: s2_read, s2_write, etc.
)
```

## Common MCP Servers

### Filesystem Server

```python
MCPServerConfig(
    name="filesystem",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"],
    tool_prefix="fs",
)
```

### GitHub Server

```python
MCPServerConfig(
    name="github",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    auth=MCPAuthConfig(
        type="api_key",
        key_env="GITHUB_TOKEN",
    ),
    tool_prefix="gh",
)
```

### Brave Search Server

```python
MCPServerConfig(
    name="search",
    transport="stdio",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-brave-search"],
    auth=MCPAuthConfig(
        type="api_key",
        key_env="BRAVE_API_KEY",
    ),
    tool_prefix="search",
)
```

## Configuration Reference

### MCPServerConfig

| Option | Type | Description |
|--------|------|-------------|
| `name` | str | Unique server identifier |
| `transport` | str | `"stdio"` or `"sse"` |
| `command` | str | Command to run (stdio only) |
| `args` | list | Command arguments (stdio only) |
| `url` | str | Server URL (SSE only) |
| `auth` | MCPAuthConfig | Authentication config |
| `tool_prefix` | str | Prefix for tool names |

### MCPAuthConfig

| Option | Type | Description |
|--------|------|-------------|
| `type` | str | Auth type (`"api_key"`) |
| `key` | str | Direct API key |
| `key_env` | str | Environment variable name |
| `header` | str | HTTP header (default: `"Authorization"`) |

## Error Handling

### Configuration Errors

```python
from mamba_agents import Agent
from mamba_agents.mcp import (
    MCPClientManager,
    MCPServerConfig,
    MCPConfigError,
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
)

# File-based config errors
try:
    manager = MCPClientManager.from_mcp_json(".mcp.json")
except MCPFileNotFoundError:
    print("Config file not found")
except MCPFileParseError as e:
    print(f"Invalid JSON: {e}")
except MCPServerValidationError as e:
    print(f"Invalid server config: {e}")

# Programmatic config errors
configs = [
    MCPServerConfig(
        name="my-server",
        transport="stdio",
        command="my-mcp-server",
    ),
]

try:
    manager = MCPClientManager(configs)
    toolsets = manager.as_toolsets()
    agent = Agent("gpt-4o", toolsets=toolsets)
    result = await agent.run("Use the tools")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Runtime error: {e}")
```

### Error Hierarchy

| Exception | Description |
|-----------|-------------|
| `MCPConfigError` | Base exception for all MCP config errors |
| `MCPFileNotFoundError` | `.mcp.json` file not found |
| `MCPFileParseError` | Invalid JSON in config file |
| `MCPServerValidationError` | Invalid server entry in config |

## Best Practices

### 1. Use `as_toolsets()` (Recommended)

```python
# Good - pydantic-ai handles lifecycle
manager = MCPClientManager(configs)
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
result = await agent.run("Use tools")
```

### 2. Use Tool Prefixes

```python
# Prevent name conflicts between servers
server1 = MCPServerConfig(name="s1", tool_prefix="s1", ...)
server2 = MCPServerConfig(name="s2", tool_prefix="s2", ...)
```

### 3. Use Environment Variables for Secrets

```python
# Don't hardcode API keys
auth = MCPAuthConfig(key_env="MY_API_KEY")  # Good
auth = MCPAuthConfig(key="sk-...")  # Avoid in production
```

### 4. Validate Configurations Early

```python
# Check for configuration errors before runtime
manager = MCPClientManager(configs)
try:
    toolsets = manager.as_toolsets()
except ValueError as e:
    print(f"Invalid config: {e}")
```

## Next Steps

- [Model Backends](model-backends.md) - Connect to local models
- [MCPClientManager API](../api/mcp/client.md) - Full reference
- [MCPServerConfig API](../api/mcp/config.md) - Configuration reference
- [load_mcp_json API](../api/mcp/loader.md) - File loader reference
- [MCP Errors API](../api/mcp/errors.md) - Error classes reference
