"""MCP configuration loader for .mcp.json files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from mamba_agents.mcp.config import MCPServerConfig
from mamba_agents.mcp.errors import (
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
)


class MCPJsonServerEntry(BaseModel):
    """A single server entry as it appears in .mcp.json.

    Supports the standard .mcp.json format (Claude Desktop compatible) plus
    extended fields for mamba-agents.

    Standard fields:
        command: Command to run (stdio transport).
        args: Command arguments.
        env: Environment variables.

    Extended fields (mamba-agents):
        url: Server URL (SSE transport).
        tool_prefix: Prefix for tool names from this server.
        env_file: Path to .env file for environment variables.
    """

    # Standard fields (Claude Desktop compatible)
    command: str | None = Field(
        default=None,
        description="Command to run for stdio transport",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command arguments",
    )
    env: dict[str, str] | None = Field(
        default=None,
        description="Environment variables",
    )

    # Extended fields (mamba-agents additions)
    url: str | None = Field(
        default=None,
        description="Server URL for SSE transport",
    )
    tool_prefix: str | None = Field(
        default=None,
        description="Prefix for tool names from this server",
    )
    env_file: str | None = Field(
        default=None,
        description="Path to .env file for environment variables",
    )

    @model_validator(mode="after")
    def validate_transport(self) -> MCPJsonServerEntry:
        """Validate that exactly one transport type is specified."""
        has_command = self.command is not None
        has_url = self.url is not None

        if not has_command and not has_url:
            raise ValueError("Either 'command' or 'url' must be specified")
        if has_command and has_url:
            raise ValueError("Cannot specify both 'command' and 'url'")

        return self


class MCPJsonFile(BaseModel):
    """Root structure of .mcp.json file.

    Attributes:
        mcpServers: Dictionary mapping server names to their configurations.
    """

    mcpServers: dict[str, MCPJsonServerEntry] = Field(
        default_factory=dict,
        description="MCP server configurations keyed by name",
    )


def _entry_to_config(name: str, entry: MCPJsonServerEntry) -> MCPServerConfig:
    """Convert an MCPJsonServerEntry to MCPServerConfig.

    Args:
        name: Server name (from the object key in .mcp.json).
        entry: Parsed server entry.

    Returns:
        MCPServerConfig instance.
    """
    # Auto-detect transport based on which field is present
    transport = "sse" if entry.url else "stdio"

    return MCPServerConfig(
        name=name,
        transport=transport,
        command=entry.command,
        args=entry.args,
        url=entry.url,
        tool_prefix=entry.tool_prefix,
        env_file=entry.env_file,
        env_vars=entry.env,
    )


def load_mcp_json(path: str | Path) -> list[MCPServerConfig]:
    """Load MCP server configurations from a .mcp.json file.

    Parses the .mcp.json file format (compatible with Claude Desktop) and
    converts entries to MCPServerConfig instances.

    Args:
        path: Path to the .mcp.json file. Can be a string or Path object.
              Supports ~ expansion for user home directory.

    Returns:
        List of MCPServerConfig instances.

    Raises:
        MCPFileNotFoundError: If the file does not exist.
        MCPFileParseError: If the file is not valid JSON.
        MCPServerValidationError: If a server entry is invalid.

    Example:
        >>> configs = load_mcp_json(".mcp.json")
        >>> manager = MCPClientManager(configs)
        >>> agent = Agent("gpt-4o", toolsets=manager.as_toolsets())

    Supported .mcp.json format:
        {
          "mcpServers": {
            "filesystem": {
              "command": "npx",
              "args": ["-y", "@modelcontextprotocol/server-filesystem", "/project"],
              "env": {"NODE_ENV": "production"}
            },
            "web-search": {
              "url": "http://localhost:8080/sse",
              "tool_prefix": "web"
            }
          }
        }
    """
    # Expand ~ and resolve path
    file_path = Path(path).expanduser()

    # Check file exists
    if not file_path.exists():
        raise MCPFileNotFoundError(f"MCP config file not found: {file_path}")

    # Read and parse JSON
    try:
        content = file_path.read_text(encoding="utf-8")
        data: dict[str, Any] = json.loads(content)
    except json.JSONDecodeError as e:
        raise MCPFileParseError(f"Invalid JSON in {file_path}: {e}") from e

    # Parse with Pydantic model
    try:
        mcp_file = MCPJsonFile.model_validate(data)
    except ValueError as e:
        raise MCPServerValidationError(f"Invalid MCP config structure: {e}") from e

    # Convert entries to MCPServerConfig
    configs: list[MCPServerConfig] = []
    for name, entry in mcp_file.mcpServers.items():
        try:
            config = _entry_to_config(name, entry)
            configs.append(config)
        except ValueError as e:
            raise MCPServerValidationError(f"Invalid server '{name}': {e}") from e

    return configs
