"""MCP (Model Context Protocol) integration.

This module provides support for connecting to MCP servers that expose tools
for AI agents. Supports three transport types:

- **stdio**: Run MCP servers as subprocesses
- **sse**: Connect via Server-Sent Events (HTTP)
- **streamable_http**: Modern HTTP transport (v0.1.3+)

Quick Start:
    >>> from mamba_agents import Agent
    >>> from mamba_agents.mcp import MCPClientManager, MCPServerConfig
    >>>
    >>> configs = [
    ...     MCPServerConfig(
    ...         name="filesystem",
    ...         transport="stdio",
    ...         command="npx",
    ...         args=["-y", "@modelcontextprotocol/server-filesystem", "/project"],
    ...     ),
    ... ]
    >>> manager = MCPClientManager(configs)
    >>> agent = Agent("gpt-4o", toolsets=manager.as_toolsets())

Loading from .mcp.json:
    >>> manager = MCPClientManager.from_mcp_json(".mcp.json")
    >>> agent = Agent("gpt-4o", toolsets=manager.as_toolsets())

Connection Testing (v0.1.3+):
    >>> result = await manager.test_connection("filesystem")
    >>> if result.success:
    ...     print(f"Tools available: {result.tool_count}")

Streamable HTTP Transport (v0.1.3+):
    >>> config = MCPServerConfig(
    ...     name="api",
    ...     transport="streamable_http",
    ...     url="http://localhost:8080/mcp",
    ... )

Classes:
    MCPClientManager: Manages MCP server configurations and connections
    MCPServerConfig: Configuration for an MCP server
    MCPAuthConfig: Authentication configuration (API keys)
    MCPConnectionResult: Result of connection testing
    MCPToolInfo: Information about an available tool

Exceptions:
    MCPConfigError: Base exception for configuration errors
    MCPConnectionError: Server connection failures
    MCPConnectionTimeoutError: Connection timeout
    MCPServerNotFoundError: Server not found in manager

See Also:
    - examples/mcp/ for runnable examples
    - docs/user-guide/mcp-integration.md for detailed guide
"""

from mamba_agents.mcp.client import MCPClientManager, MCPConnectionResult, MCPToolInfo
from mamba_agents.mcp.config import MCPAuthConfig, MCPServerConfig
from mamba_agents.mcp.errors import (
    MCPConfigError,
    MCPConnectionError,
    MCPConnectionTimeoutError,
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerNotFoundError,
    MCPServerValidationError,
)
from mamba_agents.mcp.loader import load_mcp_json

__all__ = [
    "MCPAuthConfig",
    "MCPClientManager",
    "MCPConfigError",
    "MCPConnectionError",
    "MCPConnectionResult",
    "MCPConnectionTimeoutError",
    "MCPFileNotFoundError",
    "MCPFileParseError",
    "MCPServerConfig",
    "MCPServerNotFoundError",
    "MCPServerValidationError",
    "MCPToolInfo",
    "load_mcp_json",
]
