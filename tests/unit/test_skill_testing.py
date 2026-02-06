"""Tests for the SkillTestHarness testing utility."""

from __future__ import annotations

from pathlib import Path

import pytest

from mamba_agents.skills.config import (
    Skill,
    SkillInfo,
    SkillScope,
    ValidationResult,
)
from mamba_agents.skills.errors import SkillNotFoundError
from mamba_agents.skills.testing import SkillTestHarness, skill_harness  # noqa: F401

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_FRONTMATTER = """\
---
name: test-skill
description: A test skill
---
"""

_BODY_WITH_ARGS = """\
# Test Skill

Process file: $ARGUMENTS
"""

_BODY_WITH_POSITIONAL = """\
# Test Skill

Source: $ARGUMENTS[0]
Dest: $ARGUMENTS[1]
"""

_BODY_NO_PLACEHOLDERS = """\
# Test Skill

This is a simple body with no argument placeholders.
"""


def _write_skill(
    tmp_path: Path,
    name: str = "test-skill",
    frontmatter: str = _MINIMAL_FRONTMATTER,
    body: str = "",
) -> Path:
    """Create a skill directory with a SKILL.md file."""
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(frontmatter + body, encoding="utf-8")
    return skill_dir


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    body: str | None = None,
    allowed_tools: list[str] | None = None,
    path: Path | None = None,
) -> Skill:
    """Create a Skill instance for testing."""
    info = SkillInfo(
        name=name,
        description=description,
        path=path or Path("/fake/test-skill"),
        scope=SkillScope.PROJECT,
        allowed_tools=allowed_tools,
    )
    return Skill(info=info, body=body)


# ---------------------------------------------------------------------------
# Functional tests: Load from directory path
# ---------------------------------------------------------------------------


class TestLoadFromPath:
    """Harness loads a skill from a directory path."""

    def test_load_from_directory(self, tmp_path: Path) -> None:
        """Load a skill from a directory containing SKILL.md."""
        skill_dir = _write_skill(tmp_path, body=_BODY_WITH_ARGS)
        harness = SkillTestHarness(skill_path=skill_dir)
        skill = harness.load()

        assert isinstance(skill, Skill)
        assert skill.info.name == "test-skill"
        assert skill.info.description == "A test skill"

    def test_load_from_skill_md_file(self, tmp_path: Path) -> None:
        """Load a skill from a direct SKILL.md file path."""
        skill_dir = _write_skill(tmp_path, body=_BODY_WITH_ARGS)
        skill_file = skill_dir / "SKILL.md"
        harness = SkillTestHarness(skill_path=skill_file)
        skill = harness.load()

        assert isinstance(skill, Skill)
        assert skill.info.name == "test-skill"

    def test_load_caches_result(self, tmp_path: Path) -> None:
        """Calling load() twice returns the same instance."""
        skill_dir = _write_skill(tmp_path)
        harness = SkillTestHarness(skill_path=skill_dir)
        first = harness.load()
        second = harness.load()

        assert first is second

    def test_skill_property_after_load(self, tmp_path: Path) -> None:
        """The skill property is set after loading."""
        skill_dir = _write_skill(tmp_path)
        harness = SkillTestHarness(skill_path=skill_dir)

        assert harness.skill is None
        harness.load()
        assert harness.skill is not None
        assert harness.skill.info.name == "test-skill"


# ---------------------------------------------------------------------------
# Functional tests: Load from Skill instance
# ---------------------------------------------------------------------------


