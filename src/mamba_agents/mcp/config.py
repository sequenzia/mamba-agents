"""MCP server configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class MCPAuthConfig(BaseModel):
    """Authentication configuration for MCP servers.

    Attributes:
        type: Authentication type (currently only api_key supported).
        key_env: Environment variable name containing the API key.
        key: Direct key value or env var reference (${VAR_NAME}).
        header: HTTP header name for the key.
    """

    type: Literal["api_key"] = "api_key"
    key_env: str | None = Field(
        default=None,
        description="Environment variable name containing the API key",
    )
    key: str | None = Field(
        default=None,
        description="Direct key value or env var reference (${VAR_NAME})",
    )
    header: str = Field(
        default="Authorization",
        description="HTTP header name for the key",
    )


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server.

    Supports both stdio (subprocess) and SSE (HTTP) transports.

    Attributes:
        name: Unique server name.
        transport: Transport type (stdio or sse).
        command: Command to run (stdio transport).
        args: Command arguments (stdio transport).
        url: Server URL (SSE transport).
        auth: Authentication configuration.
        tool_prefix: Prefix for tool names from this server.
        env_file: Path to .env file for environment variables.
        env_vars: Environment variables (highest precedence).
        timeout: Initialization timeout in seconds (default: 30).
        read_timeout: Read timeout for long-lived connections in seconds (default: 300).
    """

    name: str = Field(description="Unique server name")
    transport: Literal["stdio", "sse"] = Field(
        default="stdio",
        description="Transport type",
    )
    # For stdio transport
    command: str | None = Field(
        default=None,
        description="Command to run for stdio transport",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Command arguments",
    )
    # For SSE transport
    url: str | None = Field(
        default=None,
        description="Server URL for SSE transport",
    )
    # Authentication
    auth: MCPAuthConfig | None = Field(
        default=None,
        description="Authentication configuration",
    )
    # Tool namespacing
    tool_prefix: str | None = Field(
        default=None,
        description="Prefix for tool names from this server",
    )
    # Environment variables
    env_file: str | Path | None = Field(
        default=None,
        description="Path to .env file for environment variables",
    )
    env_vars: dict[str, str] | None = Field(
        default=None,
        description="Environment variables (highest precedence)",
    )
    # Timeouts
    timeout: float = Field(
        default=30.0,
        description="Initialization timeout in seconds (default: 30)",
    )
    read_timeout: float = Field(
        default=300.0,
        description="Read timeout for long-lived connections in seconds (default: 300)",
    )
