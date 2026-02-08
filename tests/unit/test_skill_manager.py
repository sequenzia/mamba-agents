"""Tests for SkillManager facade."""

from __future__ import annotations

from pathlib import Path

import pytest

from mamba_agents.skills.config import (
    Skill,
    SkillConfig,
    SkillInfo,
    SkillScope,
    TrustLevel,
    ValidationResult,
)
from mamba_agents.skills.errors import (
    SkillConflictError,
    SkillNotFoundError,
)
from mamba_agents.skills.manager import SkillManager, _namespace_tool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_FRONTMATTER = """\
---
name: {name}
description: A test skill called {name}
---

# {name}

Skill body with $ARGUMENTS placeholder.
"""


def _make_info(
    name: str = "test-skill",
    description: str = "A test skill",
    path: Path | None = None,
    scope: SkillScope = SkillScope.PROJECT,
    trust_level: TrustLevel = TrustLevel.TRUSTED,
) -> SkillInfo:
    """Create a minimal SkillInfo for testing."""
    return SkillInfo(
        name=name,
        description=description,
        path=path or Path("/skills/test-skill"),
        scope=scope,
        trust_level=trust_level,
    )


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    path: Path | None = None,
    body: str | None = None,
    is_active: bool = False,
) -> Skill:
    """Create a minimal Skill for testing."""
    skill = Skill(
        info=_make_info(name=name, description=description, path=path),
        body=body,
        is_active=is_active,
    )
    return skill


def _make_skill_dir(
    base_dir: Path,
    name: str,
    description: str = "A test skill",
    body: str | None = None,
) -> Path:
    """Create a skill directory with a valid SKILL.md file."""
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = body or _MINIMAL_FRONTMATTER.format(name=name)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")
    return skill_dir


def _make_config(
    tmp_path: Path,
    *,
    project_dir: Path | None = None,
    user_dir: Path | None = None,
    custom_paths: list[Path] | None = None,
) -> SkillConfig:
    """Build a SkillConfig for testing with temp directories."""
    p_dir = project_dir or (tmp_path / "project" / ".mamba" / "skills")
    u_dir = user_dir or (tmp_path / "user" / ".mamba" / "skills")

    return SkillConfig(
        skills_dirs=[p_dir],
        user_skills_dir=u_dir,
        custom_paths=custom_paths or [],
    )


# ---------------------------------------------------------------------------
# Constructor tests
# ---------------------------------------------------------------------------


class TestSkillManagerInit:
    """Tests for SkillManager constructor."""

    def test_default_config(self) -> None:
        """Test constructor with default (None) config."""
        manager = SkillManager()

        assert manager.config is not None
        assert isinstance(manager.config, SkillConfig)
        assert len(manager) == 0

    def test_custom_config(self, tmp_path: Path) -> None:
        """Test constructor with custom config."""
        config = _make_config(tmp_path)
        manager = SkillManager(config=config)

        assert manager.config is config
        assert len(manager) == 0

    def test_registry_starts_empty(self) -> None:
        """Test that registry is empty on init."""
        manager = SkillManager()

        assert manager.list() == []
        assert manager.registry is not None

    def test_repr_empty(self) -> None:
        """Test repr of empty manager."""
        manager = SkillManager()
        assert repr(manager) == "SkillManager(skills=0, active=0)"


# ---------------------------------------------------------------------------
# Discovery tests
# ---------------------------------------------------------------------------


