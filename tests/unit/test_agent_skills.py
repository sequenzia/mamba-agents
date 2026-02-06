"""Tests for Agent skills facade methods."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents import Agent, AgentConfig
from mamba_agents.skills.config import (
    Skill,
    SkillInfo,
    SkillScope,
    TrustLevel,
)
from mamba_agents.skills.errors import SkillNotFoundError
from mamba_agents.skills.manager import SkillManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_SKILL_MD = """\
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
    body: str | None = "Skill body with $ARGUMENTS placeholder.",
    is_active: bool = False,
) -> Skill:
    """Create a minimal Skill for testing."""
    return Skill(
        info=_make_info(name=name, description=description, path=path),
        body=body,
        is_active=is_active,
    )


def _make_skill_dir(
    base_dir: Path,
    name: str,
    description: str = "A test skill",
    body: str | None = None,
) -> Path:
    """Create a skill directory with a valid SKILL.md file."""
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = _MINIMAL_SKILL_MD.format(name=name)
    if body is not None:
        # Replace body section
        frontmatter_end = content.index("---", 3) + 3
        content = content[:frontmatter_end] + "\n\n" + body + "\n"
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir


# ---------------------------------------------------------------------------
# Tests: Lazy SkillManager Initialization
# ---------------------------------------------------------------------------


class TestAgentSkillManagerLazy:
    """Tests for lazy SkillManager initialization."""

    def test_no_skill_manager_created_without_skills(self, test_model: TestModel) -> None:
        """Agent without skills parameter has no SkillManager until accessed."""
        agent: Agent[None, str] = Agent(test_model)
        # Internal attribute should be None
        assert agent._skill_manager is None

    def test_skill_manager_property_creates_lazily(self, test_model: TestModel) -> None:
        """Accessing skill_manager property creates SkillManager lazily."""
        agent: Agent[None, str] = Agent(test_model)
        assert agent._skill_manager is None

        # Access the property
        manager = agent.skill_manager
        assert isinstance(manager, SkillManager)
        assert agent._skill_manager is not None

    def test_skill_manager_returns_same_instance(self, test_model: TestModel) -> None:
        """Multiple accesses to skill_manager return the same instance."""
        agent: Agent[None, str] = Agent(test_model)
        manager1 = agent.skill_manager
        manager2 = agent.skill_manager
        assert manager1 is manager2

    def test_agent_with_empty_skills_list_creates_manager(self, test_model: TestModel) -> None:
        """Agent with empty skills list creates SkillManager but it's empty."""
        agent: Agent[None, str] = Agent(test_model, skills=[])
        assert agent._skill_manager is not None
        assert isinstance(agent._skill_manager, SkillManager)
        assert len(agent._skill_manager) == 0


# ---------------------------------------------------------------------------
# Tests: Agent Construction with Skills
# ---------------------------------------------------------------------------


