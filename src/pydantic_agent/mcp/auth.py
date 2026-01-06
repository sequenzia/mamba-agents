"""MCP authentication handling."""

from __future__ import annotations

import os
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_agent.mcp.config import MCPAuthConfig


def resolve_auth_key(auth: "MCPAuthConfig") -> str | None:
    """Resolve the API key from authentication configuration.

    Handles both direct keys and environment variable references.

    Args:
        auth: The authentication configuration.

    Returns:
        The resolved API key, or None if not configured.

    Raises:
        ValueError: If the key cannot be resolved.
    """
    # Try key_env first (explicit env var name)
    if auth.key_env:
        value = os.environ.get(auth.key_env)
        if value:
            return value
        raise ValueError(f"Environment variable {auth.key_env} not found")

    # Then try key (may be direct value or env var reference)
    if auth.key:
        # Check for ${VAR_NAME} pattern
        match = re.match(r"^\$\{(\w+)\}$", auth.key)
        if match:
            var_name = match.group(1)
            value = os.environ.get(var_name)
            if value:
                return value
            raise ValueError(f"Environment variable {var_name} not found")
        # Direct value
        return auth.key

    return None


def build_auth_headers(auth: "MCPAuthConfig") -> dict[str, str]:
    """Build authentication headers for MCP requests.

    Args:
        auth: The authentication configuration.

    Returns:
        Dictionary of headers for authentication.
    """
    key = resolve_auth_key(auth)
    if not key:
        return {}

    header_name = auth.header

    # For Authorization header, add Bearer prefix if not present
    if header_name.lower() == "authorization" and not key.startswith("Bearer "):
        key = f"Bearer {key}"

    return {header_name: key}
