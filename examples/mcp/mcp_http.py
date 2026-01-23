#!/usr/bin/env python3
"""MCP HTTP transports example (SSE and Streamable HTTP).

This example demonstrates:
- SSE transport (Server-Sent Events)
- Streamable HTTP transport (v0.1.3+)
- Authentication with API keys
- Transport auto-detection from URL

Prerequisites:
- Running MCP server(s)
- Set MCP_API_KEY for authenticated servers (optional)

Note: Requires running MCP HTTP servers to test.
"""

from mamba_agents.mcp import MCPAuthConfig, MCPClientManager, MCPServerConfig


def main():
    # SSE Transport - URLs ending in /sse
    sse_config = MCPServerConfig(
        name="sse-server",
        transport="sse",
        url="http://localhost:8080/sse",
        tool_prefix="sse",
        timeout=30,
        read_timeout=300,  # Long timeout for streaming responses
    )

    # Streamable HTTP Transport (v0.1.3+)
    # Use for modern HTTP-based MCP servers
    http_config = MCPServerConfig(
        name="http-server",
        transport="streamable_http",
        url="http://localhost:8080/mcp",
        tool_prefix="http",
        auth=MCPAuthConfig(
            type="api_key",
            key_env="MCP_API_KEY",  # Read from environment variable
            header="Authorization",
        ),
        timeout=60,
        read_timeout=300,
    )

    manager = MCPClientManager([sse_config, http_config])

    print("Configured HTTP-based MCP servers:\n")
    for config in manager.configs:
        print(f"  {config.name}:")
        print(f"    Transport: {config.transport}")
        print(f"    URL: {config.url}")
        print(f"    Tool prefix: {config.tool_prefix}")
        print(f"    Timeout: {config.timeout}s (connection), {config.read_timeout}s (read)")
        if config.auth:
            print(f"    Auth: API key from ${config.auth.key_env}")
        print()

    print("Transport auto-detection from .mcp.json files:")
    print("  - URL ending in /sse -> SSE transport")
    print("  - Other URLs -> Streamable HTTP transport")
    print("  - Command present -> stdio transport")


if __name__ == "__main__":
    main()
