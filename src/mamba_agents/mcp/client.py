"""MCP client manager for mamba-agents."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio

from mamba_agents.mcp.auth import build_auth_headers
from mamba_agents.mcp.config import MCPServerConfig
from mamba_agents.mcp.env import resolve_server_env
from mamba_agents.mcp.loader import load_mcp_json

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
