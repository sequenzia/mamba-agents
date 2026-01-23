#!/usr/bin/env python3
"""Load MCP configuration from .mcp.json files.

This example demonstrates:
- Loading MCP servers from .mcp.json files
- Claude Desktop compatible format
- Merging configs from multiple files
- Extended fields (tool_prefix, env_file)

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import json
import tempfile
from pathlib import Path

from mamba_agents.mcp import (
    MCPClientManager,
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
    load_mcp_json,
)


def main():
    # Create a sample .mcp.json file
    sample_config = {
        "mcpServers": {
            "filesystem": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", "/project"],
                "tool_prefix": "fs",  # mamba-agents extension
            },
            "web-search": {
                "url": "http://localhost:8080/sse",  # Auto-detected as SSE
                "tool_prefix": "search",
            },
            "api-server": {
                "url": "http://localhost:8080/mcp",  # Auto-detected as Streamable HTTP
                "tool_prefix": "api",
            },
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_config, f)
        config_path = f.name

    print("Sample .mcp.json content:")
    print(json.dumps(sample_config, indent=2))
    print()

    # Method 1: Create manager directly from file
    print("--- Method 1: MCPClientManager.from_mcp_json() ---\n")
    manager = MCPClientManager.from_mcp_json(config_path)

    print(f"Loaded {len(manager.configs)} servers:")
    for config in manager.configs:
        transport = config.transport
        location = config.url if config.url else f"{config.command} {' '.join(config.args or [])}"
        print(f"  {config.name}: {transport} @ {location}")
    print()

    # Method 2: Load and inspect configs before creating manager
    print("--- Method 2: load_mcp_json() for inspection ---\n")
    configs = load_mcp_json(config_path)

    # Filter or modify configs
    filtered = [c for c in configs if c.transport == "stdio"]
    print(f"Found {len(filtered)} stdio servers")
    print()

    # Method 3: Merge multiple config files
    print("--- Method 3: Merging multiple files ---\n")
    manager = MCPClientManager.from_mcp_json(config_path)
    # manager.add_from_file("~/.mcp.json")  # Add user defaults
    # manager.add_from_file("/team/shared.mcp.json")  # Add team config
    print("Use add_from_file() to merge configs from multiple sources")
    print()

    # Error handling
    print("--- Error Handling ---\n")
    try:
        MCPClientManager.from_mcp_json("nonexistent.json")
    except MCPFileNotFoundError:
        print("  MCPFileNotFoundError: Config file not found")

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("invalid json {")
            bad_path = f.name
        MCPClientManager.from_mcp_json(bad_path)
    except MCPFileParseError:
        print("  MCPFileParseError: Invalid JSON")
    finally:
        Path(bad_path).unlink(missing_ok=True)

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"mcpServers": {"bad": {}}}, f)  # Missing required fields
            bad_path = f.name
        MCPClientManager.from_mcp_json(bad_path)
    except MCPServerValidationError:
        print("  MCPServerValidationError: Invalid server config")
    finally:
        Path(bad_path).unlink(missing_ok=True)

    # Clean up
    Path(config_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
