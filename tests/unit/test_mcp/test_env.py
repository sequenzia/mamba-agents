"""Tests for MCP environment variable resolution."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mamba_agents.mcp.config import MCPServerConfig
from mamba_agents.mcp.env import resolve_server_env

if TYPE_CHECKING:
    from pytest import MonkeyPatch


class TestResolveServerEnv:
    """Tests for resolve_server_env function."""

    def test_no_customization_returns_none(self) -> None:
        """Test that no env_file or env_vars returns None."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
        )
        result = resolve_server_env(config)
        assert result is None

    def test_env_vars_only(self, monkeypatch: MonkeyPatch) -> None:
        """Test that env_vars are included in result."""
        # Clear some env vars to have predictable test
        monkeypatch.setenv("BASE_VAR", "base_value")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_vars={"MY_VAR": "my_value", "ANOTHER_VAR": "another_value"},
        )
        result = resolve_server_env(config)

        assert result is not None
        assert result["MY_VAR"] == "my_value"
        assert result["ANOTHER_VAR"] == "another_value"
        # System env should be included
        assert result["BASE_VAR"] == "base_value"

    def test_env_file_only(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that env_file contents are loaded."""
        # Set a base env var
        monkeypatch.setenv("BASE_VAR", "base_value")

        # Create a .env file
        env_file = tmp_path / ".env"
        env_file.write_text("FILE_VAR=file_value\nANOTHER_FILE_VAR=another_file_value\n")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_file=env_file,
        )
        result = resolve_server_env(config)

        assert result is not None
        assert result["FILE_VAR"] == "file_value"
        assert result["ANOTHER_FILE_VAR"] == "another_file_value"
        # System env should be included
        assert result["BASE_VAR"] == "base_value"

    def test_env_vars_override_env_file(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that env_vars take precedence over env_file."""
        monkeypatch.setenv("BASE_VAR", "base_value")

        # Create a .env file with a var that will be overridden
        env_file = tmp_path / ".env"
        env_file.write_text("SHARED_VAR=from_file\nFILE_ONLY=file_value\n")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_file=env_file,
            env_vars={"SHARED_VAR": "from_env_vars", "VARS_ONLY": "vars_value"},
        )
        result = resolve_server_env(config)

        assert result is not None
        # env_vars should override env_file
        assert result["SHARED_VAR"] == "from_env_vars"
        # File-only var should still be present
        assert result["FILE_ONLY"] == "file_value"
        # env_vars-only var should be present
        assert result["VARS_ONLY"] == "vars_value"
        # System env should be included
        assert result["BASE_VAR"] == "base_value"

    def test_env_file_overrides_system_env(self, tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
        """Test that env_file overrides system environment."""
        monkeypatch.setenv("SHARED_VAR", "from_system")

        # Create a .env file that overrides the system var
        env_file = tmp_path / ".env"
        env_file.write_text("SHARED_VAR=from_file\n")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_file=env_file,
        )
        result = resolve_server_env(config)

        assert result is not None
        # env_file should override system env
        assert result["SHARED_VAR"] == "from_file"

    def test_env_vars_override_system_env(self, monkeypatch: MonkeyPatch) -> None:
        """Test that env_vars override system environment."""
        monkeypatch.setenv("SHARED_VAR", "from_system")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_vars={"SHARED_VAR": "from_env_vars"},
        )
        result = resolve_server_env(config)

        assert result is not None
        # env_vars should override system env
        assert result["SHARED_VAR"] == "from_env_vars"

    def test_missing_env_file_raises_error(self, tmp_path: Path) -> None:
        """Test that missing env_file raises FileNotFoundError."""
        nonexistent_file = tmp_path / "nonexistent.env"

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_file=nonexistent_file,
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            resolve_server_env(config)

        assert "env_file not found" in str(exc_info.value)

    def test_env_file_as_string_path(self, tmp_path: Path) -> None:
        """Test that env_file accepts string path."""
        env_file = tmp_path / ".env"
        env_file.write_text("STRING_PATH_VAR=value\n")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_file=str(env_file),  # Pass as string
        )
        result = resolve_server_env(config)

        assert result is not None
        assert result["STRING_PATH_VAR"] == "value"

    def test_system_env_preserved(self, monkeypatch: MonkeyPatch) -> None:
        """Test that system environment variables are preserved."""
        monkeypatch.setenv("SYS_VAR_1", "value1")
        monkeypatch.setenv("SYS_VAR_2", "value2")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_vars={"NEW_VAR": "new_value"},
        )
        result = resolve_server_env(config)

        assert result is not None
        assert result["SYS_VAR_1"] == "value1"
        assert result["SYS_VAR_2"] == "value2"
        assert result["NEW_VAR"] == "new_value"

    def test_empty_env_vars_dict_triggers_resolution(self, monkeypatch: MonkeyPatch) -> None:
        """Test that empty env_vars dict still triggers env resolution."""
        monkeypatch.setenv("BASE_VAR", "base_value")

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-cmd",
            env_vars={},  # Empty dict
        )
        result = resolve_server_env(config)

        # Should return a dict (not None) since env_vars was explicitly set
        assert result is not None
        assert result["BASE_VAR"] == "base_value"


class TestMCPServerConfigEnvFields:
    """Tests for MCPServerConfig env_file and env_vars fields."""

    def test_default_env_file_is_none(self) -> None:
        """Test that env_file defaults to None."""
        config = MCPServerConfig(name="test", command="test-cmd")
        assert config.env_file is None

    def test_default_env_vars_is_none(self) -> None:
        """Test that env_vars defaults to None."""
        config = MCPServerConfig(name="test", command="test-cmd")
        assert config.env_vars is None

    def test_env_file_accepts_path(self, tmp_path: Path) -> None:
        """Test that env_file accepts Path objects."""
        env_path = tmp_path / ".env"
        config = MCPServerConfig(
            name="test",
            command="test-cmd",
            env_file=env_path,
        )
        assert config.env_file == env_path

    def test_env_file_accepts_string(self) -> None:
        """Test that env_file accepts string paths."""
        config = MCPServerConfig(
            name="test",
            command="test-cmd",
            env_file="/path/to/.env",
        )
        assert config.env_file == "/path/to/.env"

    def test_env_vars_accepts_dict(self) -> None:
        """Test that env_vars accepts dict."""
        config = MCPServerConfig(
            name="test",
            command="test-cmd",
            env_vars={"KEY1": "value1", "KEY2": "value2"},
        )
        assert config.env_vars == {"KEY1": "value1", "KEY2": "value2"}
