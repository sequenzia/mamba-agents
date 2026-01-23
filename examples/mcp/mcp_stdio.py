#!/usr/bin/env python3
"""MCP stdio transport example.

This example demonstrates:
- Configuring MCP servers with stdio transport
- Running servers as subprocesses
- Using tool prefixes to avoid conflicts

Prerequisites:
- Node.js installed (for npx)
- Set OPENAI_API_KEY environment variable

Note: This example requires the MCP filesystem server.
Install with: npx -y @modelcontextprotocol/server-filesystem
"""

import os

from mamba_agents import Agent
from mamba_agents.mcp import MCPClientManager, MCPServerConfig


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Configure MCP server with stdio transport
    configs = [
        MCPServerConfig(
            name="filesystem",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            tool_prefix="fs",  # Tools become: fs_read_file, fs_write_file, etc.
        ),
    ]

    # Create manager and get toolsets
    manager = MCPClientManager(configs)

    print("Configured MCP servers:")
    for config in manager.configs:
        print(f"  {config.name}: {config.transport} transport")
        print(f"    Command: {config.command} {' '.join(config.args or [])}")
        print(f"    Tool prefix: {config.tool_prefix or 'none'}")

    # Create agent with MCP toolsets
    # pydantic-ai handles server lifecycle automatically
    print("\nCreating agent with MCP toolsets...")
    agent = Agent("gpt-4o-mini", toolsets=manager.as_toolsets())

    # Use the agent (uncomment to run)
    # result = agent.run_sync("List files in /tmp using the MCP filesystem tools")
    # print(f"\nAgent response: {result.output}")

    print("\nTo use the agent, uncomment the run_sync lines in this script.")


if __name__ == "__main__":
    main()
