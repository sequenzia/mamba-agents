"""Tests for the SKILL.md loader and parser."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mamba_agents.skills.config import Skill, SkillInfo, SkillScope, TrustLevel
from mamba_agents.skills.errors import (
    SkillLoadError,
    SkillNotFoundError,
    SkillParseError,
    SkillValidationError,
)
from mamba_agents.skills.loader import load_full, load_metadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_FRONTMATTER = """\
---
name: test-skill
description: A test skill
---
"""

_FULL_FRONTMATTER = """\
---
name: test-skill
description: A fully configured test skill
license: MIT
compatibility: mamba-agents>=0.2.0
metadata:
  author: tester
  version: "1.0"
allowed-tools:
  - read_file
  - write_file
model: gpt-4o
context: fork
disable-model-invocation: true
user-invocable: false
hooks:
  on_activate: setup
argument-hint: "<file_path>"
agent: code-reviewer
---
"""

_BODY_CONTENT = """\
# Test Skill

This is the skill body with instructions.

## Steps

1. Do something
2. Do something else
"""


def _write_skill(
    tmp_path: Path,
    name: str = "test-skill",
    frontmatter: str = _MINIMAL_FRONTMATTER,
    body: str = "",
) -> Path:
    """Create a skill directory with a SKILL.md file.

    The parent directory name matches the skill ``name`` so name-directory
    validation passes by default.
    """
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(frontmatter + body, encoding="utf-8")
    return skill_md


# ---------------------------------------------------------------------------
# Functional tests
# ---------------------------------------------------------------------------


class TestParseValidSkillMd:
    """Parses valid SKILL.md files with YAML frontmatter and markdown body."""

    def test_minimal_fields(self, tmp_path: Path) -> None:
        """Parse SKILL.md with only required fields."""
        skill_md = _write_skill(tmp_path)
        info = load_metadata(skill_md)

        assert info.name == "test-skill"
        assert info.description == "A test skill"
        assert info.path == skill_md.parent
        assert info.scope is SkillScope.PROJECT

    def test_all_fields_mapped_correctly(self, tmp_path: Path) -> None:
        """All frontmatter fields are mapped to SkillInfo attributes."""
        skill_md = _write_skill(tmp_path, frontmatter=_FULL_FRONTMATTER)
        info = load_metadata(skill_md)

        assert info.name == "test-skill"
        assert info.description == "A fully configured test skill"
        assert info.license == "MIT"
        assert info.compatibility == "mamba-agents>=0.2.0"
        assert info.metadata == {"author": "tester", "version": "1.0"}
        assert info.allowed_tools == ["read_file", "write_file"]
        assert info.model == "gpt-4o"
        assert info.execution_mode == "fork"
        assert info.disable_model_invocation is True
        assert info.user_invocable is False
        assert info.hooks == {"on_activate": "setup"}
        assert info.argument_hint == "<file_path>"
        assert info.agent == "code-reviewer"

    def test_returns_skill_info_type(self, tmp_path: Path) -> None:
        """load_metadata returns a SkillInfo instance."""
        skill_md = _write_skill(tmp_path)
        result = load_metadata(skill_md)
        assert isinstance(result, SkillInfo)


class TestHyphenatedYamlKeyMapping:
    """Hyphenated YAML keys mapped to Python underscores."""

    def test_allowed_tools_mapping(self, tmp_path: Path) -> None:
        """'allowed-tools' maps to 'allowed_tools'."""
        fm = "---\nname: test-skill\ndescription: t\nallowed-tools:\n  - read_file\n---\n"
        skill_md = _write_skill(tmp_path, frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.allowed_tools == ["read_file"]

    def test_disable_model_invocation_mapping(self, tmp_path: Path) -> None:
        """'disable-model-invocation' maps to 'disable_model_invocation'."""
        fm = "---\nname: test-skill\ndescription: t\ndisable-model-invocation: true\n---\n"
        skill_md = _write_skill(tmp_path, frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.disable_model_invocation is True

    def test_user_invocable_mapping(self, tmp_path: Path) -> None:
        """'user-invocable' maps to 'user_invocable'."""
        fm = "---\nname: test-skill\ndescription: t\nuser-invocable: false\n---\n"
        skill_md = _write_skill(tmp_path, frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.user_invocable is False

    def test_argument_hint_mapping(self, tmp_path: Path) -> None:
        """'argument-hint' maps to 'argument_hint'."""
        fm = "---\nname: test-skill\ndescription: t\nargument-hint: '<path>'\n---\n"
        skill_md = _write_skill(tmp_path, frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.argument_hint == "<path>"

    def test_context_renamed_to_execution_mode(self, tmp_path: Path) -> None:
        """'context' maps to 'execution_mode'."""
        fm = "---\nname: test-skill\ndescription: t\ncontext: fork\n---\n"
        skill_md = _write_skill(tmp_path, frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.execution_mode == "fork"


class TestMarkdownBodyExtraction:
    """Markdown body extracted correctly (everything after closing ---)."""

    def test_body_extracted(self, tmp_path: Path) -> None:
        """Body text after closing --- is returned."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)
        skill = load_full(skill_md)
        assert skill.body is not None
        assert "# Test Skill" in skill.body
        assert "Do something else" in skill.body

    def test_body_preserves_formatting(self, tmp_path: Path) -> None:
        """Body preserves markdown formatting."""
        body = "# Title\n\n- item 1\n- item 2\n\n```python\nprint('hi')\n```\n"
        skill_md = _write_skill(tmp_path, body=body)
        skill = load_full(skill_md)
        assert skill.body is not None
        assert "```python" in skill.body