class TestAgentConstructionWithSkills:
    """Tests for Agent construction with skills parameter."""

    def test_constructor_with_skill_instance(self, test_model: TestModel) -> None:
        """Agent constructed with Skill instance registers it."""
        skill = _make_skill(name="my-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        assert agent._skill_manager is not None
        assert agent.skill_manager.get("my-skill") is not None

    def test_constructor_with_multiple_skills(self, test_model: TestModel) -> None:
        """Agent constructed with multiple skills registers all."""
        skill1 = _make_skill(name="skill-one")
        skill2 = _make_skill(name="skill-two")
        agent: Agent[None, str] = Agent(test_model, skills=[skill1, skill2])

        assert len(agent.skill_manager) == 2
        assert agent.skill_manager.get("skill-one") is not None
        assert agent.skill_manager.get("skill-two") is not None

    def test_constructor_with_path_string(self, test_model: TestModel, tmp_path: Path) -> None:
        """Agent constructed with string path registers skill from directory."""
        _make_skill_dir(tmp_path, "path-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[str(tmp_path / "path-skill")])

        assert agent.skill_manager.get("path-skill") is not None

    def test_constructor_with_path_object(self, test_model: TestModel, tmp_path: Path) -> None:
        """Agent constructed with Path object registers skill from directory."""
        skill_dir = _make_skill_dir(tmp_path, "dir-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill_dir])

        assert agent.skill_manager.get("dir-skill") is not None


# ---------------------------------------------------------------------------
# Tests: Agent Construction with skill_dirs
# ---------------------------------------------------------------------------


class TestAgentConstructionWithSkillDirs:
    """Tests for Agent construction with skill_dirs parameter."""

    def test_constructor_with_skill_dirs(self, test_model: TestModel, tmp_path: Path) -> None:
        """Agent constructed with skill_dirs discovers skills from directories."""
        scan_dir = tmp_path / "skills"
        scan_dir.mkdir()
        _make_skill_dir(scan_dir, "discovered-skill")

        agent: Agent[None, str] = Agent(test_model, skill_dirs=[scan_dir])

        assert agent.skill_manager.get("discovered-skill") is not None

    def test_constructor_with_skill_dirs_string(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Agent constructed with string skill_dirs discovers skills."""
        scan_dir = tmp_path / "skills"
        scan_dir.mkdir()
        _make_skill_dir(scan_dir, "string-dir-skill")

        agent: Agent[None, str] = Agent(test_model, skill_dirs=[str(scan_dir)])

        assert agent.skill_manager.get("string-dir-skill") is not None

    def test_constructor_with_multiple_skill_dirs(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Agent with multiple skill_dirs discovers from all."""
        dir_a = tmp_path / "skills_a"
        dir_a.mkdir()
        _make_skill_dir(dir_a, "skill-a")

        dir_b = tmp_path / "skills_b"
        dir_b.mkdir()
        _make_skill_dir(dir_b, "skill-b")

        agent: Agent[None, str] = Agent(test_model, skill_dirs=[dir_a, dir_b])

        assert agent.skill_manager.get("skill-a") is not None
        assert agent.skill_manager.get("skill-b") is not None

    def test_constructor_with_both_skills_and_dirs(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Agent with both skills and skill_dirs registers all."""
        skill = _make_skill(name="direct-skill")

        scan_dir = tmp_path / "skills"
        scan_dir.mkdir()
        _make_skill_dir(scan_dir, "dir-skill")

        agent: Agent[None, str] = Agent(test_model, skills=[skill], skill_dirs=[scan_dir])

        assert agent.skill_manager.get("direct-skill") is not None
        assert agent.skill_manager.get("dir-skill") is not None

    def test_constructor_with_empty_skill_dirs(self, test_model: TestModel, tmp_path: Path) -> None:
        """Agent with empty skill_dirs creates manager with no skills."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        agent: Agent[None, str] = Agent(test_model, skill_dirs=[empty_dir])

        assert agent._skill_manager is not None
        assert len(agent.skill_manager) == 0


# ---------------------------------------------------------------------------
# Tests: Facade Method Delegation
# ---------------------------------------------------------------------------


class TestAgentSkillFacadeMethods:
    """Tests for Agent skill facade method delegation."""

    def test_register_skill_with_skill_instance(self, test_model: TestModel) -> None:
        """register_skill() with Skill instance delegates to SkillManager."""
        agent: Agent[None, str] = Agent(test_model)
        skill = _make_skill(name="registered-skill")

        agent.register_skill(skill)

        assert agent.skill_manager.get("registered-skill") is not None

    def test_register_skill_with_path(self, test_model: TestModel, tmp_path: Path) -> None:
        """register_skill() with Path delegates to SkillManager."""
        skill_dir = _make_skill_dir(tmp_path, "path-reg-skill")

        agent: Agent[None, str] = Agent(test_model)
        agent.register_skill(skill_dir)

        assert agent.skill_manager.get("path-reg-skill") is not None

    def test_register_skill_with_string_path(self, test_model: TestModel, tmp_path: Path) -> None:
        """register_skill() with string path delegates to SkillManager."""
        _make_skill_dir(tmp_path, "str-reg-skill")

        agent: Agent[None, str] = Agent(test_model)
        agent.register_skill(str(tmp_path / "str-reg-skill"))

        assert agent.skill_manager.get("str-reg-skill") is not None

    def test_get_skill_returns_skill(self, test_model: TestModel) -> None:
        """get_skill() returns the Skill instance."""
        skill = _make_skill(name="get-me")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        result = agent.get_skill("get-me")
        assert result is not None
        assert result.info.name == "get-me"

    def test_get_skill_returns_none_for_missing(self, test_model: TestModel) -> None:
        """get_skill() returns None for non-existent skill."""
        agent: Agent[None, str] = Agent(test_model)

        result = agent.get_skill("nonexistent")
        assert result is None

    def test_list_skills_returns_metadata(self, test_model: TestModel) -> None:
        """list_skills() returns list of SkillInfo."""
        skill1 = _make_skill(name="skill-alpha")
        skill2 = _make_skill(name="skill-beta")
        agent: Agent[None, str] = Agent(test_model, skills=[skill1, skill2])

        skills = agent.list_skills()
        assert len(skills) == 2
        names = {s.name for s in skills}
        assert names == {"skill-alpha", "skill-beta"}

    def test_list_skills_empty_when_no_skills(self, test_model: TestModel) -> None:
        """list_skills() returns empty list when no skills registered."""
        agent: Agent[None, str] = Agent(test_model)

        skills = agent.list_skills()
        assert skills == []

    def test_invoke_skill_activates_and_returns_content(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """invoke_skill() activates skill and returns processed content."""
        skill_dir = _make_skill_dir(tmp_path, "invoke-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill_dir])

        result = agent.invoke_skill("invoke-skill")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_invoke_skill_with_arguments(self, test_model: TestModel, tmp_path: Path) -> None:
        """invoke_skill() passes arguments to the skill."""
        skill_dir = tmp_path / "arg-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: arg-skill\ndescription: Arg skill\n---\n\nContent with $ARGUMENTS here."
        )

        agent: Agent[None, str] = Agent(test_model, skills=[skill_dir])
        result = agent.invoke_skill("arg-skill", "hello", "world")

        assert "hello world" in result

    def test_invoke_skill_raises_for_missing_skill(self, test_model: TestModel) -> None:
        """invoke_skill() raises SkillNotFoundError for missing skill."""
        agent: Agent[None, str] = Agent(test_model)

        with pytest.raises(SkillNotFoundError):
            agent.invoke_skill("nonexistent")


# ---------------------------------------------------------------------------
# Tests: Backward Compatibility
# ---------------------------------------------------------------------------


class TestAgentSkillsBackwardCompatibility:
    """Tests for backward compatibility — Agent works fine without skills."""

    def test_agent_without_skills_works(self, test_model: TestModel) -> None:
        """Agent created without skills parameter works normally."""
        agent: Agent[None, str] = Agent(test_model)

        # All existing functionality should work
        assert agent.config is not None
        assert agent.usage_tracker is not None
        assert agent.token_counter is not None
        assert agent.context_manager is not None

    def test_agent_run_sync_without_skills(self, test_model: TestModel) -> None:
        """Agent can run_sync without skills parameter."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)
        result = agent.run_sync("Hello")
        assert result.output == "Hello!"

    async def test_agent_run_without_skills(self, test_model: TestModel) -> None:
        """Agent can run without skills parameter."""
        model = TestModel(custom_output_text="Hello async!")
        agent: Agent[None, str] = Agent(model)
        result = await agent.run("Hello")
        assert result.output == "Hello async!"

    def test_existing_constructor_args_unchanged(self, test_model: TestModel) -> None:
        """Existing constructor arguments continue to work."""
        config = AgentConfig(
            track_context=False,
            system_prompt="You are helpful.",
        )
        agent: Agent[None, str] = Agent(
            test_model,
            config=config,
        )
        assert agent.get_system_prompt() == "You are helpful."
        assert agent.context_manager is None


# ---------------------------------------------------------------------------
# Tests: Integration (Agent + Skills end-to-end)
# ---------------------------------------------------------------------------


class TestAgentSkillsIntegration:
    """Integration tests for Agent with skills end-to-end."""

    def test_full_lifecycle_register_get_list_invoke(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Full lifecycle: construct, register, get, list, invoke."""
        agent: Agent[None, str] = Agent(test_model)

        # Register a skill
        skill_dir = _make_skill_dir(tmp_path, "lifecycle-skill")
        agent.register_skill(skill_dir)

        # Get it
        skill = agent.get_skill("lifecycle-skill")
        assert skill is not None
        assert skill.info.name == "lifecycle-skill"

        # List all
        skills = agent.list_skills()
        assert len(skills) == 1
        assert skills[0].name == "lifecycle-skill"

        # Invoke it
        content = agent.invoke_skill("lifecycle-skill")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_constructor_skills_and_later_registration(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Skills from constructor and later registration coexist."""
        skill_dir1 = _make_skill_dir(tmp_path, "initial-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill_dir1])

        # Register another skill later
        skill_dir2 = _make_skill_dir(tmp_path, "later-skill")
        agent.register_skill(skill_dir2)

        assert len(agent.list_skills()) == 2
        assert agent.get_skill("initial-skill") is not None
        assert agent.get_skill("later-skill") is not None

    def test_skill_manager_uses_settings_config(self, test_model: TestModel) -> None:
        """SkillManager uses SkillConfig from settings when available."""
        from mamba_agents.config.settings import AgentSettings
        from mamba_agents.skills.config import SkillConfig

        skill_config = SkillConfig(namespace_tools=False)
        settings = AgentSettings(skills=skill_config)

        agent: Agent[None, str] = Agent(test_model, settings=settings, skills=[])

        # The manager should use the settings config
        assert agent.skill_manager.config.namespace_tools is False

    def test_skill_manager_default_config_when_settings_none(self, test_model: TestModel) -> None:
        """SkillManager uses default SkillConfig when settings.skills is None."""
        agent: Agent[None, str] = Agent(test_model)

        # Accessing skill_manager should not raise, even with no skills config
        manager = agent.skill_manager
        assert isinstance(manager, SkillManager)