class TestLoadFromInstance:
    """Harness loads a skill from a programmatic Skill instance."""

    def test_load_returns_provided_skill(self) -> None:
        """Load returns the Skill that was provided at construction."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)
        result = harness.load()

        assert result is skill
        assert result.info.name == "test-skill"

    def test_skill_property_returns_instance(self) -> None:
        """The skill property returns the provided instance immediately."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)

        assert harness.skill is skill

    def test_skill_path_is_none(self) -> None:
        """When constructed with a Skill, skill_path is None."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)

        assert harness.skill_path is None


# ---------------------------------------------------------------------------
# Functional tests: Validate
# ---------------------------------------------------------------------------


class TestValidate:
    """Validate frontmatter and body, return ValidationResult."""

    def test_validate_from_path(self, tmp_path: Path) -> None:
        """Validate a skill from its directory path."""
        skill_dir = _write_skill(tmp_path)
        harness = SkillTestHarness(skill_path=skill_dir)
        result = harness.validate()

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.errors == []

    def test_validate_from_instance(self) -> None:
        """Validate a skill from a Skill instance."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)
        result = harness.validate()

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.errors == []

    def test_validate_invalid_skill_reports_errors(self) -> None:
        """Validation returns errors for an invalid skill."""
        info = SkillInfo(
            name="INVALID",
            description="Bad skill",
            path=Path("/fake"),
            scope=SkillScope.PROJECT,
        )
        skill = Skill(info=info, body=None)
        harness = SkillTestHarness(skill=skill)
        result = harness.validate()

        assert isinstance(result, ValidationResult)
        assert result.valid is False
        assert len(result.errors) > 0

    def test_validate_includes_path(self) -> None:
        """Validation result includes the skill path."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)
        result = harness.validate()

        assert result.skill_path == skill.info.path


# ---------------------------------------------------------------------------
# Functional tests: Invoke
# ---------------------------------------------------------------------------


class TestInvoke:
    """Simulate invocation with test arguments."""

    def test_invoke_with_arguments_placeholder(self, tmp_path: Path) -> None:
        """Invoke substitutes $ARGUMENTS with the provided string."""
        skill_dir = _write_skill(tmp_path, body=_BODY_WITH_ARGS)
        harness = SkillTestHarness(skill_path=skill_dir)
        content = harness.invoke("myfile.txt")

        assert "myfile.txt" in content
        assert "$ARGUMENTS" not in content

    def test_invoke_with_positional_arguments(self, tmp_path: Path) -> None:
        """Invoke substitutes $ARGUMENTS[N] with positional args."""
        skill_dir = _write_skill(tmp_path, body=_BODY_WITH_POSITIONAL)
        harness = SkillTestHarness(skill_path=skill_dir)
        content = harness.invoke("source.txt dest.txt")

        assert "source.txt" in content
        assert "dest.txt" in content

    def test_invoke_with_no_placeholders_appends(self, tmp_path: Path) -> None:
        """When no placeholders exist, arguments are appended."""
        skill_dir = _write_skill(tmp_path, body=_BODY_NO_PLACEHOLDERS)
        harness = SkillTestHarness(skill_path=skill_dir)
        content = harness.invoke("extra args")

        assert "ARGUMENTS: extra args" in content

    def test_invoke_empty_arguments(self, tmp_path: Path) -> None:
        """Invoke with empty arguments does not add ARGUMENTS line."""
        skill_dir = _write_skill(tmp_path, body=_BODY_NO_PLACEHOLDERS)
        harness = SkillTestHarness(skill_path=skill_dir)
        content = harness.invoke("")

        assert "ARGUMENTS:" not in content

    def test_invoke_from_skill_instance(self) -> None:
        """Invoke works when constructed with a Skill instance."""
        skill = _make_skill(body="Process: $ARGUMENTS")
        harness = SkillTestHarness(skill=skill)
        content = harness.invoke("test.py")

        assert "Process: test.py" in content

    def test_invoke_with_none_body(self) -> None:
        """Invoke with a skill that has no body returns empty or appended."""
        skill = _make_skill(body=None)
        harness = SkillTestHarness(skill=skill)
        content = harness.invoke("some args")

        assert "ARGUMENTS: some args" in content

    def test_invoke_does_not_require_llm(self, tmp_path: Path) -> None:
        """Invoke does not make any LLM calls (no model needed)."""
        # This test verifies the fundamental design: invocation is pure
        # template processing. The global ALLOW_MODEL_REQUESTS=False in
        # conftest.py would cause a failure if any model call was attempted.
        skill_dir = _write_skill(tmp_path, body=_BODY_WITH_ARGS)
        harness = SkillTestHarness(skill_path=skill_dir)
        content = harness.invoke("arg1")

        assert isinstance(content, str)


# ---------------------------------------------------------------------------
# Functional tests: Get registered tools
# ---------------------------------------------------------------------------


class TestGetRegisteredTools:
    """Verify tool registrations from skill metadata."""

    def test_returns_allowed_tools(self) -> None:
        """Returns the allowed_tools from the skill info."""
        skill = _make_skill(allowed_tools=["read_file", "write_file", "run_bash"])
        harness = SkillTestHarness(skill=skill)
        tools = harness.get_registered_tools()

        assert tools == ["read_file", "write_file", "run_bash"]

    def test_returns_empty_when_no_tools(self) -> None:
        """Returns empty list when skill has no allowed_tools."""
        skill = _make_skill(allowed_tools=None)
        harness = SkillTestHarness(skill=skill)
        tools = harness.get_registered_tools()

        assert tools == []

    def test_returns_copy_not_reference(self) -> None:
        """Returns a new list, not a reference to the internal one."""
        tool_list = ["read_file", "write_file"]
        skill = _make_skill(allowed_tools=tool_list)
        harness = SkillTestHarness(skill=skill)
        tools = harness.get_registered_tools()

        tools.append("extra_tool")
        assert "extra_tool" not in harness.get_registered_tools()

    def test_get_tools_from_path(self, tmp_path: Path) -> None:
        """Get tools from a path-loaded skill with allowed-tools in frontmatter."""
        fm = """\
