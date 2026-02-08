"""Tests for subagent markdown config loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from mamba_agents.subagents.config import SubagentConfig
from mamba_agents.subagents.errors import SubagentConfigError
from mamba_agents.subagents.loader import (
    _normalize_keys,
    _parse_frontmatter,
    discover_subagents,
    load_subagent_config,
)


class TestParseFrontmatter:
    """Tests for _parse_frontmatter helper."""

    def test_basic_frontmatter_and_body(self, tmp_path: Path) -> None:
        """Test parsing a file with frontmatter and body."""
        source = "---\nname: test\n---\nBody content here."
        path = tmp_path / "test.md"

        frontmatter, body = _parse_frontmatter(source, path)

        assert frontmatter == {"name": "test"}
        assert body == "Body content here."

    def test_no_frontmatter_raises_error(self, tmp_path: Path) -> None:
        """Test that missing frontmatter raises SubagentConfigError."""
        source = "Just plain markdown without frontmatter."
        path = tmp_path / "bad.md"

        with pytest.raises(SubagentConfigError, match="No YAML frontmatter"):
            _parse_frontmatter(source, path)

    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid YAML in frontmatter raises SubagentConfigError."""
        source = "---\n: invalid: yaml: [unterminated\n---\nBody."
        path = tmp_path / "invalid.md"

        with pytest.raises(SubagentConfigError, match="Invalid YAML"):
            _parse_frontmatter(source, path)

    def test_non_dict_frontmatter_raises_error(self, tmp_path: Path) -> None:
        """Test that non-dict frontmatter raises SubagentConfigError."""
        source = "---\n- list\n- items\n---\nBody."
        path = tmp_path / "list.md"

        with pytest.raises(SubagentConfigError, match="YAML mapping"):
            _parse_frontmatter(source, path)

    def test_empty_body_returns_none(self, tmp_path: Path) -> None:
        """Test that empty body after frontmatter returns None."""
        source = "---\nname: test\n---\n"
        path = tmp_path / "no-body.md"

        frontmatter, body = _parse_frontmatter(source, path)

        assert frontmatter == {"name": "test"}
        assert body is None

    def test_whitespace_only_body_returns_none(self, tmp_path: Path) -> None:
        """Test that whitespace-only body returns None."""
        source = "---\nname: test\n---\n   \n  \n"
        path = tmp_path / "whitespace.md"

        _frontmatter, body = _parse_frontmatter(source, path)

        assert body is None

    def test_empty_frontmatter_returns_empty_dict(self, tmp_path: Path) -> None:
        """Test that empty frontmatter returns an empty dict."""
        source = "---\n\n---\nSome body."
        path = tmp_path / "empty-fm.md"

        frontmatter, body = _parse_frontmatter(source, path)

        assert frontmatter == {}
        assert body == "Some body."


class TestNormalizeKeys:
    """Tests for _normalize_keys helper."""

    def test_hyphenated_keys_mapped_to_underscores(self) -> None:
        """Test that known hyphenated keys are mapped correctly."""
        data = {
            "disallowed-tools": ["run_bash"],
            "max-turns": 100,
            "system-prompt": "hello",
        }

        result = _normalize_keys(data)

        assert result == {
            "disallowed_tools": ["run_bash"],
            "max_turns": 100,
            "system_prompt": "hello",
        }

    def test_non_hyphenated_keys_pass_through(self) -> None:
        """Test that non-hyphenated keys pass through unchanged."""
        data = {"name": "test", "description": "desc", "model": "gpt-4"}

        result = _normalize_keys(data)

        assert result == {"name": "test", "description": "desc", "model": "gpt-4"}

    def test_unknown_hyphenated_keys_normalized(self) -> None:
        """Test that unknown hyphenated keys are also normalized."""
        data = {"some-custom-key": "value"}

        result = _normalize_keys(data)

        assert result == {"some_custom_key": "value"}


