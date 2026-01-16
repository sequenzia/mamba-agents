"""MCP client manager for mamba-agents."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio

from mamba_agents.mcp.auth import build_auth_headers
from mamba_agents.mcp.config import MCPServerConfig
from mamba_agents.mcp.env import resolve_server_env
from mamba_agents.mcp.lifecycle import ServerLifecycleManager, ServerStatus

if TYPE_CHECKING:
    from pydantic_ai.mcp import MCPServer


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
        self._lifecycle = ServerLifecycleManager()

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
            )
        elif config.transport == "sse":
            if not config.url:
                raise ValueError(f"URL required for SSE transport: {config.name}")

            headers = {}
            if config.auth:
                headers = build_auth_headers(config.auth)

            return MCPServerSSE(config.url, headers=headers, tool_prefix=config.tool_prefix)
        else:
            raise ValueError(f"Unknown transport: {config.transport}")

    async def connect_all(self) -> list[MCPServer]:
        """Connect to all configured servers.

        .. deprecated::
            Use `as_toolsets()` instead. pydantic-ai handles server lifecycle
            automatically when servers are passed via the `toolsets` parameter.

        Returns:
            List of connected MCPServer instances.

        Raises:
            ConnectionError: If any server fails to connect.
        """
        warnings.warn(
            "connect_all() is deprecated. Use as_toolsets() instead and pass servers "
            "to Agent(toolsets=...). pydantic-ai handles server lifecycle automatically.",
            DeprecationWarning,
            stacklevel=2,
        )
        servers = []
        for config in self._configs:
            server = await self._lifecycle.start_server(config)
            servers.append(server)
        return servers

    async def disconnect_all(self) -> None:
        """Disconnect from all servers.

        .. deprecated::
            Use `as_toolsets()` instead. pydantic-ai handles server lifecycle
            automatically when servers are passed via the `toolsets` parameter.
        """
        warnings.warn(
            "disconnect_all() is deprecated. Use as_toolsets() instead and pass servers "
            "to Agent(toolsets=...). pydantic-ai handles server lifecycle automatically.",
            DeprecationWarning,
            stacklevel=2,
        )
        await self._lifecycle.stop_all()

    def get_toolsets(self) -> list[MCPServer]:
        """Get MCP servers from lifecycle manager.

        .. deprecated::
            Use `as_toolsets()` instead which creates servers directly from configs.

        Returns:
            List of MCPServer instances from lifecycle manager.
        """
        warnings.warn(
            "get_toolsets() is deprecated. Use as_toolsets() instead which creates "
            "servers directly from configurations.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._lifecycle.get_all_servers()

    def get_server(self, name: str) -> MCPServer | None:
        """Get a specific server by name from lifecycle manager.

        Args:
            name: Server name.

        Returns:
            The MCPServer if managed by lifecycle, None otherwise.
        """
        return self._lifecycle.get_server(name)

    def get_status(self, name: str) -> ServerStatus:
        """Get the status of a server.

        Args:
            name: Server name.

        Returns:
            ServerStatus object with state information.
        """
        return self._lifecycle.get_status(name)

    def get_all_statuses(self) -> list[ServerStatus]:
        """Get status of all servers managed by lifecycle.

        Returns:
            List of ServerStatus objects.
        """
        return self._lifecycle.get_all_statuses()

    @property
    def configs(self) -> list[MCPServerConfig]:
        """Get all server configurations."""
        return self._configs.copy()

    async def __aenter__(self) -> MCPClientManager:
        """Async context manager entry.

        .. deprecated::
            Use `as_toolsets()` instead and pass servers to Agent(toolsets=...).
            pydantic-ai handles server lifecycle automatically.
        """
        warnings.warn(
            "Using MCPClientManager as async context manager is deprecated. "
            "Use as_toolsets() and pass servers to Agent(toolsets=...) instead. "
            "pydantic-ai handles server lifecycle automatically.",
            DeprecationWarning,
            stacklevel=2,
        )
        await self._lifecycle_connect_all_internal()
        return self

    async def _lifecycle_connect_all_internal(self) -> list[MCPServer]:
        """Internal method to connect all servers (no deprecation warning)."""
        servers = []
        for config in self._configs:
            server = await self._lifecycle.start_server(config)
            servers.append(server)
        return servers

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit - disconnect all servers."""
        await self._lifecycle.stop_all()