---
name: tool-skill
description: A skill with tools
allowed-tools:
  - read_file
  - glob_search
---
"""
        skill_dir = _write_skill(tmp_path, name="tool-skill", frontmatter=fm)
        harness = SkillTestHarness(skill_path=skill_dir)
        tools = harness.get_registered_tools()

        assert tools == ["read_file", "glob_search"]


# ---------------------------------------------------------------------------
# Functional tests: Structured results
# ---------------------------------------------------------------------------


class TestStructuredResults:
    """Return structured test results (ValidationResult, strings)."""

    def test_validate_returns_validation_result(self) -> None:
        """validate() returns a ValidationResult dataclass."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)
        result = harness.validate()

        assert isinstance(result, ValidationResult)
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    def test_invoke_returns_string(self, tmp_path: Path) -> None:
        """invoke() returns a string."""
        skill_dir = _write_skill(tmp_path, body="Hello $ARGUMENTS")
        harness = SkillTestHarness(skill_path=skill_dir)
        content = harness.invoke("world")

        assert isinstance(content, str)

    def test_get_registered_tools_returns_list_of_strings(self) -> None:
        """get_registered_tools() returns a list of strings."""
        skill = _make_skill(allowed_tools=["tool1"])
        harness = SkillTestHarness(skill=skill)
        tools = harness.get_registered_tools()

        assert isinstance(tools, list)
        assert all(isinstance(t, str) for t in tools)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestInvalidSkillPath:
    """Harness with invalid skill path produces clear error."""

    def test_load_nonexistent_directory(self, tmp_path: Path) -> None:
        """Load from a nonexistent directory raises SkillNotFoundError."""
        bad_path = tmp_path / "nonexistent-skill"
        harness = SkillTestHarness(skill_path=bad_path)

        with pytest.raises(SkillNotFoundError):
            harness.load()

    def test_load_directory_without_skill_md(self, tmp_path: Path) -> None:
        """Load from a directory without SKILL.md raises SkillNotFoundError."""
        empty_dir = tmp_path / "empty-skill"
        empty_dir.mkdir()
        harness = SkillTestHarness(skill_path=empty_dir)

        with pytest.raises(SkillNotFoundError):
            harness.load()

    def test_invoke_with_bad_path_raises(self, tmp_path: Path) -> None:
        """Invoke on a harness with a bad path raises SkillNotFoundError."""
        bad_path = tmp_path / "missing-skill"
        harness = SkillTestHarness(skill_path=bad_path)

        with pytest.raises(SkillNotFoundError):
            harness.invoke("args")

    def test_validate_missing_path(self, tmp_path: Path) -> None:
        """Validate with a missing path returns invalid result."""
        bad_path = tmp_path / "missing"
        harness = SkillTestHarness(skill_path=bad_path)
        result = harness.validate()

        assert result.valid is False
        assert len(result.errors) > 0


