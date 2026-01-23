"""Tests for MCPClientManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio, MCPServerStreamableHTTP

from mamba_agents.mcp import (
    MCPClientManager,
    MCPConnectionResult,
    MCPFileNotFoundError,
    MCPServerConfig,
    MCPServerNotFoundError,
    MCPToolInfo,
)


class TestMCPClientManager:
    """Tests for MCPClientManager."""

    def test_init_empty(self) -> None:
        """Test initialization with no configs."""
        manager = MCPClientManager()
        assert manager.configs == []

    def test_init_with_configs(self) -> None:
        """Test initialization with configs."""
        configs = [
            MCPServerConfig(name="server1", transport="stdio", command="cmd1"),
            MCPServerConfig(name="server2", transport="stdio", command="cmd2"),
        ]
        manager = MCPClientManager(configs)
        assert len(manager.configs) == 2
        assert manager.configs[0].name == "server1"

    def test_add_server(self) -> None:
        """Test adding a server configuration."""
        manager = MCPClientManager()
        config = MCPServerConfig(name="new-server", transport="stdio", command="cmd")
        manager.add_server(config)
        assert len(manager.configs) == 1
        assert manager.configs[0].name == "new-server"

    def test_configs_returns_copy(self) -> None:
        """Test that configs property returns a copy."""
        configs = [MCPServerConfig(name="server1", command="cmd")]
        manager = MCPClientManager(configs)

        # Modifying returned list shouldn't affect internal state
        returned_configs = manager.configs
        returned_configs.append(MCPServerConfig(name="server2", command="cmd2"))

        assert len(manager.configs) == 1


class TestMCPClientManagerAsToolsets:
    """Tests for as_toolsets() method."""

    def test_as_toolsets_creates_stdio_server(self) -> None:
        """Test that as_toolsets creates MCPServerStdio for stdio transport."""
        configs = [
            MCPServerConfig(
                name="fs",
                transport="stdio",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        assert isinstance(toolsets[0], MCPServerStdio)

    def test_as_toolsets_creates_sse_server(self) -> None:
        """Test that as_toolsets creates MCPServerSSE for SSE transport."""
        configs = [
            MCPServerConfig(
                name="web",
                transport="sse",
                url="http://localhost:8080/sse",
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        assert isinstance(toolsets[0], MCPServerSSE)

    def test_as_toolsets_with_tool_prefix(self) -> None:
        """Test that tool_prefix is applied to servers."""
        configs = [
            MCPServerConfig(
                name="fs",
                transport="stdio",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem", "/path"],
                tool_prefix="fs",
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        # The tool_prefix is stored internally by pydantic-ai

    def test_as_toolsets_multiple_servers(self) -> None:
        """Test creating multiple servers."""
        configs = [
            MCPServerConfig(name="server1", transport="stdio", command="cmd1"),
            MCPServerConfig(name="server2", transport="sse", url="http://localhost/sse"),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 2
        assert isinstance(toolsets[0], MCPServerStdio)
        assert isinstance(toolsets[1], MCPServerSSE)

    def test_as_toolsets_empty_configs(self) -> None:
        """Test as_toolsets with no configs returns empty list."""
        manager = MCPClientManager()
        toolsets = manager.as_toolsets()
        assert toolsets == []

    def test_as_toolsets_stdio_missing_command(self) -> None:
        """Test that ValueError is raised when stdio config missing command."""
        configs = [MCPServerConfig(name="broken", transport="stdio")]
        manager = MCPClientManager(configs)

        with pytest.raises(ValueError, match="Command required for stdio transport"):
            manager.as_toolsets()

    def test_as_toolsets_sse_missing_url(self) -> None:
        """Test that ValueError is raised when SSE config missing URL."""
        configs = [MCPServerConfig(name="broken", transport="sse")]
        manager = MCPClientManager(configs)

        with pytest.raises(ValueError, match="URL required for SSE transport"):
            manager.as_toolsets()


class TestMCPClientManagerTimeouts:
    """Tests for timeout configuration in MCPClientManager."""

    def test_stdio_server_uses_default_timeouts(self) -> None:
        """Test that stdio server uses default timeout values."""
        configs = [
            MCPServerConfig(
                name="test",
                transport="stdio",
                command="test-cmd",
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        server = toolsets[0]
        assert isinstance(server, MCPServerStdio)
        assert server.timeout == 30.0
        assert server.read_timeout == 300.0

    def test_stdio_server_uses_custom_timeouts(self) -> None:
        """Test that stdio server uses custom timeout values from config."""
        configs = [
            MCPServerConfig(
                name="slow-server",
                transport="stdio",
                command="slow-cmd",
                timeout=60.0,
                read_timeout=600.0,
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        server = toolsets[0]
        assert isinstance(server, MCPServerStdio)
        assert server.timeout == 60.0
        assert server.read_timeout == 600.0

    def test_sse_server_uses_default_timeouts(self) -> None:
        """Test that SSE server uses default timeout values."""
        configs = [
            MCPServerConfig(
                name="test",
                transport="sse",
                url="http://localhost:8080/sse",
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        server = toolsets[0]
        assert isinstance(server, MCPServerSSE)
        assert server.timeout == 30.0
        assert server.read_timeout == 300.0

    def test_sse_server_uses_custom_timeouts(self) -> None:
        """Test that SSE server uses custom timeout values from config."""
        configs = [
            MCPServerConfig(
                name="slow-server",
                transport="sse",
                url="http://localhost:8080/sse",
                timeout=120.0,
                read_timeout=1200.0,
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        server = toolsets[0]
        assert isinstance(server, MCPServerSSE)
        assert server.timeout == 120.0
        assert server.read_timeout == 1200.0


class TestMCPClientManagerFromFile:
    """Tests for from_mcp_json() and add_from_file() methods."""

    def test_from_mcp_json_creates_manager(self, tmp_path: Path) -> None:
        """Test that from_mcp_json creates a manager with loaded configs."""
        mcp_json = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                },
                "web-search": {
                    "url": "http://localhost:8080/sse",
                },
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        manager = MCPClientManager.from_mcp_json(config_file)

        assert len(manager.configs) == 2
        names = {c.name for c in manager.configs}
        assert names == {"filesystem", "web-search"}

    def test_from_mcp_json_with_string_path(self, tmp_path: Path) -> None:
        """Test from_mcp_json with string path."""
        mcp_json = {"mcpServers": {"test": {"command": "test-cmd"}}}
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        manager = MCPClientManager.from_mcp_json(str(config_file))

        assert len(manager.configs) == 1
        assert manager.configs[0].name == "test"

    def test_from_mcp_json_file_not_found(self) -> None:
        """Test that from_mcp_json raises error for missing file."""
        with pytest.raises(MCPFileNotFoundError):
            MCPClientManager.from_mcp_json("/nonexistent/.mcp.json")

    def test_add_from_file_appends_configs(self, tmp_path: Path) -> None:
        """Test that add_from_file appends to existing configs."""
        # Create initial manager with one config
        initial_config = MCPServerConfig(name="existing", command="existing-cmd")
        manager = MCPClientManager([initial_config])

        # Create .mcp.json with another config
        mcp_json = {"mcpServers": {"new-server": {"command": "new-cmd"}}}
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        manager.add_from_file(config_file)

        assert len(manager.configs) == 2
        names = {c.name for c in manager.configs}
        assert names == {"existing", "new-server"}

    def test_add_from_file_preserves_existing(self, tmp_path: Path) -> None:
        """Test that add_from_file preserves existing config details."""
        # Create initial manager with specific config
        initial_config = MCPServerConfig(
            name="existing", command="existing-cmd", args=["--flag"], tool_prefix="ex"
        )
        manager = MCPClientManager([initial_config])

        # Create empty .mcp.json
        mcp_json = {"mcpServers": {}}
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        manager.add_from_file(config_file)

        # Original config should be unchanged
        assert len(manager.configs) == 1
        assert manager.configs[0].name == "existing"
        assert manager.configs[0].command == "existing-cmd"
        assert manager.configs[0].args == ["--flag"]
        assert manager.configs[0].tool_prefix == "ex"

    def test_add_from_file_multiple_files(self, tmp_path: Path) -> None:
        """Test adding configs from multiple files."""
        manager = MCPClientManager()

        # First file
        file1 = tmp_path / "project.mcp.json"
        file1.write_text(json.dumps({"mcpServers": {"server1": {"command": "cmd1"}}}))

        # Second file
        file2 = tmp_path / "user.mcp.json"
        file2.write_text(json.dumps({"mcpServers": {"server2": {"command": "cmd2"}}}))

        manager.add_from_file(file1)
        manager.add_from_file(file2)

        assert len(manager.configs) == 2
        names = {c.name for c in manager.configs}
        assert names == {"server1", "server2"}

    def test_add_from_file_raises_for_missing_file(self, tmp_path: Path) -> None:
        """Test that add_from_file raises error for missing file."""
        manager = MCPClientManager()

        with pytest.raises(MCPFileNotFoundError):
            manager.add_from_file(tmp_path / "nonexistent.mcp.json")


class TestMCPClientManagerStreamableHTTP:
    """Tests for Streamable HTTP transport."""

    def test_as_toolsets_creates_streamable_http_server(self) -> None:
        """Test that as_toolsets creates MCPServerStreamableHTTP for streamable_http transport."""
        configs = [
            MCPServerConfig(
                name="http-server",
                transport="streamable_http",
                url="http://localhost:8080/mcp",
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        assert isinstance(toolsets[0], MCPServerStreamableHTTP)

    def test_as_toolsets_streamable_http_missing_url(self) -> None:
        """Test that ValueError is raised when streamable_http config missing URL."""
        configs = [MCPServerConfig(name="broken", transport="streamable_http")]
        manager = MCPClientManager(configs)

        with pytest.raises(ValueError, match="URL required for Streamable HTTP transport"):
            manager.as_toolsets()

    def test_streamable_http_server_uses_custom_timeouts(self) -> None:
        """Test that streamable_http server uses custom timeout values from config."""
        configs = [
            MCPServerConfig(
                name="slow-server",
                transport="streamable_http",
                url="http://localhost:8080/mcp",
                timeout=120.0,
                read_timeout=1200.0,
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        server = toolsets[0]
        assert isinstance(server, MCPServerStreamableHTTP)
        assert server.timeout == 120.0
        assert server.read_timeout == 1200.0

    def test_streamable_http_server_uses_default_timeouts(self) -> None:
        """Test that streamable_http server uses default timeout values."""
        configs = [
            MCPServerConfig(
                name="test",
                transport="streamable_http",
                url="http://localhost:8080/mcp",
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 1
        server = toolsets[0]
        assert isinstance(server, MCPServerStreamableHTTP)
        assert server.timeout == 30.0
        assert server.read_timeout == 300.0

    def test_mixed_transport_types(self) -> None:
        """Test creating servers with all three transport types."""
        configs = [
            MCPServerConfig(name="stdio-server", transport="stdio", command="cmd1"),
            MCPServerConfig(name="sse-server", transport="sse", url="http://localhost/sse"),
            MCPServerConfig(
                name="http-server", transport="streamable_http", url="http://localhost/mcp"
            ),
        ]
        manager = MCPClientManager(configs)
        toolsets = manager.as_toolsets()

        assert len(toolsets) == 3
        assert isinstance(toolsets[0], MCPServerStdio)
        assert isinstance(toolsets[1], MCPServerSSE)
        assert isinstance(toolsets[2], MCPServerStreamableHTTP)


class TestMCPClientManagerGetServer:
    """Tests for get_server() method."""

    def test_get_server_by_name(self) -> None:
        """Test getting a server by name."""
        configs = [
            MCPServerConfig(name="server1", transport="stdio", command="cmd1"),
            MCPServerConfig(name="server2", transport="sse", url="http://localhost/sse"),
        ]
        manager = MCPClientManager(configs)

        server = manager.get_server("server1")
        assert isinstance(server, MCPServerStdio)

        server2 = manager.get_server("server2")
        assert isinstance(server2, MCPServerSSE)

    def test_get_server_not_found(self) -> None:
        """Test that get_server raises error for unknown server."""
        configs = [MCPServerConfig(name="server1", transport="stdio", command="cmd1")]
        manager = MCPClientManager(configs)

        with pytest.raises(MCPServerNotFoundError, match="Server not found: unknown"):
            manager.get_server("unknown")


class TestMCPConnectionResult:
    """Tests for MCPConnectionResult model."""

    def test_successful_result(self) -> None:
        """Test creating a successful connection result."""
        tools = [
            MCPToolInfo(name="tool1", description="First tool"),
            MCPToolInfo(name="tool2", description="Second tool", input_schema={"type": "object"}),
        ]
        result = MCPConnectionResult(
            server_name="test-server",
            success=True,
            is_running=True,
            tools=tools,
            tool_count=2,
        )

        assert result.server_name == "test-server"
        assert result.success is True
        assert result.is_running is True
        assert len(result.tools) == 2
        assert result.tool_count == 2
        assert result.error is None
        assert result.error_type is None

    def test_failed_result(self) -> None:
        """Test creating a failed connection result."""
        result = MCPConnectionResult(
            server_name="test-server",
            success=False,
            error="Connection refused",
            error_type="ConnectionError",
        )

        assert result.server_name == "test-server"
        assert result.success is False
        assert result.is_running is False
        assert result.tools == []
        assert result.tool_count == 0
        assert result.error == "Connection refused"
        assert result.error_type == "ConnectionError"


class TestMCPToolInfo:
    """Tests for MCPToolInfo model."""

    def test_tool_info_minimal(self) -> None:
        """Test creating tool info with minimal fields."""
        tool = MCPToolInfo(name="my-tool")

        assert tool.name == "my-tool"
        assert tool.description is None
        assert tool.input_schema is None

    def test_tool_info_full(self) -> None:
        """Test creating tool info with all fields."""
        schema = {"type": "object", "properties": {"arg1": {"type": "string"}}}
        tool = MCPToolInfo(
            name="my-tool",
            description="A useful tool",
            input_schema=schema,
        )

        assert tool.name == "my-tool"
        assert tool.description == "A useful tool"
        assert tool.input_schema == schema


class TestMCPConnectionTesting:
    """Tests for connection testing methods."""

    @pytest.mark.asyncio
    async def test_connection_success(self) -> None:
        """Test successful connection returns proper result."""
        from unittest.mock import AsyncMock, MagicMock, patch

        configs = [MCPServerConfig(name="test-server", transport="stdio", command="test-cmd")]
        manager = MCPClientManager(configs)

        # Mock tool info returned by list_tools
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "A test tool"
        mock_tool.input_schema = {"type": "object"}

        # Create mock server
        mock_server = AsyncMock()
        mock_server.is_running = True
        mock_server.list_tools = AsyncMock(return_value=[mock_tool])
        mock_server.__aenter__ = AsyncMock(return_value=mock_server)
        mock_server.__aexit__ = AsyncMock(return_value=None)

        with patch.object(manager, "_create_server", return_value=mock_server):
            result = await manager.test_connection("test-server")

        assert result.success is True
        assert result.server_name == "test-server"
        assert result.is_running is True
        assert result.tool_count == 1
        assert len(result.tools) == 1
        assert result.tools[0].name == "test_tool"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_connection_server_not_found(self) -> None:
        """Test connection to non-existent server returns error result."""
        manager = MCPClientManager([])

        result = await manager.test_connection("nonexistent")

        assert result.success is False
        assert result.server_name == "nonexistent"
        assert result.error == "Server not found: nonexistent"
        assert result.error_type == "MCPServerNotFoundError"

    @pytest.mark.asyncio
    async def test_connection_timeout(self) -> None:
        """Test connection timeout returns error result."""
        from unittest.mock import AsyncMock, patch

        configs = [MCPServerConfig(name="slow-server", transport="stdio", command="slow-cmd")]
        manager = MCPClientManager(configs)

        # Create mock server that raises TimeoutError
        mock_server = AsyncMock()
        mock_server.__aenter__ = AsyncMock(side_effect=TimeoutError("Connection timed out"))
        mock_server.__aexit__ = AsyncMock(return_value=None)

        with patch.object(manager, "_create_server", return_value=mock_server):
            result = await manager.test_connection("slow-server")

        assert result.success is False
        assert result.server_name == "slow-server"
        assert "timed out" in result.error
        assert result.error_type == "MCPConnectionTimeoutError"

    @pytest.mark.asyncio
    async def test_connection_generic_error(self) -> None:
        """Test generic connection error returns error result."""
        from unittest.mock import AsyncMock, patch

        configs = [MCPServerConfig(name="broken-server", transport="stdio", command="broken-cmd")]
        manager = MCPClientManager(configs)

        # Create mock server that raises a generic error
        mock_server = AsyncMock()
        mock_server.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))
        mock_server.__aexit__ = AsyncMock(return_value=None)

        with patch.object(manager, "_create_server", return_value=mock_server):
            result = await manager.test_connection("broken-server")

        assert result.success is False
        assert result.server_name == "broken-server"
        assert "Connection refused" in result.error
        assert result.error_type == "ConnectionRefusedError"

    @pytest.mark.asyncio
    async def test_all_connections_success(self) -> None:
        """Test concurrent connection testing with all success."""
        from unittest.mock import AsyncMock, MagicMock, patch

        configs = [
            MCPServerConfig(name="server1", transport="stdio", command="cmd1"),
            MCPServerConfig(name="server2", transport="stdio", command="cmd2"),
        ]
        manager = MCPClientManager(configs)

        # Mock tool info
        mock_tool = MagicMock()
        mock_tool.name = "tool"
        mock_tool.description = "desc"
        mock_tool.input_schema = {}

        # Create mock server
        mock_server = AsyncMock()
        mock_server.is_running = True
        mock_server.list_tools = AsyncMock(return_value=[mock_tool])
        mock_server.__aenter__ = AsyncMock(return_value=mock_server)
        mock_server.__aexit__ = AsyncMock(return_value=None)

        with patch.object(manager, "_create_server", return_value=mock_server):
            results = await manager.test_all_connections()

        assert len(results) == 2
        assert "server1" in results
        assert "server2" in results
        assert results["server1"].success is True
        assert results["server2"].success is True

    @pytest.mark.asyncio
    async def test_all_connections_partial_failure(self) -> None:
        """Test concurrent connection testing with mixed results."""
        from unittest.mock import AsyncMock, MagicMock, patch

        configs = [
            MCPServerConfig(name="good-server", transport="stdio", command="good-cmd"),
            MCPServerConfig(name="bad-server", transport="stdio", command="bad-cmd"),
        ]
        manager = MCPClientManager(configs)

        # Mock tool info for successful connection
        mock_tool = MagicMock()
        mock_tool.name = "tool"
        mock_tool.description = "desc"
        mock_tool.input_schema = {}

        async def mock_test_connection(server_name: str) -> MCPConnectionResult:
            if server_name == "good-server":
                return MCPConnectionResult(
                    server_name=server_name,
                    success=True,
                    is_running=True,
                    tools=[MCPToolInfo(name="tool", description="desc")],
                    tool_count=1,
                )
            else:
                return MCPConnectionResult(
                    server_name=server_name,
                    success=False,
                    error="Connection failed",
                    error_type="ConnectionError",
                )

        with patch.object(manager, "test_connection", side_effect=mock_test_connection):
            results = await manager.test_all_connections()

        assert len(results) == 2
        assert results["good-server"].success is True
        assert results["bad-server"].success is False
        assert results["bad-server"].error == "Connection failed"
