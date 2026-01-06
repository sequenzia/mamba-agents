"""MCP server lifecycle management."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_ai.mcp import MCPServer

    from pydantic_agent.mcp.config import MCPServerConfig


class ServerState(Enum):
    """State of an MCP server."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class ServerStatus:
    """Status information for an MCP server.

    Attributes:
        name: Server name.
        state: Current server state.
        error: Error message if in error state.
        tools: List of available tool names.
    """

    name: str
    state: ServerState
    error: str | None = None
    tools: list[str] = field(default_factory=list)


class ServerLifecycleManager:
    """Manages the lifecycle of MCP servers.

    Handles starting, stopping, and health checking MCP servers.
    """

    def __init__(self) -> None:
        """Initialize the lifecycle manager."""
        self._servers: dict[str, "MCPServer"] = {}
        self._states: dict[str, ServerState] = {}
        self._errors: dict[str, str] = {}

    async def start_server(
        self,
        config: "MCPServerConfig",
    ) -> "MCPServer":
        """Start an MCP server based on configuration.

        Args:
            config: Server configuration.

        Returns:
            The connected MCP server.

        Raises:
            ValueError: If transport type is invalid.
            ConnectionError: If server fails to connect.
        """
        from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio

        from pydantic_agent.mcp.auth import build_auth_headers

        self._states[config.name] = ServerState.STARTING

        try:
            if config.transport == "stdio":
                if not config.command:
                    raise ValueError(f"Command required for stdio transport: {config.name}")

                server = MCPServerStdio(
                    config.command,
                    args=config.args,
                )
            elif config.transport == "sse":
                if not config.url:
                    raise ValueError(f"URL required for SSE transport: {config.name}")

                headers = {}
                if config.auth:
                    headers = build_auth_headers(config.auth)

                server = MCPServerSSE(config.url, headers=headers)
            else:
                raise ValueError(f"Unknown transport: {config.transport}")

            self._servers[config.name] = server
            self._states[config.name] = ServerState.RUNNING
            return server

        except Exception as e:
            self._states[config.name] = ServerState.ERROR
            self._errors[config.name] = str(e)
            raise

    async def stop_server(self, name: str) -> None:
        """Stop an MCP server.

        Args:
            name: Name of the server to stop.
        """
        if name not in self._servers:
            return

        self._states[name] = ServerState.STOPPING

        # MCP servers are context managers, they clean up when exiting
        # For now, just remove from tracking
        del self._servers[name]
        self._states[name] = ServerState.STOPPED

    async def stop_all(self) -> None:
        """Stop all MCP servers."""
        names = list(self._servers.keys())
        for name in names:
            await self.stop_server(name)

    def get_status(self, name: str) -> ServerStatus:
        """Get the status of a server.

        Args:
            name: Server name.

        Returns:
            ServerStatus object.
        """
        state = self._states.get(name, ServerState.STOPPED)
        error = self._errors.get(name)

        return ServerStatus(
            name=name,
            state=state,
            error=error,
        )

    def get_all_statuses(self) -> list[ServerStatus]:
        """Get status of all known servers.

        Returns:
            List of ServerStatus objects.
        """
        return [self.get_status(name) for name in self._states]

    def get_server(self, name: str) -> "MCPServer | None":
        """Get a running server by name.

        Args:
            name: Server name.

        Returns:
            The MCPServer if running, None otherwise.
        """
        return self._servers.get(name)

    def get_all_servers(self) -> list["MCPServer"]:
        """Get all running servers.

        Returns:
            List of running MCPServer instances.
        """
        return list(self._servers.values())
