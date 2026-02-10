"""Cross-cutting integration tests for the subagents subsystem.

These tests verify interactions between multiple subagent components
(config, errors, loader, spawner, delegation, manager) working together.
Individual module tests are in the sibling ``test_*.py`` files.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents.agent.core import Agent
from mamba_agents.skills.config import Skill, SkillInfo, SkillScope
from mamba_agents.skills.registry import SkillRegistry
from mamba_agents.subagents.config import SubagentConfig
from mamba_agents.subagents.delegation import delegate, delegate_sync
from mamba_agents.subagents.errors import (
    SubagentConfigError,
    SubagentDelegationError,
    SubagentError,
    SubagentNestingError,
    SubagentNotFoundError,
    SubagentTimeoutError,
)
from mamba_agents.subagents.loader import discover_subagents, load_subagent_config
from mamba_agents.subagents.manager import SubagentManager
from mamba_agents.subagents.spawner import spawn


@pytest.fixture
def parent_agent(test_model: TestModel) -> Agent[None, str]:
    """Create a parent agent for cross-cutting tests."""
    return Agent(test_model)


def _make_test_agent(output_text: str = "test output") -> Agent[None, str]:
    """Create a test agent with a specific output text."""
    return Agent(TestModel(custom_output_text=output_text))


# ---------------------------------------------------------------------------
# Loader -> Spawner integration
# ---------------------------------------------------------------------------


class TestLoaderSpawnerIntegration:
    """Tests verifying loader output feeds correctly into spawn()."""

    def test_loaded_config_spawns_subagent(
        self, parent_agent: Agent[None, str], sample_agent_dir: Path
    ) -> None:
        """SubagentConfig from loader can be used with spawn()."""
        config = load_subagent_config(sample_agent_dir / "helper.md")
        subagent = spawn(config, parent_agent)

        assert isinstance(subagent, Agent)
        assert subagent.config._is_subagent is True

    def test_loaded_config_has_system_prompt_from_body(
        self, parent_agent: Agent[None, str], sample_agent_dir: Path
    ) -> None:
        """Subagent spawned from loaded config has body as system prompt."""
        config = load_subagent_config(sample_agent_dir / "helper.md")
        subagent = spawn(config, parent_agent)

        prompt = subagent.get_system_prompt()
        assert "helper" in prompt.lower()

    def test_discovered_configs_all_spawn(
        self, parent_agent: Agent[None, str], sample_agent_dir: Path
    ) -> None:
        """All configs from discover_subagents can be spawned."""
        configs = discover_subagents(project_dir=sample_agent_dir)

        for config in configs:
            subagent = spawn(config, parent_agent)
            assert isinstance(subagent, Agent)
            assert subagent.config._is_subagent is True


# ---------------------------------------------------------------------------
# Loader -> Manager integration
# ---------------------------------------------------------------------------


class TestLoaderManagerIntegration:
    """Tests verifying loader output feeds correctly into SubagentManager."""

    def test_loaded_config_registers_in_manager(
        self, parent_agent: Agent[None, str], sample_agent_dir: Path
    ) -> None:
        """SubagentConfig from loader can be registered in SubagentManager."""
        config = load_subagent_config(sample_agent_dir / "researcher.md")
        manager = SubagentManager(parent_agent)
        manager.register(config)

        assert manager.get("researcher") is not None
        assert len(manager) == 1

    def test_multiple_loaded_configs_register(
        self, parent_agent: Agent[None, str], sample_agent_dir: Path
    ) -> None:
        """Multiple loaded configs can be registered and coexist."""
        configs = discover_subagents(project_dir=sample_agent_dir)
        manager = SubagentManager(parent_agent, configs=configs)

        assert len(manager) == len(configs)
        for config in configs:
            assert manager.get(config.name) is not None


# ---------------------------------------------------------------------------
# Spawner -> Delegation integration
# ---------------------------------------------------------------------------


class TestSpawnerDelegationIntegration:
    """Tests verifying spawned agents work correctly with delegation."""

    def test_spawned_subagent_delegation_sync(self, parent_agent: Agent[None, str]) -> None:
        """Spawned subagent can be used with delegate_sync."""
        config = SubagentConfig(name="sync-worker", description="Sync worker")
        subagent = spawn(config, parent_agent)

        with subagent.override(model=TestModel(custom_output_text="sync result")):
            result = delegate_sync(
                subagent,
                "Process this data",
                subagent_name="sync-worker",
            )

        assert result.success is True
        assert result.output == "sync result"
        assert result.subagent_name == "sync-worker"

    async def test_spawned_subagent_delegation_async(self, parent_agent: Agent[None, str]) -> None:
        """Spawned subagent can be used with async delegate."""
        config = SubagentConfig(name="async-worker", description="Async worker")
        subagent = spawn(config, parent_agent)

        with subagent.override(model=TestModel(custom_output_text="async result")):
            result = await delegate(
                subagent,
                "Process this data async",
                subagent_name="async-worker",
            )

        assert result.success is True
        assert result.output == "async result"

    def test_spawned_subagent_with_custom_prompt_delegates(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Subagent with custom system prompt delegates correctly."""
        config = SubagentConfig(
            name="prompted-worker",
            description="Has prompt",
            system_prompt="You are an expert data analyst.",
        )
        subagent = spawn(config, parent_agent)

        with subagent.override(model=TestModel(custom_output_text="analyzed")):
            result = delegate_sync(subagent, "Analyze this dataset")

        assert result.success is True
        assert result.output == "analyzed"


