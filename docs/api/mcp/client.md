# MCPClientManager

Manage MCP server connections.

## Quick Example

```python
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

manager = MCPClientManager()

# Add server
manager.add_server(MCPServerConfig(
    name="server1",
    transport="stdio",
    command="my-server",
))

# Get toolsets for agent
toolsets = manager.as_toolsets()
```

## With Agent

```python
from mamba_agents import Agent
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

configs = [
    MCPServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/project"],
    ),
]

manager = MCPClientManager(configs)
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
result = await agent.run("List project files")
```

## Loading from .mcp.json

Load configurations from `.mcp.json` files (Claude Desktop compatible format):

```python
from mamba_agents.mcp import MCPClientManager

# Create manager from file
manager = MCPClientManager.from_mcp_json(".mcp.json")
agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
```

### Merging Multiple Files

```python
# Start with project config
manager = MCPClientManager.from_mcp_json("project/.mcp.json")

# Add user defaults
manager.add_from_file("~/.mcp.json")
```

### Combining File and Programmatic Config

```python
from mamba_agents.mcp import MCPClientManager, MCPServerConfig

# Load from file
manager = MCPClientManager.from_mcp_json(".mcp.json")

# Add additional server
manager.add_server(MCPServerConfig(
    name="custom",
    transport="stdio",
    command="custom-server",
))
```

## Error Handling

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
    print(f"Invalid config: {e}")
```

## API Reference

::: mamba_agents.mcp.client.MCPClientManager
    options:
      show_root_heading: true
      show_source: true