class TestLoadSubagentConfig:
    """Tests for load_subagent_config function."""

    def test_parse_valid_agent_file(self, tmp_path: Path) -> None:
        """Test parsing a fully specified agent markdown file."""
        content = """\
---
name: researcher
description: Research subagent for gathering information
tools: [read_file, grep_search]
model: gpt-4
skills: [web-search]
max-turns: 25
---

You are a research assistant. Your job is to gather information.
"""
        agent_file = tmp_path / "researcher.md"
        agent_file.write_text(content)

        config = load_subagent_config(agent_file)

        assert isinstance(config, SubagentConfig)
        assert config.name == "researcher"
        assert config.description == "Research subagent for gathering information"
        assert config.tools == ["read_file", "grep_search"]
        assert config.model == "gpt-4"
        assert config.skills == ["web-search"]
        assert config.max_turns == 25
        assert config.system_prompt == (
            "You are a research assistant. Your job is to gather information."
        )

    def test_parse_minimal_file(self, tmp_path: Path) -> None:
        """Test parsing a file with only name and description."""
        content = """\
---
name: simple
description: A simple subagent
---
"""
        agent_file = tmp_path / "simple.md"
        agent_file.write_text(content)

        config = load_subagent_config(agent_file)

        assert config.name == "simple"
        assert config.description == "A simple subagent"
        assert config.model is None
        assert config.tools is None
        assert config.disallowed_tools is None
        assert config.system_prompt is None
        assert config.skills is None
        assert config.max_turns == 50  # default

    def test_body_becomes_system_prompt(self, tmp_path: Path) -> None:
        """Test that markdown body becomes system_prompt."""
        content = """\
---
name: writer
description: Writing subagent
---

You are a skilled writer. Focus on clarity and conciseness.

Use active voice whenever possible.
"""
        agent_file = tmp_path / "writer.md"
        agent_file.write_text(content)

        config = load_subagent_config(agent_file)

        assert config.system_prompt is not None
        assert "skilled writer" in config.system_prompt
        assert "active voice" in config.system_prompt

    def test_frontmatter_system_prompt_overrides_body(self, tmp_path: Path) -> None:
        """Test that system_prompt in frontmatter takes precedence over body."""
        content = """\
---
name: explicit
description: Explicit prompt subagent
system-prompt: This is the explicit prompt.
---

This body should be ignored.
"""
        agent_file = tmp_path / "explicit.md"
        agent_file.write_text(content)

        config = load_subagent_config(agent_file)

        assert config.system_prompt == "This is the explicit prompt."

    def test_hyphenated_keys_mapped(self, tmp_path: Path) -> None:
        """Test that hyphenated YAML keys are mapped to Python underscores."""
        content = """\
---
name: guarded
description: Guarded subagent
disallowed-tools: [run_bash, delete_file]
max-turns: 10
---
"""
        agent_file = tmp_path / "guarded.md"
        agent_file.write_text(content)

        config = load_subagent_config(agent_file)

        assert config.disallowed_tools == ["run_bash", "delete_file"]
        assert config.max_turns == 10

    def test_missing_name_raises_error(self, tmp_path: Path) -> None:
        """Test that missing name field raises SubagentConfigError."""
        content = """\
---
description: No name provided
---
"""
        agent_file = tmp_path / "noname.md"
        agent_file.write_text(content)

        with pytest.raises(SubagentConfigError, match="Validation failed"):
            load_subagent_config(agent_file)

    def test_missing_description_raises_error(self, tmp_path: Path) -> None:
        """Test that missing description field raises SubagentConfigError."""
        content = """\
---
name: nodesc
---
"""
        agent_file = tmp_path / "nodesc.md"
        agent_file.write_text(content)

        with pytest.raises(SubagentConfigError, match="Validation failed"):
            load_subagent_config(agent_file)

    def test_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid YAML raises SubagentConfigError."""
        content = """\
