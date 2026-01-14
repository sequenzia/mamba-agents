# MCPClientManager

Manage MCP server connections.

## Quick Example

```python
from pydantic_agent.mcp import MCPClientManager, MCPServerConfig

manager = MCPClientManager()

# Add server
manager.add_server(MCPServerConfig(
    name="server1",
    transport="stdio",
    command="my-server",
))

# Connect
await manager.connect_all()

# Get tools
toolsets = manager.get_toolsets()

# Check status
status = manager.get_status("server1")

# Disconnect
await manager.disconnect_all()
```

## Context Manager

```python
async with MCPClientManager(servers) as manager:
    toolsets = manager.get_toolsets()
    # Auto-connects and disconnects
```

## API Reference

::: pydantic_agent.mcp.client.MCPClientManager
    options:
      show_root_heading: true
      show_source: true
