"""Tests for MCP configuration models."""

from __future__ import annotations

from mamba_agents.mcp.config import MCPAuthConfig, MCPServerConfig


class TestMCPAuthConfig:
    """Tests for MCPAuthConfig."""

    def test_default_values(self) -> None:
        """Test default values for MCPAuthConfig."""
        auth = MCPAuthConfig()
        assert auth.type == "api_key"
        assert auth.key_env is None
        assert auth.key is None
        assert auth.header == "Authorization"

    def test_with_key(self) -> None:
        """Test MCPAuthConfig with direct key."""
        auth = MCPAuthConfig(key="my-secret-key")
        assert auth.key == "my-secret-key"

    def test_with_key_env(self) -> None:
        """Test MCPAuthConfig with environment variable reference."""
        auth = MCPAuthConfig(key_env="MY_API_KEY")
        assert auth.key_env == "MY_API_KEY"

    def test_with_custom_header(self) -> None:
        """Test MCPAuthConfig with custom header."""
        auth = MCPAuthConfig(key="test", header="X-API-Key")
        assert auth.header == "X-API-Key"


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_stdio_config(self) -> None:
        """Test MCPServerConfig for stdio transport."""
        config = MCPServerConfig(
            name="test-server",
            transport="stdio",
            command="python",
            args=["-m", "my_server"],
        )
        assert config.name == "test-server"
        assert config.transport == "stdio"
        assert config.command == "python"
        assert config.args == ["-m", "my_server"]
        assert config.url is None

    def test_sse_config(self) -> None:
        """Test MCPServerConfig for SSE transport."""
        config = MCPServerConfig(
            name="web-server",
            transport="sse",
            url="http://localhost:8080/sse",
        )
        assert config.name == "web-server"
        assert config.transport == "sse"
        assert config.url == "http://localhost:8080/sse"
        assert config.command is None

    def test_with_auth(self) -> None:
        """Test MCPServerConfig with authentication."""
        auth = MCPAuthConfig(key="secret")
        config = MCPServerConfig(
            name="secure-server",
            transport="sse",
            url="https://api.example.com/mcp",
            auth=auth,
        )
        assert config.auth is not None
        assert config.auth.key == "secret"

    def test_with_tool_prefix(self) -> None:
        """Test MCPServerConfig with tool prefix."""
        config = MCPServerConfig(
            name="fs-server",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
            tool_prefix="fs",
        )
        assert config.tool_prefix == "fs"

    def test_default_transport(self) -> None:
        """Test that default transport is stdio."""
        config = MCPServerConfig(name="test", command="test-cmd")
        assert config.transport == "stdio"

    def test_default_args_empty_list(self) -> None:
        """Test that default args is empty list."""
        config = MCPServerConfig(name="test", command="test-cmd")
        assert config.args == []

    def test_default_timeout_values(self) -> None:
        """Test that default timeout values are set correctly."""
        config = MCPServerConfig(name="test", command="test-cmd")
        assert config.timeout == 30.0
        assert config.read_timeout == 300.0

    def test_custom_timeout_values(self) -> None:
        """Test MCPServerConfig with custom timeout values."""
        config = MCPServerConfig(
            name="slow-server",
            command="slow-cmd",
            timeout=60.0,
            read_timeout=600.0,
        )
        assert config.timeout == 60.0
        assert config.read_timeout == 600.0
