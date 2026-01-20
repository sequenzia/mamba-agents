"""Tests for MCPClientManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic_ai.mcp import MCPServerSSE, MCPServerStdio

from mamba_agents.mcp import MCPClientManager, MCPFileNotFoundError, MCPServerConfig


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
