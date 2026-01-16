"""Environment variable resolution for MCP servers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import dotenv_values

if TYPE_CHECKING:
    from mamba_agents.mcp.config import MCPServerConfig


def resolve_server_env(config: MCPServerConfig) -> dict[str, str] | None:
    """Resolve environment variables for an MCP server.

    Merges environment variables in order (later overwrites earlier):
    1. os.environ (base)
    2. env_file contents
    3. env_vars dict

    Returns None if no env customization is needed, allowing the subprocess
    to inherit the parent's environment naturally.

    Args:
        config: Server configuration with optional env_file and env_vars.

    Returns:
        Merged environment dict, or None if no customization needed.

    Raises:
        FileNotFoundError: If env_file is specified but does not exist.
    """
    # If no customization, let subprocess inherit parent env
    if config.env_file is None and config.env_vars is None:
        return None

    # Start with system environment
    env = dict(os.environ)

    # Layer env_file if provided
    if config.env_file:
        env_path = Path(config.env_file)
        if not env_path.exists():
            raise FileNotFoundError(f"env_file not found: {env_path}")
        file_vars = dotenv_values(env_path)
        # Filter out None values (dotenv_values can return None for unset vars)
        env.update({k: v for k, v in file_vars.items() if v is not None})

    # Layer env_vars (highest precedence)
    if config.env_vars:
        env.update(config.env_vars)

    return env
