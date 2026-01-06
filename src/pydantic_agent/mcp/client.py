"""MCP client manager for pydantic-agent."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic_agent.mcp.config import MCPServerConfig
from pydantic_agent.mcp.lifecycle import ServerLifecycleManager, ServerStatus

if TYPE_CHECKING:
    from pydantic_ai.mcp import MCPServer


class MCPClientManager:
    """Manages MCP server connections.

    Provides a high-level interface for connecting to and managing
    multiple MCP servers.
    """

    def __init__(self, configs: list[MCPServerConfig] | None = None) -> None:
        """Initialize the MCP client manager.

        Args:
            configs: Optional list of server configurations to connect.
        """
        self._configs = configs or []
        self._lifecycle = ServerLifecycleManager()

    def add_server(self, config: MCPServerConfig) -> None:
        """Add a server configuration.

        Args:
            config: Server configuration to add.
        """
        self._configs.append(config)

    async def connect_all(self) -> list["MCPServer"]:
        """Connect to all configured servers.

        Returns:
            List of connected MCPServer instances.

        Raises:
            ConnectionError: If any server fails to connect.
        """
        servers = []
        for config in self._configs:
            server = await self._lifecycle.start_server(config)
            servers.append(server)
        return servers

    async def disconnect_all(self) -> None:
        """Disconnect from all servers."""
        await self._lifecycle.stop_all()

    def get_toolsets(self) -> list["MCPServer"]:
        """Get MCP servers as toolsets for pydantic-ai Agent.

        Returns:
            List of MCPServer instances to use as toolsets.
        """
        return self._lifecycle.get_all_servers()

    def get_server(self, name: str) -> "MCPServer | None":
        """Get a specific server by name.

        Args:
            name: Server name.

        Returns:
            The MCPServer if connected, None otherwise.
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
        """Get status of all servers.

        Returns:
            List of ServerStatus objects.
        """
        return self._lifecycle.get_all_statuses()

    async def __aenter__(self) -> "MCPClientManager":
        """Async context manager entry - connect all servers."""
        await self.connect_all()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit - disconnect all servers."""
        await self.disconnect_all()
