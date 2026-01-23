"""MCP client manager for mamba-agents."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel
from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio, MCPServerStreamableHTTP

from mamba_agents.mcp.auth import build_auth_headers
from mamba_agents.mcp.config import MCPServerConfig
from mamba_agents.mcp.env import resolve_server_env
from mamba_agents.mcp.errors import MCPServerNotFoundError
from mamba_agents.mcp.loader import load_mcp_json

if TYPE_CHECKING:
    from pydantic_ai.mcp import MCPServer


class MCPToolInfo(BaseModel):
    """Information about a tool provided by an MCP server.

    Attributes:
        name: Tool name.
        description: Tool description (may be None).
        input_schema: JSON schema for tool input parameters (may be None).
    """

    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = None


class MCPConnectionResult(BaseModel):
    """Result of testing a connection to an MCP server.

    Attributes:
        server_name: Name of the server that was tested.
        success: Whether the connection succeeded.
        is_running: Whether the server is running.
        tools: List of tools available from the server.
        tool_count: Number of tools available.
        error: Error message if connection failed.
        error_type: Type of error if connection failed.
    """

    server_name: str
    success: bool
    is_running: bool = False
    tools: list[MCPToolInfo] = []
    tool_count: int = 0
    error: str | None = None
    error_type: str | None = None


class MCPClientManager:
    """Manages MCP server configurations and creates toolsets for pydantic-ai Agent.

    The recommended pattern is to use `as_toolsets()` to get MCP servers and pass
    them directly to the Agent via the `toolsets` parameter. pydantic-ai handles
    the server lifecycle (connection/disconnection) automatically.

    Example:
        >>> configs = [
        ...     MCPServerConfig(
        ...         name="filesystem",
        ...         transport="stdio",
        ...         command="npx",
        ...         args=["-y", "@modelcontextprotocol/server-filesystem", "/project"],
        ...         tool_prefix="fs",
        ...     ),
        ... ]
        >>> manager = MCPClientManager(configs)
        >>> agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
        >>> result = await agent.run("List project files")
    """

    def __init__(self, configs: list[MCPServerConfig] | None = None) -> None:
        """Initialize the MCP client manager.

        Args:
            configs: Optional list of server configurations.
        """
        self._configs = configs or []

    def add_server(self, config: MCPServerConfig) -> None:
        """Add a server configuration.

        Args:
            config: Server configuration to add.
        """
        self._configs.append(config)

    def as_toolsets(self) -> list[MCPServer]:
        """Get MCP servers as toolsets for pydantic-ai Agent.

        Creates MCPServer instances from configurations. These servers should
        be passed to Agent via the `toolsets` parameter. pydantic-ai handles
        server lifecycle automatically (connection on first use, cleanup on exit).

        Returns:
            List of MCPServer instances to pass to Agent(toolsets=...).

        Example:
            >>> manager = MCPClientManager(configs)
            >>> agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
        """
        servers: list[MCPServer] = []
        for config in self._configs:
            server = self._create_server(config)
            servers.append(server)
        return servers

    def _create_server(self, config: MCPServerConfig) -> MCPServer:
        """Create an MCP server instance from configuration.

        Args:
            config: Server configuration.

        Returns:
            MCPServer instance.

        Raises:
            ValueError: If configuration is invalid.
        """
        if config.transport == "stdio":
            if not config.command:
                raise ValueError(f"Command required for stdio transport: {config.name}")

            env = resolve_server_env(config)
            return MCPServerStdio(
                config.command,
                args=config.args,
                env=env,
                tool_prefix=config.tool_prefix,
                timeout=config.timeout,
                read_timeout=config.read_timeout,
            )
        elif config.transport == "sse":
            if not config.url:
                raise ValueError(f"URL required for SSE transport: {config.name}")

            headers = {}
            if config.auth:
                headers = build_auth_headers(config.auth)

            return MCPServerSSE(
                config.url,
                headers=headers,
                tool_prefix=config.tool_prefix,
                timeout=config.timeout,
                read_timeout=config.read_timeout,
            )
        elif config.transport == "streamable_http":
            if not config.url:
                raise ValueError(f"URL required for Streamable HTTP transport: {config.name}")

            headers = {}
            if config.auth:
                headers = build_auth_headers(config.auth)

            return MCPServerStreamableHTTP(
                config.url,
                headers=headers,
                tool_prefix=config.tool_prefix,
                timeout=config.timeout,
                read_timeout=config.read_timeout,
            )
        else:
            raise ValueError(f"Unknown transport: {config.transport}")

    @property
    def configs(self) -> list[MCPServerConfig]:
        """Get all server configurations."""
        return self._configs.copy()

    @classmethod
    def from_mcp_json(cls, path: str | Path) -> MCPClientManager:
        """Create an MCPClientManager from a .mcp.json file.

        Parses the .mcp.json file format (compatible with Claude Desktop) and
        creates a manager with the loaded configurations.

        Args:
            path: Path to the .mcp.json file. Can be a string or Path object.
                  Supports ~ expansion for user home directory.

        Returns:
            MCPClientManager instance with loaded configurations.

        Raises:
            MCPFileNotFoundError: If the file does not exist.
            MCPFileParseError: If the file is not valid JSON.
            MCPServerValidationError: If a server entry is invalid.

        Example:
            >>> manager = MCPClientManager.from_mcp_json(".mcp.json")
            >>> agent = Agent("gpt-4o", toolsets=manager.as_toolsets())
        """
        configs = load_mcp_json(path)
        return cls(configs)

    def add_from_file(self, path: str | Path) -> None:
        """Add server configurations from a .mcp.json file.

        Parses the .mcp.json file and appends configurations to the existing
        list. Useful for merging multiple configuration sources.

        Args:
            path: Path to the .mcp.json file. Can be a string or Path object.
                  Supports ~ expansion for user home directory.

        Raises:
            MCPFileNotFoundError: If the file does not exist.
            MCPFileParseError: If the file is not valid JSON.
            MCPServerValidationError: If a server entry is invalid.

        Example:
            >>> manager = MCPClientManager(existing_configs)
            >>> manager.add_from_file("project/.mcp.json")
            >>> manager.add_from_file("~/.mcp.json")  # User defaults
        """
        configs = load_mcp_json(path)
        self._configs.extend(configs)

    def get_server(self, name: str) -> MCPServer:
        """Get a single MCP server instance by name.

        Creates an MCPServer instance from the configuration with the given name.

        Args:
            name: Name of the server to retrieve.

        Returns:
            MCPServer instance.

        Raises:
            MCPServerNotFoundError: If no server with the given name exists.

        Example:
            >>> manager = MCPClientManager(configs)
            >>> server = manager.get_server("filesystem")
        """
        config = self._get_config_by_name(name)
        if config is None:
            raise MCPServerNotFoundError(f"Server not found: {name}")
        return self._create_server(config)

    def _get_config_by_name(self, name: str) -> MCPServerConfig | None:
        """Get a server configuration by name.

        Args:
            name: Server name to find.

        Returns:
            MCPServerConfig if found, None otherwise.
        """
        for config in self._configs:
            if config.name == name:
                return config
        return None

    async def test_connection(self, server_name: str) -> MCPConnectionResult:
        """Test connection to an MCP server.

        Creates a server instance, connects to it, and retrieves the list of
        available tools to verify the connection is working.

        Args:
            server_name: Name of the server to test.

        Returns:
            MCPConnectionResult with connection status and tool information.

        Example:
            >>> manager = MCPClientManager(configs)
            >>> result = await manager.test_connection("filesystem")
            >>> if result.success:
            ...     print(f"Connected! {result.tool_count} tools available")
        """
        config = self._get_config_by_name(server_name)
        if config is None:
            return MCPConnectionResult(
                server_name=server_name,
                success=False,
                error=f"Server not found: {server_name}",
                error_type="MCPServerNotFoundError",
            )

        try:
            server = self._create_server(config)
            async with server:
                is_running = server.is_running
                tools_raw = await server.list_tools()
                tools = [
                    MCPToolInfo(
                        name=t.name,
                        description=t.description,
                        input_schema=t.input_schema,
                    )
                    for t in tools_raw
                ]
                return MCPConnectionResult(
                    server_name=server_name,
                    success=True,
                    is_running=is_running,
                    tools=tools,
                    tool_count=len(tools),
                )
        except TimeoutError as e:
            return MCPConnectionResult(
                server_name=server_name,
                success=False,
                error=f"Connection to {server_name} timed out: {e}",
                error_type="MCPConnectionTimeoutError",
            )
        except Exception as e:
            return MCPConnectionResult(
                server_name=server_name,
                success=False,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def test_all_connections(self) -> dict[str, MCPConnectionResult]:
        """Test connections to all configured MCP servers.

        Tests each server concurrently and returns results for all.

        Returns:
            Dictionary mapping server names to their connection results.

        Example:
            >>> manager = MCPClientManager(configs)
            >>> results = await manager.test_all_connections()
            >>> for name, result in results.items():
            ...     status = "OK" if result.success else "FAILED"
            ...     print(f"{name}: {status}")
        """
        tasks = [self.test_connection(config.name) for config in self._configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return_dict: dict[str, MCPConnectionResult] = {}
        for config, result in zip(self._configs, results, strict=True):
            if isinstance(result, Exception):
                return_dict[config.name] = MCPConnectionResult(
                    server_name=config.name,
                    success=False,
                    error=str(result),
                    error_type=type(result).__name__,
                )
            else:
                return_dict[config.name] = result
        return return_dict

    def test_connection_sync(self, server_name: str) -> MCPConnectionResult:
        """Synchronous wrapper for test_connection.

        Args:
            server_name: Name of the server to test.

        Returns:
            MCPConnectionResult with connection status and tool information.

        Example:
            >>> manager = MCPClientManager(configs)
            >>> result = manager.test_connection_sync("filesystem")
            >>> print(f"Success: {result.success}")
        """
        return asyncio.run(self.test_connection(server_name))

    def test_all_connections_sync(self) -> dict[str, MCPConnectionResult]:
        """Synchronous wrapper for test_all_connections.

        Returns:
            Dictionary mapping server names to their connection results.

        Example:
            >>> manager = MCPClientManager(configs)
            >>> results = manager.test_all_connections_sync()
        """
        return asyncio.run(self.test_all_connections())