class TestSkillInstanceNoPath:
    """Harness with Skill instance (no path) works directly."""

    def test_load_works_without_path(self) -> None:
        """Load returns the skill instance without needing a filesystem path."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)
        result = harness.load()

        assert result is skill

    def test_validate_works_without_path(self) -> None:
        """Validate works on an in-memory skill instance."""
        skill = _make_skill()
        harness = SkillTestHarness(skill=skill)
        result = harness.validate()

        assert isinstance(result, ValidationResult)
        assert result.valid is True

    def test_invoke_works_without_path(self) -> None:
        """Invoke works on a skill instance with a body."""
        skill = _make_skill(body="Do: $ARGUMENTS")
        harness = SkillTestHarness(skill=skill)
        content = harness.invoke("something")

        assert "Do: something" in content

    def test_get_tools_works_without_path(self) -> None:
        """Get tools works on a skill instance without a filesystem."""
        skill = _make_skill(allowed_tools=["tool_a", "tool_b"])
        harness = SkillTestHarness(skill=skill)
        tools = harness.get_registered_tools()

        assert tools == ["tool_a", "tool_b"]


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


class TestConstructionValidation:
    """Construction requires at least one of skill_path or skill."""

    def test_neither_provided_raises_value_error(self) -> None:
        """Raises ValueError when neither path nor skill is given."""
        with pytest.raises(ValueError, match="Either 'skill_path' or 'skill'"):
            SkillTestHarness()

    def test_both_provided_uses_skill(self) -> None:
        """When both are provided, the Skill instance takes precedence."""
        skill = _make_skill(name="direct-skill", description="Direct")
        harness = SkillTestHarness(
            skill_path=Path("/some/path"),
            skill=skill,
        )
        result = harness.load()

        assert result is skill
        assert result.info.name == "direct-skill"


# ---------------------------------------------------------------------------
# pytest fixture tests
# ---------------------------------------------------------------------------


class TestSkillHarnessFixture:
    """The skill_harness pytest fixture works correctly."""

    def test_fixture_creates_harness_from_path(
        self,
        tmp_path: Path,
        skill_harness,  # noqa: F811
    ) -> None:
        """Fixture creates a SkillTestHarness from a path."""
        skill_dir = _write_skill(tmp_path)
        harness = skill_harness(path=skill_dir)

        assert isinstance(harness, SkillTestHarness)
        assert harness.skill_path == skill_dir

    def test_fixture_creates_harness_from_skill(
        self,
        skill_harness,  # noqa: F811
    ) -> None:
        """Fixture creates a SkillTestHarness from a Skill instance."""
        skill = _make_skill()
        harness = skill_harness(skill=skill)

        assert isinstance(harness, SkillTestHarness)
        assert harness.skill is skill

    def test_fixture_harness_loads(
        self,
        tmp_path: Path,
        skill_harness,  # noqa: F811
    ) -> None:
        """Harness created by fixture can load skills."""
        skill_dir = _write_skill(tmp_path, body="Hello")
        harness = skill_harness(path=skill_dir)
        skill = harness.load()

        assert skill.info.name == "test-skill"

    def test_fixture_harness_validates(
        self,
        skill_harness,  # noqa: F811
    ) -> None:
        """Harness created by fixture can validate skills."""
        skill = _make_skill()
        harness = skill_harness(skill=skill)
        result = harness.validate()

        assert result.valid is True
