#!/usr/bin/env python3
"""MCP connection testing example (v0.1.3+).

This example demonstrates:
- Testing individual server connections
- Testing all connections at once
- Handling connection errors
- Inspecting available tools

Prerequisites:
- Node.js installed (for npx)
"""

import asyncio

from mamba_agents.mcp import MCPClientManager, MCPServerConfig


async def async_example():
    """Async connection testing."""
    print("--- Async Connection Testing ---\n")

    # Configure MCP servers
    configs = [
        MCPServerConfig(
            name="filesystem",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            tool_prefix="fs",
            timeout=10,  # 10 second connection timeout
        ),
    ]

    manager = MCPClientManager(configs)

    # Test a single connection
    print("Testing filesystem server connection...")
    result = await manager.test_connection("filesystem")

    if result.success:
        print(f"  Connected! Server running: {result.is_running}")
        print(f"  Available tools ({result.tool_count}):")
        for tool in result.tools:
            desc = tool.description or "No description"
            # Truncate long descriptions
            if len(desc) > 60:
                desc = desc[:57] + "..."
            print(f"    - {tool.name}: {desc}")
    else:
        print(f"  Connection failed: {result.error}")
        print(f"  Error type: {result.error_type}")

    # Test all connections at once
    print("\nTesting all connections...")
    results = await manager.test_all_connections()

    for name, res in results.items():
        status = "OK" if res.success else f"FAILED ({res.error_type})"
        tools = f"{res.tool_count} tools" if res.success else ""
        print(f"  {name}: {status} {tools}")


def sync_example():
    """Synchronous connection testing."""
    print("\n--- Sync Connection Testing ---\n")

    configs = [
        MCPServerConfig(
            name="test-server",
            transport="stdio",
            command="echo",  # Simple command that will fail MCP handshake
            args=["hello"],
            timeout=5,
        ),
    ]

    manager = MCPClientManager(configs)

    # Sync version of test_connection
    result = manager.test_connection_sync("test-server")
    print(f"Test result: {'OK' if result.success else 'FAILED'}")
    if not result.success:
        print(f"  Error: {result.error}")
        print(f"  Type: {result.error_type}")


if __name__ == "__main__":
    asyncio.run(async_example())
    sync_example()
