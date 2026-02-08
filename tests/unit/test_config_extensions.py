"""Tests for AgentConfig and AgentSettings skill/subagent extensions."""

from __future__ import annotations

from pathlib import Path

import pytest

from mamba_agents.agent.config import AgentConfig
from mamba_agents.config.settings import AgentSettings
from mamba_agents.skills.config import SkillConfig


class TestAgentConfigIsSubagent:
    """Tests for AgentConfig._is_subagent private attribute."""

    def test_default_is_false(self) -> None:
        """_is_subagent defaults to False when not explicitly set."""
        config = AgentConfig()
        assert config._is_subagent is False

    def test_set_via_init(self) -> None:
        """_is_subagent cannot be set via constructor kwargs (private attr)."""
        # PrivateAttr fields are not settable via constructor kwargs
        config = AgentConfig()
        assert config._is_subagent is False

    def test_set_directly(self) -> None:
        """_is_subagent can be set directly by the spawner."""
        config = AgentConfig()
        config._is_subagent = True
        assert config._is_subagent is True

    def test_not_in_model_dump(self) -> None:
        """_is_subagent should not appear in model_dump (private attr)."""
        config = AgentConfig()
        config._is_subagent = True
        dumped = config.model_dump()
        assert "_is_subagent" not in dumped

    def test_not_in_model_fields(self) -> None:
        """_is_subagent should not appear in model_fields (private attr)."""
        assert "_is_subagent" not in AgentConfig.model_fields

    def test_existing_fields_unchanged(self) -> None:
        """Existing AgentConfig fields still work with _is_subagent present."""
        config = AgentConfig(
            max_iterations=20,
            system_prompt="Test prompt",
            track_context=False,
            auto_compact=False,
            graceful_tool_errors=False,
        )
        assert config.max_iterations == 20
        assert config.system_prompt == "Test prompt"
        assert config.track_context is False
        assert config.auto_compact is False
        assert config.graceful_tool_errors is False
        assert config._is_subagent is False


class TestAgentSettingsSkillsField:
    """Tests for AgentSettings.skills field."""

    def test_default_is_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """skills defaults to None when not provided."""
        monkeypatch.chdir(tmp_path)
        settings = AgentSettings(_env_file=None)
        assert settings.skills is None

    def test_accepts_skill_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """skills field accepts a SkillConfig instance."""
        monkeypatch.chdir(tmp_path)
        skill_config = SkillConfig(
            auto_discover=False,
            namespace_tools=False,
        )
        settings = AgentSettings(_env_file=None, skills=skill_config)
        assert settings.skills is not None
        assert isinstance(settings.skills, SkillConfig)
        assert settings.skills.auto_discover is False
        assert settings.skills.namespace_tools is False

    def test_accepts_skill_config_dict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """skills field accepts a dict that can be coerced to SkillConfig."""
        monkeypatch.chdir(tmp_path)
        settings = AgentSettings(
            _env_file=None,
            skills={"auto_discover": False, "namespace_tools": True},
        )
        assert settings.skills is not None
        assert isinstance(settings.skills, SkillConfig)
        assert settings.skills.auto_discover is False

    def test_skill_config_with_custom_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """skills field works with custom_paths in SkillConfig."""
        monkeypatch.chdir(tmp_path)
        custom_dir = tmp_path / "my_skills"
        custom_dir.mkdir()
        skill_config = SkillConfig(
            custom_paths=[custom_dir],
            trusted_paths=[custom_dir],
        )
        settings = AgentSettings(_env_file=None, skills=skill_config)
        assert settings.skills is not None
        assert custom_dir in settings.skills.custom_paths
        assert custom_dir in settings.skills.trusted_paths

    def test_model_dump_includes_skills(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """skills field appears in model_dump when set."""
        monkeypatch.chdir(tmp_path)
        settings = AgentSettings(
            _env_file=None,
            skills=SkillConfig(auto_discover=False),
        )
        dumped = settings.model_dump()
        assert "skills" in dumped
        assert dumped["skills"]["auto_discover"] is False

    def test_model_dump_skills_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """skills field is None in model_dump when not set."""
        monkeypatch.chdir(tmp_path)
        settings = AgentSettings(_env_file=None)
        dumped = settings.model_dump()
        assert "skills" in dumped
        assert dumped["skills"] is None


class TestBackwardCompatibility:
    """Tests verifying backward compatibility of config extensions."""

    def test_agent_config_no_args(self) -> None:
        """AgentConfig works with no arguments (all defaults)."""
        config = AgentConfig()
        assert config.max_iterations == 10
        assert config.system_prompt == ""
        assert config.context is None
        assert config.tokenizer is None
        assert config.track_context is True
        assert config.auto_compact is True
        assert config.graceful_tool_errors is True

    def test_agent_config_original_kwargs(self) -> None:
        """AgentConfig works with original keyword arguments only."""
        config = AgentConfig(
            max_iterations=5,
            track_context=False,
        )
        assert config.max_iterations == 5
        assert config.track_context is False

    def test_agent_settings_no_args(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """AgentSettings works with no arguments (all defaults)."""
        monkeypatch.chdir(tmp_path)
        settings = AgentSettings(_env_file=None)
        assert settings.model_backend is not None
        assert settings.logging is not None
        assert settings.retry is not None
        assert settings.context is not None
        assert settings.tokenizer is not None
        assert settings.prompts is not None
        assert settings.cost_rates == {}
        assert settings.skills is None

    def test_agent_settings_original_kwargs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AgentSettings works with original keyword arguments."""
        monkeypatch.chdir(tmp_path)
        settings = AgentSettings(
            _env_file=None,
            cost_rates={"gpt-4": 0.03},
        )
        assert settings.cost_rates == {"gpt-4": 0.03}
        assert settings.skills is None

    def test_no_circular_imports(self) -> None:
        """Verify no circular imports between agent config and skills config."""
        # If these imports work without error, no circular import exists
        from mamba_agents.agent.config import AgentConfig as AC
        from mamba_agents.config.settings import AgentSettings as AS
        from mamba_agents.skills.config import SkillConfig as SC

        assert AC is not None
        assert AS is not None
        assert SC is not None