class TestLoadMetadataReturnsInfoOnly:
    """load_metadata returns only SkillInfo without reading body."""

    def test_returns_skill_info(self, tmp_path: Path) -> None:
        """load_metadata returns SkillInfo, not Skill."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)
        info = load_metadata(skill_md)
        assert isinstance(info, SkillInfo)
        assert not isinstance(info, Skill)

    def test_scope_passed_through(self, tmp_path: Path) -> None:
        """Scope parameter is used on the returned SkillInfo."""
        skill_md = _write_skill(tmp_path)
        info = load_metadata(skill_md, scope=SkillScope.USER)
        assert info.scope is SkillScope.USER


class TestLoadFullReturnsSkill:
    """load_full returns complete Skill with body."""

    def test_returns_skill_type(self, tmp_path: Path) -> None:
        """load_full returns a Skill instance."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)
        skill = load_full(skill_md)
        assert isinstance(skill, Skill)

    def test_skill_has_info(self, tmp_path: Path) -> None:
        """Returned Skill contains populated SkillInfo."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)
        skill = load_full(skill_md)
        assert skill.info.name == "test-skill"
        assert skill.info.description == "A test skill"

    def test_skill_has_body(self, tmp_path: Path) -> None:
        """Returned Skill contains the markdown body."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)
        skill = load_full(skill_md)
        assert skill.body is not None
        assert "# Test Skill" in skill.body

    def test_scope_passed_through(self, tmp_path: Path) -> None:
        """Scope parameter is used on the Skill info."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)
        skill = load_full(skill_md, scope=SkillScope.CUSTOM)
        assert skill.info.scope is SkillScope.CUSTOM

    def test_all_fields_in_skill_info(self, tmp_path: Path) -> None:
        """load_full maps all frontmatter fields to Skill.info."""
        skill_md = _write_skill(tmp_path, frontmatter=_FULL_FRONTMATTER, body=_BODY_CONTENT)
        skill = load_full(skill_md)
        assert skill.info.model == "gpt-4o"
        assert skill.info.execution_mode == "fork"
        assert skill.info.agent == "code-reviewer"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEmptyBody:
    """Empty body (frontmatter only, no instructions) -- valid, body is None."""

    def test_no_content_after_closing_delimiter(self, tmp_path: Path) -> None:
        """Body is None when nothing follows the closing ---."""
        skill_md = _write_skill(tmp_path)
        skill = load_full(skill_md)
        assert skill.body is None

    def test_only_whitespace_after_closing_delimiter(self, tmp_path: Path) -> None:
        """Body is None when only whitespace follows closing ---."""
        skill_md = _write_skill(tmp_path, body="\n\n   \n")
        skill = load_full(skill_md)
        assert skill.body is None


class TestLargeBody:
    """Large body (>5000 tokens estimated) -- accept but log warning."""

    def test_large_body_accepted(self, tmp_path: Path) -> None:
        """A large body is loaded without error."""
        large_body = "x" * 25000  # ~6250 estimated tokens
        skill_md = _write_skill(tmp_path, body=large_body)
        skill = load_full(skill_md)
        assert skill.body is not None
        assert len(skill.body) >= 25000

    def test_large_body_logs_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """A warning is logged when body exceeds the token threshold."""
        large_body = "x" * 25000  # ~6250 estimated tokens
        skill_md = _write_skill(tmp_path, body=large_body)
        with caplog.at_level(logging.WARNING, logger="mamba_agents.skills.loader"):
            load_full(skill_md)
        assert any("approximately" in record.message for record in caplog.records)

    def test_small_body_no_warning(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """No warning for body within the recommended size."""
        small_body = "x" * 100
        skill_md = _write_skill(tmp_path, body=small_body)
        with caplog.at_level(logging.WARNING, logger="mamba_agents.skills.loader"):
            load_full(skill_md)
        assert not any("approximately" in record.message for record in caplog.records)


class TestUnknownFields:
    """Frontmatter with unknown fields -- ignore, don't error."""

    def test_unknown_fields_ignored(self, tmp_path: Path) -> None:
        """Unknown frontmatter keys are silently dropped."""
        fm = "---\nname: test-skill\ndescription: t\ncustom-field: value\nfoo: bar\n---\n"
        skill_md = _write_skill(tmp_path, frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.name == "test-skill"
        # Unknown fields should not cause errors or appear on the dataclass.
        assert not hasattr(info, "custom_field")


class TestBodyWithHorizontalRules:
    """Body with --- markers (e.g., horizontal rules) -- only split on first pair."""

    def test_horizontal_rule_in_body_preserved(self, tmp_path: Path) -> None:
        """Horizontal rules (---) in the body are not treated as delimiters."""
        body = "# Section 1\n\n---\n\n# Section 2\n\nMore content.\n"
        skill_md = _write_skill(tmp_path, body=body)
        skill = load_full(skill_md)
        assert skill.body is not None
        assert "---" in skill.body
        assert "Section 2" in skill.body

    def test_multiple_horizontal_rules_in_body(self, tmp_path: Path) -> None:
        """Multiple --- lines in the body are all preserved."""
        body = "A\n\n---\n\nB\n\n---\n\nC\n"
        skill_md = _write_skill(tmp_path, body=body)
        skill = load_full(skill_md)
        assert skill.body is not None
        assert skill.body.count("---") == 2
        assert "A" in skill.body
        assert "C" in skill.body


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestMissingFrontmatterDelimiters:
    """Missing --- markers -> SkillParseError with clear message."""

    def test_no_opening_delimiter(self, tmp_path: Path) -> None:
        """Raises SkillParseError when opening --- is missing."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("name: test\ndescription: hi\n")

        with pytest.raises(SkillParseError, match="Missing opening '---'"):
            load_metadata(skill_md)

    def test_no_closing_delimiter(self, tmp_path: Path) -> None:
        """Raises SkillParseError when closing --- is missing."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\nname: test\ndescription: hi\n")

        with pytest.raises(SkillParseError, match="Missing closing '---'"):
            load_metadata(skill_md)


