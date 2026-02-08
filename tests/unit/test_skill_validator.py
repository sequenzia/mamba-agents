"""Tests for skill validation and trust level enforcement."""

from __future__ import annotations

from pathlib import Path

from mamba_agents.skills.config import (
    SkillInfo,
    SkillScope,
    TrustLevel,
    ValidationResult,
)
from mamba_agents.skills.validator import (
    check_trust_restrictions,
    resolve_trust_level,
    validate,
    validate_frontmatter,
)


class TestValidateFrontmatter:
    """Tests for validate_frontmatter function."""

    def test_valid_skill_minimal(self) -> None:
        """Valid skill with only required fields produces no errors."""
        data = {"name": "my-skill", "description": "A simple skill"}
        result = validate_frontmatter(data)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_valid_skill_all_optional_fields(self) -> None:
        """Valid skill with all optional fields produces no errors."""
        data = {
            "name": "full-skill",
            "description": "A fully-configured skill",
            "license": "MIT",
            "compatibility": "mamba-agents>=0.2.0",
            "metadata": {"author": "test", "version": "1.0"},
            "allowed-tools": ["read_file", "write_file"],
            "model": "gpt-4o",
            "context": "fork",
            "execution-mode": "fork",
            "agent": "code-reviewer",
            "disable-model-invocation": True,
            "user-invocable": False,
            "hooks": {"on_activate": "setup"},
            "argument-hint": "<file_path>",
        }
        result = validate_frontmatter(data)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_missing_name(self) -> None:
        """Missing 'name' field is detected."""
        data = {"description": "A skill without a name"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("'name'" in e for e in result.errors)

    def test_missing_description(self) -> None:
        """Missing 'description' field is detected."""
        data = {"name": "my-skill"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("'description'" in e for e in result.errors)

    def test_missing_both_required_fields(self) -> None:
        """Missing both required fields reports both errors."""
        data = {"license": "MIT"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert len(result.errors) >= 2
        assert any("'name'" in e for e in result.errors)
        assert any("'description'" in e for e in result.errors)

    def test_invalid_name_uppercase(self) -> None:
        """Name with uppercase characters is rejected."""
        data = {"name": "My-Skill", "description": "Invalid name"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("lowercase" in e for e in result.errors)

    def test_invalid_name_spaces(self) -> None:
        """Name with spaces is rejected."""
        data = {"name": "my skill", "description": "Invalid name"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("name" in e.lower() for e in result.errors)

    def test_invalid_name_underscore(self) -> None:
        """Name with underscores is rejected."""
        data = {"name": "my_skill", "description": "Invalid name"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("name" in e.lower() for e in result.errors)

    def test_invalid_name_too_long(self) -> None:
        """Name exceeding 64 characters is rejected."""
        long_name = "a" * 65
        data = {"name": long_name, "description": "Too long"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("64" in e for e in result.errors)

    def test_valid_name_max_length(self) -> None:
        """Name at exactly 64 characters is accepted."""
        name = "a" * 64
        data = {"name": name, "description": "Max length"}
        result = validate_frontmatter(data)

        assert result.valid is True

    def test_invalid_name_empty(self) -> None:
        """Empty name string is rejected."""
        data = {"name": "", "description": "Empty name"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("empty" in e.lower() for e in result.errors)

    def test_invalid_name_starts_with_hyphen(self) -> None:
        """Name starting with a hyphen is rejected."""
        data = {"name": "-bad-name", "description": "Bad start"}
        result = validate_frontmatter(data)

        assert result.valid is False

    def test_valid_name_with_numbers(self) -> None:
        """Name with numbers is accepted."""
        data = {"name": "skill-v2", "description": "Versioned skill"}
        result = validate_frontmatter(data)

        assert result.valid is True

    def test_invalid_field_type_name_not_string(self) -> None:
        """Non-string 'name' is detected as a type error."""
        data = {"name": 123, "description": "Bad type"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("'name'" in e and "string" in e for e in result.errors)

    def test_invalid_field_type_description_not_string(self) -> None:
        """Non-string 'description' is detected as a type error."""
        data = {"name": "my-skill", "description": 42}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("'description'" in e and "string" in e for e in result.errors)

    def test_invalid_field_type_allowed_tools_not_list(self) -> None:
        """Non-list 'allowed-tools' is detected as a type error."""
        data = {"name": "my-skill", "description": "ok", "allowed-tools": "read_file"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("allowed-tools" in e for e in result.errors)

    def test_invalid_field_type_metadata_not_dict(self) -> None:
        """Non-dict 'metadata' is detected as a type error."""
        data = {"name": "my-skill", "description": "ok", "metadata": "invalid"}
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("metadata" in e for e in result.errors)

    def test_invalid_field_type_disable_model_invocation_not_bool(self) -> None:
        """Non-bool 'disable-model-invocation' is detected as a type error."""
        data = {
            "name": "my-skill",
            "description": "ok",
            "disable-model-invocation": "yes",
        }
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("disable-model-invocation" in e for e in result.errors)

    def test_invalid_allowed_tools_item_not_string(self) -> None:
        """Non-string items in 'allowed-tools' list are detected."""
        data = {
            "name": "my-skill",
            "description": "ok",
            "allowed-tools": ["read_file", 123],
        }
        result = validate_frontmatter(data)

        assert result.valid is False
        assert any("index 1" in e for e in result.errors)

    def test_unknown_fields_produce_warnings(self) -> None:
        """Unknown frontmatter fields produce warnings, not errors."""
        data = {
            "name": "my-skill",
            "description": "ok",
            "custom-field": "value",
            "extra": True,
        }
        result = validate_frontmatter(data)

        assert result.valid is True
        assert len(result.warnings) == 2
        assert any("custom-field" in w for w in result.warnings)
        assert any("extra" in w for w in result.warnings)

    def test_multiple_errors_all_reported(self) -> None:
        """Multiple validation errors are all reported, not just the first."""
        data = {
            "name": "INVALID NAME!",
            # description is missing
            "allowed-tools": "not-a-list",
            "metadata": "not-a-dict",
        }
        result = validate_frontmatter(data)

        assert result.valid is False
        # At minimum: missing description, invalid name, bad allowed-tools, bad metadata
        assert len(result.errors) >= 4

    def test_returns_validation_result_type(self) -> None:
        """Function returns a ValidationResult dataclass."""
        result = validate_frontmatter({"name": "ok", "description": "ok"})
        assert isinstance(result, ValidationResult)


class TestValidate:
    """Tests for validate function (file-based validation)."""

    def test_valid_skill_file(self, tmp_path: Path) -> None:
        """Valid SKILL.md file passes validation."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: my-skill\ndescription: A test skill\n---\n# Instructions\nDo stuff.\n"
        )

        result = validate(skill_dir)

        assert result.valid is True
        assert result.errors == []
        assert result.skill_path == skill_dir

    def test_valid_skill_file_direct_path(self, tmp_path: Path) -> None:
        """Passing SKILL.md file path directly also works."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(
            "---\nname: my-skill\ndescription: A test skill\n---\n# Body\n"
        )

        result = validate(skill_file)

        assert result.valid is True
        assert result.skill_path == skill_dir

    def test_missing_skill_file(self, tmp_path: Path) -> None:
        """Missing SKILL.md returns an error."""
        skill_dir = tmp_path / "missing-skill"
        skill_dir.mkdir()

        result = validate(skill_dir)

        assert result.valid is False
        assert any("not found" in e for e in result.errors)

    def test_missing_frontmatter(self, tmp_path: Path) -> None:
        """SKILL.md without frontmatter markers returns an error."""
        skill_dir = tmp_path / "no-front"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Just a markdown file\nNo frontmatter here.\n")

        result = validate(skill_dir)

        assert result.valid is False
        assert any("frontmatter" in e.lower() for e in result.errors)

    def test_name_directory_mismatch(self, tmp_path: Path) -> None:
        """Name not matching parent directory is detected."""
        skill_dir = tmp_path / "actual-dir"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: different-name\ndescription: Mismatch test\n---\n"
        )

        result = validate(skill_dir)

        assert result.valid is False
        assert any("does not match" in e for e in result.errors)

    def test_name_directory_match(self, tmp_path: Path) -> None:
        """Name matching parent directory passes validation."""
        skill_dir = tmp_path / "matching-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: matching-skill\ndescription: Match test\n---\n"
        )

        result = validate(skill_dir)

        assert result.valid is True

    def test_validation_errors_from_frontmatter(self, tmp_path: Path) -> None:
        """Frontmatter errors are included in the file validation result."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: BAD\n---\n# Body\n"
        )

        result = validate(skill_dir)

        assert result.valid is False
        # Should have name format error + missing description
        assert len(result.errors) >= 2

    def test_returns_skill_path(self, tmp_path: Path) -> None:
        """Result includes the skill path."""
        skill_dir = tmp_path / "path-test"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: path-test\ndescription: ok\n---\n"
        )

        result = validate(skill_dir)
        assert result.skill_path == skill_dir

    def test_empty_frontmatter(self, tmp_path: Path) -> None:
        """Empty frontmatter (no fields) reports missing required fields."""
        skill_dir = tmp_path / "empty-front"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\n---\n# Body\n")

        result = validate(skill_dir)

        assert result.valid is False
        assert any("'name'" in e for e in result.errors)
        assert any("'description'" in e for e in result.errors)


class TestResolveTrustLevel:
    """Tests for resolve_trust_level function."""

    def test_project_scope_is_trusted(self) -> None:
        """Project-scoped skills default to trusted."""
        level = resolve_trust_level(SkillScope.PROJECT, Path("/project/.mamba/skills/my-skill"))
        assert level is TrustLevel.TRUSTED

    def test_user_scope_is_trusted(self) -> None:
        """User-scoped skills default to trusted."""
        level = resolve_trust_level(SkillScope.USER, Path.home() / ".mamba/skills/my-skill")
        assert level is TrustLevel.TRUSTED

    def test_custom_scope_is_untrusted_by_default(self) -> None:
        """Custom-scoped skills default to untrusted."""
        level = resolve_trust_level(SkillScope.CUSTOM, Path("/some/custom/path"))
        assert level is TrustLevel.UNTRUSTED

    def test_custom_scope_trusted_via_trusted_paths(self, tmp_path: Path) -> None:
        """Custom-scoped skill in a trusted path is trusted."""
        trusted_dir = tmp_path / "trusted"
        trusted_dir.mkdir()
        skill_path = trusted_dir / "my-skill"
        skill_path.mkdir()

        level = resolve_trust_level(
            SkillScope.CUSTOM, skill_path, trusted_paths=[trusted_dir]
        )
        assert level is TrustLevel.TRUSTED

    def test_custom_scope_not_in_trusted_paths(self, tmp_path: Path) -> None:
        """Custom-scoped skill not in any trusted path is untrusted."""
        trusted_dir = tmp_path / "trusted"
        trusted_dir.mkdir()
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        skill_path = other_dir / "my-skill"
        skill_path.mkdir()

        level = resolve_trust_level(
            SkillScope.CUSTOM, skill_path, trusted_paths=[trusted_dir]
        )
        assert level is TrustLevel.UNTRUSTED

    def test_custom_scope_empty_trusted_paths(self) -> None:
        """Custom-scoped skill with empty trusted_paths list is untrusted."""
        level = resolve_trust_level(
            SkillScope.CUSTOM, Path("/custom/skill"), trusted_paths=[]
        )
        assert level is TrustLevel.UNTRUSTED

    def test_custom_scope_none_trusted_paths(self) -> None:
        """Custom-scoped skill with None trusted_paths is untrusted."""
        level = resolve_trust_level(
            SkillScope.CUSTOM, Path("/custom/skill"), trusted_paths=None
        )
        assert level is TrustLevel.UNTRUSTED


class TestCheckTrustRestrictions:
    """Tests for check_trust_restrictions function."""

    def _make_skill(self, **overrides: object) -> SkillInfo:
        """Create a SkillInfo with defaults for testing."""
        defaults: dict[str, object] = {
            "name": "test-skill",
            "description": "Test",
            "path": Path("/skills/test"),
            "scope": SkillScope.CUSTOM,
            "trust_level": TrustLevel.UNTRUSTED,
        }
        defaults.update(overrides)
        return SkillInfo(**defaults)  # type: ignore[arg-type]

    def test_trusted_skill_no_violations(self) -> None:
        """Trusted skills never produce violations regardless of fields."""
        skill = self._make_skill(
            trust_level=TrustLevel.TRUSTED,
            hooks={"on_activate": "setup"},
            execution_mode="fork",
            allowed_tools=["read_file"],
        )
        violations = check_trust_restrictions(skill)
        assert violations == []

    def test_untrusted_skill_with_hooks(self) -> None:
        """Untrusted skill using hooks is detected."""
        skill = self._make_skill(hooks={"on_activate": "setup"})
        violations = check_trust_restrictions(skill)

        assert len(violations) == 1
        assert "hooks" in violations[0].lower()

    def test_untrusted_skill_with_fork(self) -> None:
        """Untrusted skill using context:fork is detected."""
        skill = self._make_skill(execution_mode="fork")
        violations = check_trust_restrictions(skill)

        assert len(violations) == 1
        assert "fork" in violations[0].lower()

    def test_untrusted_skill_with_allowed_tools(self) -> None:
        """Untrusted skill using allowed-tools is detected."""
        skill = self._make_skill(allowed_tools=["read_file", "write_file"])
        violations = check_trust_restrictions(skill)

        assert len(violations) == 1
        assert "allowed-tools" in violations[0].lower()

    def test_untrusted_skill_multiple_violations(self) -> None:
        """Untrusted skill with multiple violations reports all of them."""
        skill = self._make_skill(
            hooks={"on_activate": "setup"},
            execution_mode="fork",
            allowed_tools=["read_file"],
        )
        violations = check_trust_restrictions(skill)

        assert len(violations) == 3

    def test_untrusted_skill_no_restricted_features(self) -> None:
        """Untrusted skill without restricted features has no violations."""
        skill = self._make_skill()
        violations = check_trust_restrictions(skill)
        assert violations == []

    def test_untrusted_skill_empty_hooks(self) -> None:
        """Untrusted skill with empty hooks dict has no violation."""
        skill = self._make_skill(hooks={})
        violations = check_trust_restrictions(skill)
        assert violations == []

    def test_untrusted_skill_none_hooks(self) -> None:
        """Untrusted skill with None hooks has no violation."""
        skill = self._make_skill(hooks=None)
        violations = check_trust_restrictions(skill)
        assert violations == []

    def test_untrusted_skill_empty_allowed_tools(self) -> None:
        """Untrusted skill with empty allowed_tools list has no violation."""
        skill = self._make_skill(allowed_tools=[])
        violations = check_trust_restrictions(skill)
        assert violations == []

    def test_untrusted_skill_non_fork_execution_mode(self) -> None:
        """Untrusted skill with non-fork execution mode has no fork violation."""
        skill = self._make_skill(execution_mode="inline")
        violations = check_trust_restrictions(skill)
        assert violations == []
