"""MCP configuration error hierarchy."""

from __future__ import annotations


class MCPConfigError(Exception):
    """Base exception for MCP configuration errors."""


class MCPFileNotFoundError(MCPConfigError):
    """Raised when .mcp.json file cannot be found."""


class MCPFileParseError(MCPConfigError):
    """Raised when .mcp.json file cannot be parsed as JSON."""


class MCPServerValidationError(MCPConfigError):
    """Raised when a server configuration in .mcp.json is invalid."""