class TestInvalidYamlSyntax:
    """Invalid YAML syntax -> SkillParseError with line info."""

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        """Raises SkillParseError on YAML syntax errors."""
        fm = "---\nname: test-skill\ndescription: [\n---\n"
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillParseError, match="YAML syntax error"):
            load_metadata(skill_md)

    def test_yaml_tab_error(self, tmp_path: Path) -> None:
        """Raises SkillParseError when YAML contains tabs."""
        fm = "---\nname: test-skill\n\tdescription: bad\n---\n"
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillParseError):
            load_metadata(skill_md)


class TestMissingRequiredFields:
    """Missing required fields -> SkillValidationError."""

    def test_missing_name(self, tmp_path: Path) -> None:
        """Raises SkillValidationError when name is missing."""
        fm = "---\ndescription: A skill\n---\n"
        skill_dir = tmp_path / "no-name-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="Missing required field: name"):
            load_metadata(skill_md)

    def test_missing_description(self, tmp_path: Path) -> None:
        """Raises SkillValidationError when description is missing."""
        fm = "---\nname: no-name-skill\n---\n"
        skill_dir = tmp_path / "no-name-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="Missing required field: description"):
            load_metadata(skill_md)

    def test_both_required_fields_missing(self, tmp_path: Path) -> None:
        """Raises SkillValidationError listing both missing fields."""
        fm = "---\nlicense: MIT\n---\n"
        skill_dir = tmp_path / "no-fields-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError) as exc_info:
            load_metadata(skill_md)
        assert "name" in str(exc_info.value)
        assert "description" in str(exc_info.value)