# ---------------------------------------------------------------------------
# Full lifecycle: Config -> Loader -> Manager -> Delegation
# ---------------------------------------------------------------------------


class TestFullLifecycleIntegration:
    """End-to-end tests exercising the full subagent lifecycle."""

    def test_file_to_delegation_pipeline(
        self, parent_agent: Agent[None, str], sample_agent_dir: Path
    ) -> None:
        """Full pipeline: load from file -> register -> delegate -> result."""
        config = load_subagent_config(sample_agent_dir / "helper.md")

        manager = SubagentManager(parent_agent)
        manager.register(config)

        sub = _make_test_agent("pipeline result")
        with patch.object(manager, "_spawn", return_value=sub):
            result = manager.delegate_sync("helper", "Execute the pipeline")

        assert result.success is True
        assert result.output == "pipeline result"

    def test_discover_register_delegate_lifecycle(
        self, parent_agent: Agent[None, str], sample_agent_dir: Path
    ) -> None:
        """Discover configs -> register all -> delegate to one."""
        configs = discover_subagents(project_dir=sample_agent_dir)
        manager = SubagentManager(parent_agent, configs=configs)

        sub = _make_test_agent("discovered result")
        with patch.object(manager, "_spawn", return_value=sub):
            result = manager.delegate_sync(configs[0].name, "Use discovered config")

        assert result.success is True

    def test_usage_tracks_through_full_lifecycle(self, parent_agent: Agent[None, str]) -> None:
        """Usage is tracked from delegation back through to parent agent."""
        config = SubagentConfig(name="tracked-sub", description="Usage tracking")
        manager = SubagentManager(parent_agent, configs=[config])

        initial_count = parent_agent.get_usage().request_count
        sub = _make_test_agent("tracked")

        with patch.object(manager, "_spawn", return_value=sub):
            result = manager.delegate_sync("tracked-sub", "Track my usage")

        assert result.success is True
        assert parent_agent.get_usage().request_count > initial_count

        breakdown = manager.get_usage_breakdown()
        assert "tracked-sub" in breakdown
        assert breakdown["tracked-sub"].request_count >= 1


# ---------------------------------------------------------------------------
# Error hierarchy cross-cutting
# ---------------------------------------------------------------------------


