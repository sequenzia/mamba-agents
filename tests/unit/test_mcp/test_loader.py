"""Tests for MCP configuration loader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mamba_agents.mcp import (
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
    load_mcp_json,
)


class TestLoadMcpJson:
    """Tests for load_mcp_json function."""

    def test_load_stdio_server(self, tmp_path: Path) -> None:
        """Test loading a basic stdio server."""
        mcp_json = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/project"],
                }
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].name == "filesystem"
        assert configs[0].transport == "stdio"
        assert configs[0].command == "npx"
        assert configs[0].args == ["-y", "@modelcontextprotocol/server-filesystem", "/project"]

    def test_load_sse_server(self, tmp_path: Path) -> None:
        """Test loading an SSE server."""
        mcp_json = {
            "mcpServers": {
                "web-search": {
                    "url": "http://localhost:8080/sse",
                }
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].name == "web-search"
        assert configs[0].transport == "sse"
        assert configs[0].url == "http://localhost:8080/sse"

    def test_load_multiple_servers(self, tmp_path: Path) -> None:
        """Test loading multiple servers from one file."""
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

        configs = load_mcp_json(config_file)

        assert len(configs) == 2
        names = {c.name for c in configs}
        assert names == {"filesystem", "web-search"}

    def test_load_with_env_vars(self, tmp_path: Path) -> None:
        """Test loading server with env mapping."""
        mcp_json = {
            "mcpServers": {
                "myserver": {
                    "command": "mycommand",
                    "env": {"NODE_ENV": "production", "DEBUG": "true"},
                }
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].env_vars == {"NODE_ENV": "production", "DEBUG": "true"}

    def test_load_with_tool_prefix(self, tmp_path: Path) -> None:
        """Test loading server with tool_prefix (extended field)."""
        mcp_json = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                    "tool_prefix": "fs",
                }
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].tool_prefix == "fs"

    def test_load_with_env_file(self, tmp_path: Path) -> None:
        """Test loading server with env_file (extended field)."""
        mcp_json = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "env_file": ".env.local",
                }
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].env_file == ".env.local"

    def test_load_empty_servers(self, tmp_path: Path) -> None:
        """Test loading file with empty mcpServers."""
        mcp_json = {"mcpServers": {}}
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert configs == []

    def test_load_supports_tilde_expansion(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that ~ in path expands to home directory."""
        mcp_json = {"mcpServers": {"test": {"command": "test-cmd"}}}
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        # Mock expanduser to return our temp path
        monkeypatch.setattr(
            Path, "expanduser", lambda self: tmp_path / ".mcp.json" if "~" in str(self) else self
        )

        configs = load_mcp_json("~/.mcp.json")

        assert len(configs) == 1

    def test_file_not_found(self) -> None:
        """Test MCPFileNotFoundError when file doesn't exist."""
        with pytest.raises(MCPFileNotFoundError, match="MCP config file not found"):
            load_mcp_json("/nonexistent/path/.mcp.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        """Test MCPFileParseError when file is not valid JSON."""
        config_file = tmp_path / ".mcp.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(MCPFileParseError, match="Invalid JSON"):
            load_mcp_json(config_file)

    def test_missing_command_and_url(self, tmp_path: Path) -> None:
        """Test validation error when neither command nor url is specified."""
        mcp_json = {"mcpServers": {"broken": {"args": ["arg1", "arg2"]}}}
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        with pytest.raises(
            MCPServerValidationError, match="Either 'command' or 'url' must be specified"
        ):
            load_mcp_json(config_file)

    def test_both_command_and_url(self, tmp_path: Path) -> None:
        """Test validation error when both command and url are specified."""
        mcp_json = {
            "mcpServers": {"broken": {"command": "npx", "url": "http://localhost:8080/sse"}}
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        with pytest.raises(
            MCPServerValidationError, match="Cannot specify both 'command' and 'url'"
        ):
            load_mcp_json(config_file)

    def test_load_with_string_path(self, tmp_path: Path) -> None:
        """Test loading with string path (not Path object)."""
        mcp_json = {"mcpServers": {"test": {"command": "test-cmd"}}}
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(str(config_file))

        assert len(configs) == 1
        assert configs[0].name == "test"

    def test_load_full_example(self, tmp_path: Path) -> None:
        """Test loading a complete example with all fields."""
        mcp_json = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/project"],
                    "env": {"NODE_ENV": "production"},
                    "tool_prefix": "fs",
                    "env_file": ".env.local",
                },
                "web-search": {"url": "http://localhost:8080/sse", "tool_prefix": "web"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 2

        # Find configs by name
        fs_config = next(c for c in configs if c.name == "filesystem")
        web_config = next(c for c in configs if c.name == "web-search")

        # Verify filesystem config
        assert fs_config.transport == "stdio"
        assert fs_config.command == "npx"
        assert fs_config.args == ["-y", "@modelcontextprotocol/server-filesystem", "/project"]
        assert fs_config.env_vars == {"NODE_ENV": "production"}
        assert fs_config.tool_prefix == "fs"
        assert fs_config.env_file == ".env.local"

        # Verify web-search config
        assert web_config.transport == "sse"
        assert web_config.url == "http://localhost:8080/sse"
        assert web_config.tool_prefix == "web"


class TestTransportDetection:
    """Tests for URL-based transport detection."""

    def test_sse_url_detected(self, tmp_path: Path) -> None:
        """Test that URLs ending with /sse are detected as SSE transport."""
        mcp_json = {
            "mcpServers": {
                "sse-server": {"url": "http://localhost:8080/sse"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].transport == "sse"

    def test_streamable_http_url_detected(self, tmp_path: Path) -> None:
        """Test that URLs not ending with /sse are detected as Streamable HTTP."""
        mcp_json = {
            "mcpServers": {
                "http-server": {"url": "http://localhost:8080/mcp"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].transport == "streamable_http"

    def test_sse_url_with_trailing_slash(self, tmp_path: Path) -> None:
        """Test that /sse/ (with trailing slash) is still detected as SSE."""
        mcp_json = {
            "mcpServers": {
                "sse-server": {"url": "http://localhost:8080/sse/"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].transport == "sse"

    def test_mixed_transports_detected(self, tmp_path: Path) -> None:
        """Test detecting all three transport types in one file."""
        mcp_json = {
            "mcpServers": {
                "stdio-server": {"command": "npx", "args": ["-y", "some-server"]},
                "sse-server": {"url": "http://localhost:8080/sse"},
                "http-server": {"url": "http://localhost:8080/mcp"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 3

        # Find configs by name
        stdio_config = next(c for c in configs if c.name == "stdio-server")
        sse_config = next(c for c in configs if c.name == "sse-server")
        http_config = next(c for c in configs if c.name == "http-server")

        assert stdio_config.transport == "stdio"
        assert sse_config.transport == "sse"
        assert http_config.transport == "streamable_http"

    def test_api_url_detected_as_streamable_http(self, tmp_path: Path) -> None:
        """Test that /api URLs are detected as Streamable HTTP."""
        mcp_json = {
            "mcpServers": {
                "api-server": {"url": "http://localhost:8080/api/v1/mcp"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].transport == "streamable_http"

    def test_root_url_detected_as_streamable_http(self, tmp_path: Path) -> None:
        """Test that root URLs are detected as Streamable HTTP."""
        mcp_json = {
            "mcpServers": {
                "root-server": {"url": "http://localhost:8080"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].transport == "streamable_http"

    def test_events_sse_path_detected_as_sse(self, tmp_path: Path) -> None:
        """Test that /events/sse is detected as SSE."""
        mcp_json = {
            "mcpServers": {
                "events-server": {"url": "http://localhost:8080/events/sse"},
            }
        }
        config_file = tmp_path / ".mcp.json"
        config_file.write_text(json.dumps(mcp_json))

        configs = load_mcp_json(config_file)

        assert len(configs) == 1
        assert configs[0].transport == "sse"