class TestInvalidNameFormat:
    """Invalid name format -> SkillValidationError with format requirements."""

    def test_uppercase_name(self, tmp_path: Path) -> None:
        """Rejects names with uppercase characters."""
        fm = "---\nname: My-SKILL\ndescription: t\n---\n"
        skill_dir = tmp_path / "My-SKILL"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="invalid"):
            load_metadata(skill_md)

    def test_special_characters(self, tmp_path: Path) -> None:
        """Rejects names with special characters."""
        fm = "---\nname: my_skill!\ndescription: t\n---\n"
        skill_dir = tmp_path / "my_skill!"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="invalid"):
            load_metadata(skill_md)

    def test_name_too_long(self, tmp_path: Path) -> None:
        """Rejects names exceeding 64 characters."""
        long_name = "a" * 65
        fm = f"---\nname: {long_name}\ndescription: t\n---\n"
        skill_dir = tmp_path / long_name
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="exceeds maximum length"):
            load_metadata(skill_md)

    def test_name_starts_with_hyphen(self, tmp_path: Path) -> None:
        """Rejects names starting with a hyphen."""
        fm = "---\nname: -bad-name\ndescription: t\n---\n"
        skill_dir = tmp_path / "-bad-name"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="invalid"):
            load_metadata(skill_md)

    def test_name_ends_with_hyphen(self, tmp_path: Path) -> None:
        """Rejects names ending with a hyphen."""
        fm = "---\nname: bad-name-\ndescription: t\n---\n"
        skill_dir = tmp_path / "bad-name-"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="invalid"):
            load_metadata(skill_md)

    def test_valid_name_accepted(self, tmp_path: Path) -> None:
        """Accepts a valid lowercase-hyphenated name."""
        fm = "---\nname: my-cool-skill-123\ndescription: t\n---\n"
        skill_md = _write_skill(tmp_path, name="my-cool-skill-123", frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.name == "my-cool-skill-123"

    def test_single_char_name_valid(self, tmp_path: Path) -> None:
        """Accepts a single character name."""
        fm = "---\nname: a\ndescription: t\n---\n"
        skill_md = _write_skill(tmp_path, name="a", frontmatter=fm)
        info = load_metadata(skill_md)
        assert info.name == "a"


class TestNameDirectoryMismatch:
    """Name doesn't match parent directory -> SkillValidationError."""

    def test_name_mismatch(self, tmp_path: Path) -> None:
        """Raises SkillValidationError when name differs from directory."""
        fm = "---\nname: different-name\ndescription: t\n---\n"
        skill_dir = tmp_path / "actual-dir-name"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(fm)

        with pytest.raises(SkillValidationError, match="does not match parent directory"):
            load_metadata(skill_md)


class TestFileNotFound:
    """File not found -> SkillNotFoundError."""

    def test_missing_file(self, tmp_path: Path) -> None:
        """Raises SkillNotFoundError when SKILL.md does not exist."""
        missing = tmp_path / "nonexistent" / "SKILL.md"
        with pytest.raises(SkillNotFoundError):
            load_metadata(missing)

    def test_error_contains_path(self, tmp_path: Path) -> None:
        """Error message includes the path that was checked."""
        missing = tmp_path / "gone" / "SKILL.md"
        with pytest.raises(SkillNotFoundError, match="gone"):
            load_metadata(missing)


class TestPermissionDenied:
    """Permission denied -> SkillLoadError."""

    def test_permission_denied(self, tmp_path: Path) -> None:
        """Raises SkillLoadError on permission denied."""
        skill_dir = tmp_path / "locked-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\nname: locked-skill\n---\n")
        skill_md.chmod(0o000)

        try:
            with pytest.raises(SkillLoadError):
                load_metadata(skill_md)
        finally:
            # Restore permissions for cleanup.
            skill_md.chmod(0o644)


