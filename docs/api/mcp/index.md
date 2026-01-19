# MCP Module

Model Context Protocol integration.

## Classes

| Class | Description |
|-------|-------------|
| [MCPClientManager](client.md) | Manage MCP server connections |
| [MCPServerConfig](config.md) | Server configuration |

## Functions

| Function | Description |
|----------|-------------|
| [load_mcp_json](loader.md) | Load configs from .mcp.json file |

## Exceptions

| Exception | Description |
|-----------|-------------|
| [MCPConfigError](errors.md) | Base MCP configuration error |
| [MCPFileNotFoundError](errors.md) | Config file not found |
| [MCPFileParseError](errors.md) | Invalid JSON in config |
| [MCPServerValidationError](errors.md) | Invalid server entry |

## Quick Example

```python
from mamba_agents import Agent
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

configs = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    ),
]

manager = MCPClientManager(configs)
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
result = await agent.run("List files")
```

## Loading from .mcp.json

```python
from mamba_agents.mcp import MCPClientManager

# Load from Claude Desktop compatible format
manager = MCPClientManager.from_mcp_json(".mcp.json")
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
```

## Imports

```python
from mamba_agents.mcp import (
    # Manager and config
    MCPClientManager,
    MCPServerConfig,
    MCPAuthConfig,
    # Loader
    load_mcp_json,
    # Exceptions
    MCPConfigError,
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
)
```