class TestErrorHierarchyCrossCutting:
    """Tests verifying error hierarchy works correctly across components."""

    def test_all_subagent_errors_catchable_by_base(self) -> None:
        """All subagent errors are catchable via SubagentError."""
        errors = [
            SubagentConfigError(name="test", detail="bad"),
            SubagentNotFoundError(config_name="test"),
            SubagentNestingError(name="test", parent_name="parent"),
            SubagentDelegationError(name="test", task="task"),
            SubagentTimeoutError(name="test", max_turns=10),
        ]

        for err in errors:
            assert isinstance(err, SubagentError)
            assert isinstance(err, Exception)

    def test_nesting_error_propagates_from_spawn_through_manager(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """SubagentNestingError from spawn() propagates through manager."""
        child_config = SubagentConfig(name="child", description="Child")
        child = spawn(child_config, parent_agent)

        manager = SubagentManager(child)
        grandchild = SubagentConfig(name="grandchild", description="Nested")
        manager.register(grandchild)

        with pytest.raises(SubagentNestingError):
            manager.delegate_sync("grandchild", "Should fail")

    def test_config_error_from_loader_catchable_as_base_error(self, tmp_path: Path) -> None:
        """SubagentConfigError from loader is catchable as SubagentError."""
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("no frontmatter here", encoding="utf-8")

        with pytest.raises(SubagentError):
            load_subagent_config(bad_file)


# ---------------------------------------------------------------------------
# Package exports
# ---------------------------------------------------------------------------


class TestPackageExports:
    """Tests verifying the subagents __init__.py exports are correct."""

    def test_all_public_names_importable(self) -> None:
        """All names in __all__ are importable from the package."""
        import mamba_agents.subagents as pkg

        for name in pkg.__all__:
            assert hasattr(pkg, name), f"{name} is in __all__ but not importable"

    def test_expected_exports_present(self) -> None:
        """Expected classes and errors are in the public exports."""
        import mamba_agents.subagents as pkg

        expected = [
            "DelegationHandle",
            "SubagentConfig",
            "SubagentConfigError",
            "SubagentDelegationError",
            "SubagentError",
            "SubagentManager",
            "SubagentNestingError",
            "SubagentNotFoundError",
            "SubagentResult",
            "SubagentTimeoutError",
        ]
        for name in expected:
            assert hasattr(pkg, name), f"{name} not found in subagents package"

    def test_all_list_is_sorted(self) -> None:
        """__all__ list is alphabetically sorted."""
        import mamba_agents.subagents as pkg

        assert pkg.__all__ == sorted(pkg.__all__)


# ---------------------------------------------------------------------------
# Context isolation cross-cutting
# ---------------------------------------------------------------------------


class TestContextIsolationCrossCutting:
    """Tests verifying context isolation between parent and subagents."""

    def test_subagent_context_isolated_from_parent(self, parent_agent: Agent[None, str]) -> None:
        """Subagent has its own context manager, independent from parent."""
        config = SubagentConfig(name="isolated", description="Isolated")
        subagent = spawn(config, parent_agent)

        assert subagent.context_manager is not parent_agent.context_manager
        assert subagent.usage_tracker is not parent_agent.usage_tracker
        assert subagent.get_messages() == []

    def test_subagent_delegation_does_not_pollute_parent_messages(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Messages from subagent delegation do not appear in parent."""
        config = SubagentConfig(name="clean", description="Clean")
        subagent = spawn(config, parent_agent)

        initial_parent_messages = len(parent_agent.get_messages())

        with subagent.override(model=TestModel(custom_output_text="sub msg")):
            delegate_sync(subagent, "Generate some messages")

        # Parent messages should not have increased
        assert len(parent_agent.get_messages()) == initial_parent_messages


# ---------------------------------------------------------------------------
# Skill-based subagent cross-cutting
# ---------------------------------------------------------------------------


class TestSkillSubagentCrossCutting:
    """Tests for subagents that use skills."""

    def test_skill_content_in_spawned_subagent_prompt(self, parent_agent: Agent[None, str]) -> None:
        """Skills are pre-loaded into the subagent's system prompt."""
        registry = SkillRegistry()
        skill = Skill(
            info=SkillInfo(
                name="test-skill",
                description="Test skill",
                path=Path("/fake/test-skill"),
                scope=SkillScope.PROJECT,
            ),
            body="You have special skill capabilities.",
        )
        registry.register(skill)

        config = SubagentConfig(
            name="skilled-sub",
            description="Has skills",
            skills=["test-skill"],
            system_prompt="Base prompt.",
        )
        subagent = spawn(config, parent_agent, skill_registry=registry)

        prompt = subagent.get_system_prompt()
        assert "Base prompt." in prompt
        assert "special skill capabilities" in prompt

    def test_manager_with_skill_registry_passes_registry(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """SubagentManager passes skill registry through to spawn."""
        registry = SkillRegistry()

        manager = SubagentManager(
            parent_agent,
            skill_registry=registry,
        )

        config = SubagentConfig(name="skill-sub", description="With skills")
        manager.register(config)

        sub = _make_test_agent("skilled output")
        with patch.object(manager, "_spawn", return_value=sub):
            result = manager.delegate_sync("skill-sub", "Use skills")

        assert result.success is True