# ---------------------------------------------------------------------------
# Additional integration-style tests
# ---------------------------------------------------------------------------


class TestMinimalSkillMd:
    """Parse minimal SKILL.md (name + description only)."""

    def test_minimal_with_load_metadata(self, tmp_path: Path) -> None:
        """load_metadata works with name + description only."""
        skill_md = _write_skill(tmp_path)
        info = load_metadata(skill_md)
        assert info.name == "test-skill"
        assert info.description == "A test skill"
        assert info.license is None
        assert info.allowed_tools is None

    def test_minimal_with_load_full(self, tmp_path: Path) -> None:
        """load_full works with name + description only."""
        skill_md = _write_skill(tmp_path)
        skill = load_full(skill_md)
        assert skill.info.name == "test-skill"
        assert skill.body is None


class TestFrontmatterOnlyVsFullLoading:
    """Frontmatter-only vs full loading."""

    def test_load_metadata_vs_load_full(self, tmp_path: Path) -> None:
        """load_metadata returns SkillInfo, load_full returns Skill with body."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)

        info = load_metadata(skill_md)
        assert isinstance(info, SkillInfo)

        skill = load_full(skill_md)
        assert isinstance(skill, Skill)
        assert skill.body is not None
        assert skill.info.name == info.name

    def test_both_produce_same_metadata(self, tmp_path: Path) -> None:
        """Metadata from load_metadata matches Skill.info from load_full."""
        skill_md = _write_skill(tmp_path, frontmatter=_FULL_FRONTMATTER, body=_BODY_CONTENT)

        info = load_metadata(skill_md)
        skill = load_full(skill_md)

        assert info.name == skill.info.name
        assert info.description == skill.info.description
        assert info.license == skill.info.license
        assert info.allowed_tools == skill.info.allowed_tools
        assert info.model == skill.info.model
        assert info.execution_mode == skill.info.execution_mode


class TestDefaultFieldValues:
    """Verify default values for optional SkillInfo fields."""

    def test_boolean_defaults(self, tmp_path: Path) -> None:
        """disable_model_invocation defaults to False, user_invocable to True."""
        skill_md = _write_skill(tmp_path)
        info = load_metadata(skill_md)
        assert info.disable_model_invocation is False
        assert info.user_invocable is True

    def test_trust_level_default(self, tmp_path: Path) -> None:
        """trust_level defaults to TRUSTED."""
        skill_md = _write_skill(tmp_path)
        info = load_metadata(skill_md)
        assert info.trust_level is TrustLevel.TRUSTED


class TestStringPathInput:
    """Verify that string paths are accepted (not just Path objects)."""

    def test_load_metadata_with_string_path(self, tmp_path: Path) -> None:
        """load_metadata accepts a string path."""
        skill_md = _write_skill(tmp_path)
        info = load_metadata(str(skill_md))
        assert info.name == "test-skill"

    def test_load_full_with_string_path(self, tmp_path: Path) -> None:
        """load_full accepts a string path."""
        skill_md = _write_skill(tmp_path, body=_BODY_CONTENT)
        skill = load_full(str(skill_md))
        assert skill.info.name == "test-skill"
        assert skill.body is not None