class TestSkillManagerDiscover:
    """Tests for discover() method."""

    def test_discover_from_project_dir(self, tmp_path: Path) -> None:
        """Test discovering skills from project directory."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill_dir(project_dir, "alpha")
        _make_skill_dir(project_dir, "beta")

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        result = manager.discover()

        assert len(result) == 2
        assert len(manager) == 2
        names = {info.name for info in result}
        assert names == {"alpha", "beta"}

    def test_discover_registers_in_registry(self, tmp_path: Path) -> None:
        """Test that discovered skills are in the registry."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill_dir(project_dir, "my-skill")

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        manager.discover()

        assert manager.get("my-skill") is not None
        assert manager.get("my-skill").info.name == "my-skill"

    def test_discover_no_duplicates_on_repeated_calls(self, tmp_path: Path) -> None:
        """Test that calling discover() twice doesn't create duplicates."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill_dir(project_dir, "alpha")

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        first = manager.discover()
        second = manager.discover()

        assert len(first) == 1
        assert len(second) == 0  # No new skills on second call
        assert len(manager) == 1

    def test_discover_empty_directory(self, tmp_path: Path) -> None:
        """Test discover with no skills in directories."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        result = manager.discover()

        assert result == []
        assert len(manager) == 0

    def test_discover_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test discover with nonexistent directories (no crash)."""
        config = _make_config(tmp_path)
        manager = SkillManager(config=config)

        result = manager.discover()

        assert result == []

    def test_discover_individual_errors_logged_and_skipped(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that individual skill errors don't abort discovery."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        # Create a valid skill
        _make_skill_dir(project_dir, "valid-skill")

        # Create an invalid skill (missing frontmatter)
        invalid_dir = project_dir / "bad-skill"
        invalid_dir.mkdir()
        (invalid_dir / "SKILL.md").write_text("no frontmatter here")

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        with caplog.at_level("ERROR"):
            result = manager.discover()

        # The valid skill should be registered
        assert len(result) == 1
        assert result[0].name == "valid-skill"


# ---------------------------------------------------------------------------
# Registration lifecycle tests
# ---------------------------------------------------------------------------


class TestSkillManagerRegistration:
    """Tests for register() and deregister() methods."""

    def test_register_skill_instance(self) -> None:
        """Test registering a Skill instance."""
        manager = SkillManager()
        skill = _make_skill(name="my-skill")

        manager.register(skill)

        assert manager.get("my-skill") is not None
        assert len(manager) == 1

    def test_register_skill_info(self) -> None:
        """Test registering a SkillInfo instance."""
        manager = SkillManager()
        info = _make_info(name="my-skill")

        manager.register(info)

        assert manager.get("my-skill") is not None
        assert len(manager) == 1

    def test_register_path(self, tmp_path: Path) -> None:
        """Test registering a skill from a path."""
        skill_dir = _make_skill_dir(tmp_path, "path-skill")
        manager = SkillManager()

        manager.register(skill_dir)

        assert manager.get("path-skill") is not None

    def test_register_duplicate_raises(self) -> None:
        """Test that duplicate registration raises SkillConflictError."""
        manager = SkillManager()
        manager.register(_make_skill(name="dup"))

        with pytest.raises(SkillConflictError, match="dup"):
            manager.register(_make_skill(name="dup"))

    def test_deregister_removes_skill(self) -> None:
        """Test that deregister removes a skill from the registry."""
        manager = SkillManager()
        manager.register(_make_skill(name="to-remove"))

        manager.deregister("to-remove")

        assert manager.get("to-remove") is None
        assert len(manager) == 0

    def test_deregister_nonexistent_raises(self) -> None:
        """Test that deregistering a missing skill raises SkillNotFoundError."""
        manager = SkillManager()

        with pytest.raises(SkillNotFoundError, match="nonexistent"):
            manager.deregister("nonexistent")

    def test_deregister_deactivates_active_skill(self, tmp_path: Path) -> None:
        """Test that deregister deactivates an active skill first."""
        skill_dir = _make_skill_dir(tmp_path, "active-skill")
        manager = SkillManager()
        manager.register(skill_dir)

        # Activate the skill
        manager.activate("active-skill")

        # Verify active
        skill = manager.get("active-skill")
        assert skill.is_active

        # Deregister should deactivate first
        manager.deregister("active-skill")
        assert manager.get("active-skill") is None


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------


class TestSkillManagerRetrieval:
    """Tests for get() and list() methods."""

    def test_get_existing_skill(self) -> None:
        """Test getting a registered skill."""
        manager = SkillManager()
        manager.register(_make_skill(name="existing"))

        result = manager.get("existing")

        assert result is not None
        assert result.info.name == "existing"

    def test_get_nonexistent_returns_none(self) -> None:
        """Test getting a missing skill returns None."""
        manager = SkillManager()

        assert manager.get("missing") is None

    def test_list_returns_all_infos(self) -> None:
        """Test listing all registered skill metadata."""
        manager = SkillManager()
        manager.register(_make_skill(name="alpha"))
        manager.register(_make_skill(name="beta"))

        result = manager.list()

        assert len(result) == 2
        names = {info.name for info in result}
        assert names == {"alpha", "beta"}

    def test_list_empty_registry(self) -> None:
        """Test listing returns empty list when no skills registered."""
        manager = SkillManager()

        assert manager.list() == []


# ---------------------------------------------------------------------------
# Activation lifecycle tests
# ---------------------------------------------------------------------------


class TestSkillManagerActivation:
    """Tests for activate() and deactivate() methods."""

    def test_activate_returns_content(self, tmp_path: Path) -> None:
        """Test that activate returns processed skill content."""
        skill_dir = _make_skill_dir(tmp_path, "activatable")
        manager = SkillManager()
        manager.register(skill_dir)

        content = manager.activate("activatable")

        assert isinstance(content, str)
        assert len(content) > 0

    def test_activate_sets_active_flag(self, tmp_path: Path) -> None:
        """Test that activate marks the skill as active."""
        skill_dir = _make_skill_dir(tmp_path, "activatable")
        manager = SkillManager()
        manager.register(skill_dir)

        manager.activate("activatable")

        skill = manager.get("activatable")
        assert skill.is_active

    def test_activate_with_arguments(self, tmp_path: Path) -> None:
        """Test that arguments are substituted into skill content."""
        skill_dir = _make_skill_dir(tmp_path, "arg-skill")
        manager = SkillManager()
        manager.register(skill_dir)

        content = manager.activate("arg-skill", arguments="hello world")

        assert "hello world" in content

    def test_activate_nonexistent_raises(self) -> None:
        """Test that activating a missing skill raises SkillNotFoundError."""
        manager = SkillManager()

        with pytest.raises(SkillNotFoundError, match="ghost"):
            manager.activate("ghost")

    def test_activate_already_active_refreshes(self, tmp_path: Path) -> None:
        """Test that activating an already-active skill refreshes it."""
        skill_dir = _make_skill_dir(tmp_path, "reactivate")
        manager = SkillManager()
        manager.register(skill_dir)

        content1 = manager.activate("reactivate", arguments="first")
        content2 = manager.activate("reactivate", arguments="second")

        assert "first" in content1
        assert "second" in content2

        skill = manager.get("reactivate")
        assert skill.is_active

    def test_deactivate_clears_active_flag(self, tmp_path: Path) -> None:
        """Test that deactivate clears the active flag."""
        skill_dir = _make_skill_dir(tmp_path, "deactivatable")
        manager = SkillManager()
        manager.register(skill_dir)

        manager.activate("deactivatable")
        assert manager.get("deactivatable").is_active

        manager.deactivate("deactivatable")
        assert not manager.get("deactivatable").is_active

    def test_deactivate_nonexistent_is_noop(self) -> None:
        """Test that deactivating a nonexistent skill does nothing."""
        manager = SkillManager()

        # Should not raise
        manager.deactivate("nonexistent")

    def test_deactivate_inactive_is_noop(self, tmp_path: Path) -> None:
        """Test that deactivating an already-inactive skill does nothing."""
        skill_dir = _make_skill_dir(tmp_path, "inactive")
        manager = SkillManager()
        manager.register(skill_dir)

        # Should not raise (skill exists but is not active)
        manager.deactivate("inactive")


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestSkillManagerValidation:
    """Tests for validate() method."""

    def test_validate_valid_skill(self, tmp_path: Path) -> None:
        """Test validating a valid skill."""
        skill_dir = _make_skill_dir(tmp_path, "valid-skill")
        manager = SkillManager()

        result = manager.validate(skill_dir)

        assert isinstance(result, ValidationResult)
        assert result.valid

    def test_validate_invalid_skill(self, tmp_path: Path) -> None:
        """Test validating an invalid skill returns errors."""
        invalid_dir = tmp_path / "invalid-skill"
        invalid_dir.mkdir()
        (invalid_dir / "SKILL.md").write_text("no frontmatter here")

        manager = SkillManager()
        result = manager.validate(invalid_dir)

        assert not result.valid
        assert len(result.errors) > 0

    def test_validate_missing_skill(self, tmp_path: Path) -> None:
        """Test validating a nonexistent path."""
        manager = SkillManager()
        result = manager.validate(tmp_path / "nonexistent")

        assert not result.valid


# ---------------------------------------------------------------------------
# Tools tests
# ---------------------------------------------------------------------------


class TestSkillManagerTools:
    """Tests for get_tools() and get_all_tools() methods."""

    def test_get_tools_inactive_skill_returns_empty(self) -> None:
        """Test that get_tools returns empty list for inactive skill."""
        manager = SkillManager()
        manager.register(_make_skill(name="inactive"))

        assert manager.get_tools("inactive") == []

    def test_get_tools_nonexistent_returns_empty(self) -> None:
        """Test that get_tools returns empty list for missing skill."""
        manager = SkillManager()

        assert manager.get_tools("missing") == []

    def test_get_tools_active_skill_with_tools(self, tmp_path: Path) -> None:
        """Test getting tools from an active skill with registered tools."""
        skill_dir = _make_skill_dir(tmp_path, "tooled-skill")
        manager = SkillManager()
        manager.register(skill_dir)
        manager.activate("tooled-skill")

        # Manually add a tool to the skill's internal list
        def my_tool() -> str:
            return "result"

        skill = manager.get("tooled-skill")
        skill._tools.append(my_tool)

        tools = manager.get_tools("tooled-skill")
        assert len(tools) == 1
        assert tools[0]() == "result"

    def test_get_all_tools_empty_when_none_active(self) -> None:
        """Test get_all_tools returns empty when no skills are active."""
        manager = SkillManager()
        manager.register(_make_skill(name="inactive"))

        assert manager.get_all_tools() == []

    def test_get_all_tools_with_namespace(self, tmp_path: Path) -> None:
        """Test get_all_tools applies namespace prefixes."""
        skill_dir = _make_skill_dir(tmp_path, "ns-skill")
        config = SkillConfig(
            skills_dirs=[tmp_path],
            user_skills_dir=tmp_path / "user",
            namespace_tools=True,
        )
        manager = SkillManager(config=config)
        manager.register(skill_dir)
        manager.activate("ns-skill")

        def read_file() -> str:
            return "content"

        skill = manager.get("ns-skill")
        skill._tools.append(read_file)

        tools = manager.get_all_tools()

        assert len(tools) == 1
        assert tools[0].__name__ == "ns-skill:read_file"
        assert tools[0]() == "content"

    def test_get_all_tools_without_namespace(self, tmp_path: Path) -> None:
        """Test get_all_tools without namespace prefixes."""
        skill_dir = _make_skill_dir(tmp_path, "raw-skill")
        config = SkillConfig(
            skills_dirs=[tmp_path],
            user_skills_dir=tmp_path / "user",
            namespace_tools=False,
        )
        manager = SkillManager(config=config)
        manager.register(skill_dir)
        manager.activate("raw-skill")

        def my_fn() -> str:
            return "value"

        skill = manager.get("raw-skill")
        skill._tools.append(my_fn)

        tools = manager.get_all_tools()

        assert len(tools) == 1
        assert tools[0].__name__ == "my_fn"

    def test_get_all_tools_multiple_active_skills(self, tmp_path: Path) -> None:
        """Test collecting tools from multiple active skills."""
        dir_a = _make_skill_dir(tmp_path / "skills", "skill-a")
        dir_b = _make_skill_dir(tmp_path / "skills", "skill-b")

        manager = SkillManager()
        manager.register(dir_a)
        manager.register(dir_b)
        manager.activate("skill-a")
        manager.activate("skill-b")

        def tool_a() -> str:
            return "a"

        def tool_b() -> str:
            return "b"

        manager.get("skill-a")._tools.append(tool_a)
        manager.get("skill-b")._tools.append(tool_b)

        tools = manager.get_all_tools()
        assert len(tools) == 2


# ---------------------------------------------------------------------------
# References tests
# ---------------------------------------------------------------------------


class TestSkillManagerReferences:
    """Tests for get_references() and load_reference() methods."""

    def test_get_references_empty_when_no_dir(self, tmp_path: Path) -> None:
        """Test get_references returns empty list when no references dir."""
        skill_dir = _make_skill_dir(tmp_path, "no-refs")
        manager = SkillManager()
        manager.register(skill_dir)

        assert manager.get_references("no-refs") == []

    def test_get_references_lists_files(self, tmp_path: Path) -> None:
        """Test get_references returns list of reference files."""
        skill_dir = _make_skill_dir(tmp_path, "has-refs")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "api-docs.md").write_text("# API Docs")
        (refs_dir / "schema.json").write_text('{"type": "object"}')

        manager = SkillManager()
        manager.register(skill_dir)

        refs = manager.get_references("has-refs")

        assert len(refs) == 2
        names = {p.name for p in refs}
        assert names == {"api-docs.md", "schema.json"}

    def test_get_references_nonexistent_skill_returns_empty(self) -> None:
        """Test get_references returns empty for missing skill."""
        manager = SkillManager()

        assert manager.get_references("missing") == []

    def test_get_references_excludes_subdirectories(self, tmp_path: Path) -> None:
        """Test that get_references only returns files, not directories."""
        skill_dir = _make_skill_dir(tmp_path, "refs-test")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "file.md").write_text("content")
        (refs_dir / "subdir").mkdir()

        manager = SkillManager()
        manager.register(skill_dir)

        refs = manager.get_references("refs-test")
        assert len(refs) == 1
        assert refs[0].name == "file.md"

    def test_load_reference_returns_content(self, tmp_path: Path) -> None:
        """Test load_reference reads and returns file content."""
        skill_dir = _make_skill_dir(tmp_path, "ref-skill")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "guide.md").write_text("# Getting Started\n\nHello world.")

        manager = SkillManager()
        manager.register(skill_dir)

        content = manager.load_reference("ref-skill", "guide.md")

        assert content == "# Getting Started\n\nHello world."

    def test_load_reference_nonexistent_skill_raises(self) -> None:
        """Test load_reference raises SkillNotFoundError for missing skill."""
        manager = SkillManager()

        with pytest.raises(SkillNotFoundError, match="missing"):
            manager.load_reference("missing", "file.md")

    def test_load_reference_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """Test load_reference raises FileNotFoundError for missing file."""
        skill_dir = _make_skill_dir(tmp_path, "ref-skill")
        manager = SkillManager()
        manager.register(skill_dir)

        with pytest.raises(FileNotFoundError, match=r"ghost\.md"):
            manager.load_reference("ref-skill", "ghost.md")

    def test_load_reference_json_content(self, tmp_path: Path) -> None:
        """Test load_reference works with JSON files."""
        skill_dir = _make_skill_dir(tmp_path, "json-skill")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "config.json").write_text('{"key": "value"}')

        manager = SkillManager()
        manager.register(skill_dir)

        content = manager.load_reference("json-skill", "config.json")
        assert '"key": "value"' in content


# ---------------------------------------------------------------------------
# Integration test: Full discover -> activate -> use tools workflow
# ---------------------------------------------------------------------------


class TestSkillManagerIntegration:
    """Integration tests for the full SkillManager workflow."""

    def test_discover_activate_use_tools_deactivate(self, tmp_path: Path) -> None:
        """Test full lifecycle: discover, activate, use tools, deactivate."""
        # Set up project directory with skills
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill_dir(project_dir, "search")
        _make_skill_dir(project_dir, "format")

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        # Step 1: Discover
        discovered = manager.discover()
        assert len(discovered) == 2

        # Step 2: Activate
        content = manager.activate("search", arguments="query text")
        assert "query text" in content
        assert manager.get("search").is_active

        # Step 3: Register tools on the active skill
        def search_fn(query: str) -> list[str]:
            return [f"result for {query}"]

        manager.get("search")._tools.append(search_fn)
        tools = manager.get_tools("search")
        assert len(tools) == 1
        assert tools[0]("test") == ["result for test"]

        # Step 4: Deactivate
        manager.deactivate("search")
        assert not manager.get("search").is_active
        assert manager.get_tools("search") == []

    def test_discover_then_register_additional(self, tmp_path: Path) -> None:
        """Test that manual registration works alongside discovery."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill_dir(project_dir, "discovered")

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        manager.discover()
        assert len(manager) == 1

        # Manually register another skill
        extra_dir = _make_skill_dir(tmp_path / "extra", "manual-skill")
        manager.register(extra_dir)

        assert len(manager) == 2
        assert manager.get("manual-skill") is not None

    def test_discover_validate_activate_with_references(self, tmp_path: Path) -> None:
        """Test full workflow including validation and reference loading."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        # Create a skill with references
        skill_dir = _make_skill_dir(project_dir, "documented")
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "api.md").write_text("# API Reference\n\nEndpoints here.")
        (refs_dir / "examples.md").write_text("# Examples\n\nUsage examples.")

        config = _make_config(tmp_path, project_dir=project_dir)
        manager = SkillManager(config=config)

        # Discover
        manager.discover()
        assert len(manager) == 1

        # Validate
        result = manager.validate(skill_dir)
        assert result.valid

        # Activate
        content = manager.activate("documented")
        assert len(content) > 0

        # Load references
        refs = manager.get_references("documented")
        assert len(refs) == 2

        api_content = manager.load_reference("documented", "api.md")
        assert "API Reference" in api_content

        examples_content = manager.load_reference("documented", "examples.md")
        assert "Usage examples." in examples_content


# ---------------------------------------------------------------------------
# Namespace tool helper tests
# ---------------------------------------------------------------------------


class TestNamespaceTool:
    """Tests for the _namespace_tool helper function."""

    def test_preserves_behavior(self) -> None:
        """Test that namespaced tool preserves original behavior."""

        def original(x: int) -> int:
            return x * 2

        wrapped = _namespace_tool(original, "skill:original")
        assert wrapped(5) == 10

    def test_sets_prefixed_name(self) -> None:
        """Test that namespaced tool has the prefixed name."""

        def my_func() -> None:
            pass

        wrapped = _namespace_tool(my_func, "skill:my_func")
        assert wrapped.__name__ == "skill:my_func"

    def test_preserves_docstring(self) -> None:
        """Test that namespaced tool preserves the original docstring."""

        def documented() -> None:
            """My docstring."""

        wrapped = _namespace_tool(documented, "ns:documented")
        assert wrapped.__doc__ == "My docstring."


# ---------------------------------------------------------------------------
# Repr and dunder tests
# ---------------------------------------------------------------------------


class TestSkillManagerDunder:
    """Tests for __repr__ and __len__ methods."""

    def test_len_reflects_registry_count(self) -> None:
        """Test that len() returns the number of registered skills."""
        manager = SkillManager()
        assert len(manager) == 0

        manager.register(_make_skill(name="one"))
        assert len(manager) == 1

        manager.register(_make_skill(name="two"))
        assert len(manager) == 2

    def test_repr_shows_active_count(self, tmp_path: Path) -> None:
        """Test that repr shows active skill count."""
        skill_dir = _make_skill_dir(tmp_path, "active-repr")
        manager = SkillManager()
        manager.register(skill_dir)

        assert "active=0" in repr(manager)

        manager.activate("active-repr")
        assert "active=1" in repr(manager)
