# MCP Module

Model Context Protocol integration.

## Classes

| Class | Description |
|-------|-------------|
| [MCPClientManager](client.md) | Manage MCP server connections |
| [MCPServerConfig](config.md) | Server configuration |

## Quick Example

```python
from pydantic_agent import Agent
from pydantic_agent.mcp import MCPClientManager, MCPServerConfig

servers = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    ),
]

async with MCPClientManager(servers) as manager:
    toolsets = manager.get_toolsets()
    agent = Agent("gpt-4o", tools=toolsets)
```

## Imports

```python
from pydantic_agent.mcp import MCPClientManager, MCPServerConfig, MCPAuthConfig
```
