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


class MCPConnectionError(Exception):
    """Base exception for MCP connection errors."""


class MCPConnectionTimeoutError(MCPConnectionError):
    """Raised when connection to an MCP server times out."""


class MCPServerNotFoundError(MCPConnectionError):
    """Raised when a server name is not found in configurations."""
