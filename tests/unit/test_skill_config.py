"""Tests for skill data models, enums, and configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from mamba_agents.skills.config import (
    Skill,
    SkillConfig,
    SkillInfo,
    SkillScope,
    TrustLevel,
    ValidationResult,
)


class TestSkillScope:
    """Tests for SkillScope enum."""

    def test_member_values(self) -> None:
        """Test that all members have the correct string values."""
        assert SkillScope.PROJECT.value == "project"
        assert SkillScope.USER.value == "user"
        assert SkillScope.CUSTOM.value == "custom"

    def test_string_conversion(self) -> None:
        """Test that str() returns the enum value."""
        assert str(SkillScope.PROJECT) == "SkillScope.PROJECT"
        assert SkillScope.PROJECT == "project"

    def test_construction_from_value(self) -> None:
        """Test that enum can be constructed from a string value."""
        assert SkillScope("project") is SkillScope.PROJECT
        assert SkillScope("user") is SkillScope.USER
        assert SkillScope("custom") is SkillScope.CUSTOM

    def test_member_count(self) -> None:
        """Test that the enum has exactly 3 members."""
        assert len(SkillScope) == 3


class TestTrustLevel:
    """Tests for TrustLevel enum."""

    def test_member_values(self) -> None:
        """Test that all members have the correct string values."""
        assert TrustLevel.TRUSTED.value == "trusted"
        assert TrustLevel.UNTRUSTED.value == "untrusted"

    def test_string_conversion(self) -> None:
        """Test that str() returns the enum value."""
        assert TrustLevel.TRUSTED == "trusted"
        assert TrustLevel.UNTRUSTED == "untrusted"

    def test_construction_from_value(self) -> None:
        """Test that enum can be constructed from a string value."""
        assert TrustLevel("trusted") is TrustLevel.TRUSTED
        assert TrustLevel("untrusted") is TrustLevel.UNTRUSTED

    def test_member_count(self) -> None:
        """Test that the enum has exactly 2 members."""
        assert len(TrustLevel) == 2


class TestSkillInfo:
    """Tests for SkillInfo dataclass."""

    def test_minimal_construction(self) -> None:
        """Test construction with only required fields."""
        info = SkillInfo(
            name="test-skill",
            description="A test skill",
            path=Path("/some/path"),
            scope=SkillScope.PROJECT,
        )

        assert info.name == "test-skill"
        assert info.description == "A test skill"
        assert info.path == Path("/some/path")
        assert info.scope is SkillScope.PROJECT

    def test_optional_fields_default_to_none(self) -> None:
        """Test that all optional fields default to None."""
        info = SkillInfo(
            name="test-skill",
            description="A test skill",
            path=Path("/some/path"),
            scope=SkillScope.PROJECT,
        )

        assert info.license is None
        assert info.compatibility is None
        assert info.metadata is None
        assert info.allowed_tools is None
        assert info.model is None
        assert info.execution_mode is None
        assert info.agent is None
        assert info.argument_hint is None
        assert info.hooks is None

    def test_boolean_defaults(self) -> None:
        """Test that boolean fields have correct defaults."""
        info = SkillInfo(
            name="test-skill",
            description="A test skill",
            path=Path("/some/path"),
            scope=SkillScope.PROJECT,
        )

        assert info.disable_model_invocation is False
        assert info.user_invocable is True

    def test_trust_level_default(self) -> None:
        """Test that trust_level defaults to TRUSTED."""
        info = SkillInfo(
            name="test-skill",
            description="A test skill",
            path=Path("/some/path"),
            scope=SkillScope.PROJECT,
        )

        assert info.trust_level is TrustLevel.TRUSTED

    def test_construction_with_all_fields(self) -> None:
        """Test construction with all optional fields set."""
        info = SkillInfo(
            name="full-skill",
            description="A fully-configured skill",
            path=Path("/skills/full"),
            scope=SkillScope.USER,
            license="MIT",
            compatibility="mamba-agents>=0.2.0",
            metadata={"author": "test", "version": "1.0"},
            allowed_tools=["read_file", "write_file"],
            model="gpt-4o",
            execution_mode="fork",
            agent="code-reviewer",
            disable_model_invocation=True,
            user_invocable=False,
            argument_hint="<file_path>",
            hooks={"on_activate": "setup"},
            trust_level=TrustLevel.UNTRUSTED,
        )

        assert info.name == "full-skill"
        assert info.description == "A fully-configured skill"
        assert info.path == Path("/skills/full")
        assert info.scope is SkillScope.USER
        assert info.license == "MIT"
        assert info.compatibility == "mamba-agents>=0.2.0"
        assert info.metadata == {"author": "test", "version": "1.0"}
        assert info.allowed_tools == ["read_file", "write_file"]
        assert info.model == "gpt-4o"
        assert info.execution_mode == "fork"
        assert info.agent == "code-reviewer"
        assert info.disable_model_invocation is True
        assert info.user_invocable is False
        assert info.argument_hint == "<file_path>"
        assert info.hooks == {"on_activate": "setup"}
        assert info.trust_level is TrustLevel.UNTRUSTED

    def test_scope_as_custom(self) -> None:
        """Test construction with CUSTOM scope."""
        info = SkillInfo(
            name="custom-skill",
            description="Custom skill",
            path=Path("/custom/path"),
            scope=SkillScope.CUSTOM,
        )

        assert info.scope is SkillScope.CUSTOM


class TestSkill:
    """Tests for Skill Pydantic model."""

    def _make_info(self) -> SkillInfo:
        """Create a minimal SkillInfo for testing."""
        return SkillInfo(
            name="test-skill",
            description="A test skill",
            path=Path("/some/path"),
            scope=SkillScope.PROJECT,
        )

    def test_construction_with_defaults(self) -> None:
        """Test that Skill can be constructed with just info."""
        skill = Skill(info=self._make_info())

        assert skill.info.name == "test-skill"
        assert skill.body is None
        assert skill.is_active is False

    def test_lazy_loaded_body(self) -> None:
        """Test that body can be set after construction."""
        skill = Skill(info=self._make_info())
        assert skill.body is None

        skill.body = "# Skill Content\nThis is the skill body."
        assert skill.body == "# Skill Content\nThis is the skill body."

    def test_is_active_flag(self) -> None:
        """Test that is_active can be set at construction."""
        skill = Skill(info=self._make_info(), is_active=True)
        assert skill.is_active is True

    def test_private_tools_attribute(self) -> None:
        """Test that _tools is a private attribute with empty list default."""
        skill = Skill(info=self._make_info())
        assert skill._tools == []

    def test_private_tools_can_store_callables(self) -> None:
        """Test that _tools can store callable objects."""

        def my_tool() -> str:
            return "result"

        skill = Skill(info=self._make_info())
        skill._tools.append(my_tool)
        assert len(skill._tools) == 1
        assert skill._tools[0]() == "result"

    def test_serialization_excludes_tools(self) -> None:
        """Test that model_dump excludes the private _tools attribute."""
        skill = Skill(info=self._make_info())
        skill._tools.append(lambda: None)

        dumped = skill.model_dump()
        assert "_tools" not in dumped
        assert "info" in dumped
        assert "body" in dumped
        assert "is_active" in dumped

    def test_model_json_schema_excludes_tools(self) -> None:
        """Test that JSON schema excludes the private _tools attribute."""
        schema = Skill.model_json_schema()
        properties = schema.get("properties", {})
        assert "_tools" not in properties


class TestSkillConfig:
    """Tests for SkillConfig Pydantic model."""

    def test_default_values(self) -> None:
        """Test that default values are correct."""
        config = SkillConfig()

        assert config.skills_dirs == [Path(".mamba/skills")]
        assert config.custom_paths == []
        assert config.auto_discover is True
        assert config.namespace_tools is True
        assert config.trusted_paths == []

    def test_user_skills_dir_default_expands_tilde(self) -> None:
        """Test that user_skills_dir expands ~ to home directory."""
        config = SkillConfig()

        assert "~" not in str(config.user_skills_dir)
        assert config.user_skills_dir == Path.home() / ".mamba" / "skills"

    def test_user_skills_dir_custom_expands_tilde(self) -> None:
        """Test that a custom user_skills_dir with ~ is expanded."""
        config = SkillConfig(user_skills_dir=Path("~/custom/skills"))

        assert "~" not in str(config.user_skills_dir)
        assert config.user_skills_dir == Path.home() / "custom" / "skills"

    def test_custom_values(self) -> None:
        """Test construction with custom values."""
        config = SkillConfig(
            skills_dirs=[Path("project/skills"), Path("lib/skills")],
            user_skills_dir=Path("/absolute/skills"),
            custom_paths=[Path("/extra/skills")],
            auto_discover=False,
            namespace_tools=False,
            trusted_paths=[Path("/trusted/path")],
        )

        assert config.skills_dirs == [Path("project/skills"), Path("lib/skills")]
        assert config.user_skills_dir == Path("/absolute/skills")
        assert config.custom_paths == [Path("/extra/skills")]
        assert config.auto_discover is False
        assert config.namespace_tools is False
        assert config.trusted_paths == [Path("/trusted/path")]

    def test_invalid_type_raises_validation_error(self) -> None:
        """Test that Pydantic validation catches invalid field types."""
        with pytest.raises(ValidationError):
            SkillConfig(auto_discover="not_a_bool")  # type: ignore[arg-type]


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_valid_result(self) -> None:
        """Test construction of a valid result."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.skill_path is None
        assert result.trust_level is None

    def test_invalid_result_with_errors(self) -> None:
        """Test construction with validation errors."""
        result = ValidationResult(
            valid=False,
            errors=["Missing required field: name", "Invalid scope value"],
        )

        assert result.valid is False
        assert len(result.errors) == 2
        assert "Missing required field: name" in result.errors

    def test_result_with_warnings(self) -> None:
        """Test construction with warnings."""
        result = ValidationResult(
            valid=True,
            warnings=["Deprecated field: compat"],
        )

        assert result.valid is True
        assert len(result.warnings) == 1

    def test_result_with_all_fields(self) -> None:
        """Test construction with all fields set."""
        result = ValidationResult(
            valid=False,
            errors=["Bad field"],
            warnings=["Deprecated usage"],
            skill_path=Path("/skills/test"),
            trust_level=TrustLevel.UNTRUSTED,
        )

        assert result.valid is False
        assert result.errors == ["Bad field"]
        assert result.warnings == ["Deprecated usage"]
        assert result.skill_path == Path("/skills/test")
        assert result.trust_level is TrustLevel.UNTRUSTED