---
name: [unterminated
---
Body text.
"""
        agent_file = tmp_path / "bad.md"
        agent_file.write_text(content)

        with pytest.raises(SubagentConfigError, match="Invalid YAML"):
            load_subagent_config(agent_file)

    def test_no_frontmatter_raises_error(self, tmp_path: Path) -> None:
        """Test that a file without frontmatter raises SubagentConfigError."""
        content = "Just plain markdown content without any frontmatter."
        agent_file = tmp_path / "plain.md"
        agent_file.write_text(content)

        with pytest.raises(SubagentConfigError, match="No YAML frontmatter"):
            load_subagent_config(agent_file)

    def test_file_not_found_raises_error(self, tmp_path: Path) -> None:
        """Test that a missing file raises SubagentConfigError."""
        missing_file = tmp_path / "nonexistent.md"

        with pytest.raises(SubagentConfigError, match="Cannot read file"):
            load_subagent_config(missing_file)

    def test_file_without_body_valid(self, tmp_path: Path) -> None:
        """Test that a file without body is valid with system_prompt as None."""
        content = """\
---
name: metadata-only
description: Only metadata, no prompt
model: gpt-4
---
"""
        agent_file = tmp_path / "metadata-only.md"
        agent_file.write_text(content)

        config = load_subagent_config(agent_file)

        assert config.name == "metadata-only"
        assert config.system_prompt is None


class TestDiscoverSubagents:
    """Tests for discover_subagents function."""

    def _write_agent_file(self, directory: Path, name: str, description: str) -> Path:
        """Helper to write a minimal agent file."""
        directory.mkdir(parents=True, exist_ok=True)
        content = f"---\nname: {name}\ndescription: {description}\n---\n"
        path = directory / f"{name}.md"
        path.write_text(content)
        return path

    def test_discover_from_project_directory(self, tmp_path: Path) -> None:
        """Test discovery from project-level .mamba/agents/ directory."""
        project_dir = tmp_path / ".mamba" / "agents"
        self._write_agent_file(project_dir, "agent-a", "First agent")
        self._write_agent_file(project_dir, "agent-b", "Second agent")

        configs = discover_subagents(project_dir=project_dir, user_dir=tmp_path / "empty")

        assert len(configs) == 2
        names = {c.name for c in configs}
        assert names == {"agent-a", "agent-b"}

    def test_discover_from_user_directory(self, tmp_path: Path) -> None:
        """Test discovery from user-level ~/.mamba/agents/ directory."""
        user_dir = tmp_path / "user_mamba" / "agents"
        self._write_agent_file(user_dir, "user-agent", "User-level agent")

        configs = discover_subagents(project_dir=tmp_path / "empty", user_dir=user_dir)

        assert len(configs) == 1
        assert configs[0].name == "user-agent"

    def test_discover_from_both_directories(self, tmp_path: Path) -> None:
        """Test discovery from both project and user directories."""
        project_dir = tmp_path / "project" / "agents"
        user_dir = tmp_path / "user" / "agents"
        self._write_agent_file(project_dir, "proj-agent", "Project agent")
        self._write_agent_file(user_dir, "user-agent", "User agent")

        configs = discover_subagents(project_dir=project_dir, user_dir=user_dir)

        assert len(configs) == 2
        names = {c.name for c in configs}
        assert names == {"proj-agent", "user-agent"}

    def test_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        """Test that non-existent directories are silently skipped."""
        configs = discover_subagents(
            project_dir=tmp_path / "nonexistent",
            user_dir=tmp_path / "also-nonexistent",
        )

        assert configs == []

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        """Test that an empty directory returns no configs."""
        empty_dir = tmp_path / "empty_agents"
        empty_dir.mkdir(parents=True)

        configs = discover_subagents(project_dir=empty_dir, user_dir=tmp_path / "nope")

        assert configs == []

    def test_multiple_agent_files_discovered(self, tmp_path: Path) -> None:
        """Test that all .md files in a directory are discovered."""
        agents_dir = tmp_path / "agents"
        self._write_agent_file(agents_dir, "alpha", "Alpha agent")
        self._write_agent_file(agents_dir, "beta", "Beta agent")
        self._write_agent_file(agents_dir, "gamma", "Gamma agent")

        configs = discover_subagents(project_dir=agents_dir, user_dir=tmp_path / "nope")

        assert len(configs) == 3
        names = {c.name for c in configs}
        assert names == {"alpha", "beta", "gamma"}

    def test_non_md_files_ignored(self, tmp_path: Path) -> None:
        """Test that non-.md files are ignored during discovery."""
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir(parents=True)

        # Write an .md file
        self._write_agent_file(agents_dir, "valid", "Valid agent")

        # Write a non-md file
        (agents_dir / "notes.txt").write_text("Not an agent file.")

        configs = discover_subagents(project_dir=agents_dir, user_dir=tmp_path / "nope")

        assert len(configs) == 1
        assert configs[0].name == "valid"

    def test_subdirectories_not_traversed(self, tmp_path: Path) -> None:
        """Test that subdirectories within agents dir are not scanned."""
        agents_dir = tmp_path / "agents"
        self._write_agent_file(agents_dir, "top-level", "Top-level agent")

        # Create a subdirectory with an .md file
        sub_dir = agents_dir / "subdir"
        self._write_agent_file(sub_dir, "nested", "Nested agent")

        configs = discover_subagents(project_dir=agents_dir, user_dir=tmp_path / "nope")

        assert len(configs) == 1
        assert configs[0].name == "top-level"

    def test_files_loaded_in_sorted_order(self, tmp_path: Path) -> None:
        """Test that files are loaded in sorted (alphabetical) order."""
        agents_dir = tmp_path / "agents"
        self._write_agent_file(agents_dir, "zebra", "Zebra agent")
        self._write_agent_file(agents_dir, "alpha", "Alpha agent")
        self._write_agent_file(agents_dir, "middle", "Middle agent")

        configs = discover_subagents(project_dir=agents_dir, user_dir=tmp_path / "nope")

        assert [c.name for c in configs] == ["alpha", "middle", "zebra"]
