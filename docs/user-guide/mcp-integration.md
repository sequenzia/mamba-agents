# MCP Integration

Pydantic Agent supports the Model Context Protocol (MCP) for connecting to external tool servers.

## Overview

MCP allows your agent to use tools provided by external servers:

- **Stdio transport** - Run MCP servers as subprocesses
- **SSE transport** - Connect to HTTP-based MCP servers
- **Authentication** - API key support for secure servers

## Quick Start

```python
from pydantic_agent import Agent
from pydantic_agent.mcp import MCPServerConfig, MCPClientManager

# Configure MCP servers
servers = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/project"],
    ),
]

# Connect and use
async with MCPClientManager(servers) as manager:
    toolsets = manager.get_toolsets()
    agent = Agent("gpt-4o", tools=toolsets)
    result = await agent.run("List files in the project")
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
from pydantic_agent.mcp import MCPServerConfig, MCPAuthConfig

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

### Basic Usage

```python
from pydantic_agent.mcp import MCPClientManager, MCPServerConfig

manager = MCPClientManager()

# Add servers
manager.add_server(MCPServerConfig(
    name="server1",
    transport="stdio",
    command="my-server",
))

# Connect to all servers
await manager.connect_all()

# Get tools for agent
toolsets = manager.get_toolsets()

# Disconnect when done
await manager.disconnect_all()
```

### Context Manager (Recommended)

```python
async with MCPClientManager(servers) as manager:
    toolsets = manager.get_toolsets()
    agent = Agent("gpt-4o", tools=toolsets)

    # Servers are automatically connected/disconnected
    result = await agent.run("Use the MCP tools")
```

### Server Status

```python
# Check individual server
status = manager.get_status("filesystem")
print(f"Connected: {status.connected}")
print(f"Tools: {status.tool_count}")

# Check all servers
all_statuses = manager.get_all_statuses()
for name, status in all_statuses.items():
    print(f"{name}: {status.connected}")
```

### Getting Specific Servers

```python
# Get a specific server
server = manager.get_server("filesystem")

# Use server-specific tools
tools = server.get_tools()
```

## Tool Prefixing

Avoid name conflicts with tool prefixes:

```python
MCPServerConfig(
    name="server1",
    transport="stdio",
    command="server1",
    tool_prefix="s1_",  # Tools become: s1_read, s1_write, etc.
)

MCPServerConfig(
    name="server2",
    transport="stdio",
    command="server2",
    tool_prefix="s2_",  # Tools become: s2_read, s2_write, etc.
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
| `url` | str | Server URL (sse only) |
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

```python
from pydantic_agent.mcp import MCPClientManager

try:
    async with MCPClientManager(servers) as manager:
        toolsets = manager.get_toolsets()
except ConnectionError as e:
    print(f"Failed to connect: {e}")
except TimeoutError as e:
    print(f"Connection timeout: {e}")
```

## Best Practices

### 1. Use Context Managers

```python
# Good - automatic cleanup
async with MCPClientManager(servers) as manager:
    ...

# Avoid - manual cleanup required
manager = MCPClientManager(servers)
await manager.connect_all()
try:
    ...
finally:
    await manager.disconnect_all()
```

### 2. Handle Server Failures

```python
statuses = manager.get_all_statuses()
failed = [name for name, s in statuses.items() if not s.connected]
if failed:
    logger.warning(f"Failed servers: {failed}")
```

### 3. Use Tool Prefixes

```python
# Prevent name conflicts between servers
server1 = MCPServerConfig(name="s1", tool_prefix="s1_", ...)
server2 = MCPServerConfig(name="s2", tool_prefix="s2_", ...)
```

## Next Steps

- [Model Backends](model-backends.md) - Connect to local models
- [MCPClientManager API](../api/mcp/client.md) - Full reference
- [MCPServerConfig API](../api/mcp/config.md) - Configuration reference
