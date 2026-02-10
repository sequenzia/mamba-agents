"""Tests for Agent subagent facade methods."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents import Agent, AgentConfig
from mamba_agents.subagents.config import DelegationHandle, SubagentConfig, SubagentResult
from mamba_agents.subagents.errors import SubagentConfigError, SubagentNotFoundError
from mamba_agents.subagents.manager import SubagentManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    name: str = "helper",
    description: str = "A helpful subagent",
    model: str | None = None,
) -> SubagentConfig:
    """Create a minimal SubagentConfig for testing."""
    return SubagentConfig(name=name, description=description, model=model)


def _make_test_agent(output_text: str = "test output") -> Agent[None, str]:
    """Create a test agent with a specific output text for subagent mocking."""
    return Agent(TestModel(custom_output_text=output_text))


# ---------------------------------------------------------------------------
# Tests: Explicit SubagentManager Initialization
# ---------------------------------------------------------------------------


class TestAgentSubagentManagerInit:
    """Tests for explicit SubagentManager initialization via init_subagents()."""

    def test_no_subagent_manager_created_without_init(self, test_model: TestModel) -> None:
        """Agent without subagents parameter has no SubagentManager."""
        agent: Agent[None, str] = Agent(test_model)
        assert agent._subagent_manager is None
        assert agent.has_subagent_manager is False

    def test_has_subagent_manager_false_before_init(self, test_model: TestModel) -> None:
        """has_subagent_manager returns False before init_subagents() is called."""
        agent: Agent[None, str] = Agent(test_model)
        assert agent.has_subagent_manager is False

    def test_has_subagent_manager_true_after_init(self, test_model: TestModel) -> None:
        """has_subagent_manager returns True after init_subagents() is called."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()
        assert agent.has_subagent_manager is True

    def test_subagent_manager_property_raises_before_init(self, test_model: TestModel) -> None:
        """Accessing subagent_manager before init_subagents() raises AttributeError."""
        agent: Agent[None, str] = Agent(test_model)

        with pytest.raises(AttributeError, match="init_subagents"):
            _ = agent.subagent_manager

    def test_subagent_manager_property_returns_after_init(self, test_model: TestModel) -> None:
        """Accessing subagent_manager after init_subagents() returns SubagentManager."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()

        manager = agent.subagent_manager
        assert isinstance(manager, SubagentManager)

    def test_subagent_manager_returns_same_instance(self, test_model: TestModel) -> None:
        """Multiple accesses to subagent_manager return the same instance."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()
        manager1 = agent.subagent_manager
        manager2 = agent.subagent_manager
        assert manager1 is manager2

    def test_init_subagents_double_call_is_idempotent(self, test_model: TestModel) -> None:
        """Calling init_subagents() twice is a no-op on the second call."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()
        manager1 = agent.subagent_manager

        # Second call should not replace the manager
        agent.init_subagents(subagents=[_make_config(name="extra")])
        manager2 = agent.subagent_manager
        assert manager1 is manager2
        # The extra config should NOT be registered (idempotent no-op)
        assert agent.subagent_manager.get("extra") is None

    def test_agent_with_empty_subagents_list_creates_manager(self, test_model: TestModel) -> None:
        """Agent with empty subagents list creates SubagentManager but it's empty."""
        agent: Agent[None, str] = Agent(test_model, subagents=[])
        assert agent._subagent_manager is not None
        assert isinstance(agent._subagent_manager, SubagentManager)
        assert len(agent._subagent_manager) == 0

    def test_init_subagents_on_subagent_raises(self, test_model: TestModel) -> None:
        """Subagent cannot call init_subagents()."""
        config = AgentConfig()
        config._is_subagent = True
        agent: Agent[None, str] = Agent(test_model, config=config)

        with pytest.raises(RuntimeError, match="Subagents cannot"):
            agent.init_subagents()


# ---------------------------------------------------------------------------
# Tests: Agent Construction with Subagents
# ---------------------------------------------------------------------------


class TestAgentConstructionWithSubagents:
    """Tests for Agent construction with subagents parameter."""

    def test_constructor_with_single_config(self, test_model: TestModel) -> None:
        """Agent constructed with single SubagentConfig registers it."""
        config = _make_config(name="my-helper")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])

        assert agent._subagent_manager is not None
        assert agent.subagent_manager.get("my-helper") is not None

    def test_constructor_with_multiple_configs(self, test_model: TestModel) -> None:
        """Agent constructed with multiple configs registers all."""
        config1 = _make_config(name="helper-one")
        config2 = _make_config(name="helper-two")
        agent: Agent[None, str] = Agent(test_model, subagents=[config1, config2])

        assert len(agent.subagent_manager) == 2
        assert agent.subagent_manager.get("helper-one") is not None
        assert agent.subagent_manager.get("helper-two") is not None

    def test_constructor_configs_accessible_via_list_subagents(self, test_model: TestModel) -> None:
        """Configs passed to constructor are accessible via list_subagents()."""
        config1 = _make_config(name="alpha")
        config2 = _make_config(name="beta")
        agent: Agent[None, str] = Agent(test_model, subagents=[config1, config2])

        configs = agent.list_subagents()
        names = {c.name for c in configs}
        assert names == {"alpha", "beta"}

    def test_constructor_auto_calls_init_subagents(self, test_model: TestModel) -> None:
        """Agent(subagents=[...]) auto-calls init_subagents()."""
        config = _make_config(name="auto-init")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])

        assert agent.has_subagent_manager is True
        assert agent.subagent_manager.get("auto-init") is not None


# ---------------------------------------------------------------------------
# Tests: Facade Method Delegation
# ---------------------------------------------------------------------------


class TestAgentSubagentFacadeMethods:
    """Tests for Agent subagent facade method delegation."""

    def test_register_subagent(self, test_model: TestModel) -> None:
        """register_subagent() delegates to SubagentManager.register()."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()
        config = _make_config(name="registered-agent")

        agent.register_subagent(config)

        assert agent.subagent_manager.get("registered-agent") is not None

    def test_register_subagent_without_init_raises(self, test_model: TestModel) -> None:
        """register_subagent() without init_subagents() raises AttributeError."""
        agent: Agent[None, str] = Agent(test_model)
        config = _make_config(name="orphan")

        with pytest.raises(AttributeError, match="init_subagents"):
            agent.register_subagent(config)

    def test_register_subagent_invalid_raises(self, test_model: TestModel) -> None:
        """register_subagent() with invalid config raises SubagentConfigError."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()
        config = SubagentConfig(name="  ", description="Blank name")

        with pytest.raises(SubagentConfigError, match="must not be empty"):
            agent.register_subagent(config)

    def test_list_subagents_returns_configs(self, test_model: TestModel) -> None:
        """list_subagents() returns list of SubagentConfig."""
        config1 = _make_config(name="agent-alpha")
        config2 = _make_config(name="agent-beta")
        agent: Agent[None, str] = Agent(test_model, subagents=[config1, config2])

        configs = agent.list_subagents()
        assert len(configs) == 2
        names = {c.name for c in configs}
        assert names == {"agent-alpha", "agent-beta"}

    def test_list_subagents_raises_without_init(self, test_model: TestModel) -> None:
        """list_subagents() raises AttributeError when not initialized."""
        agent: Agent[None, str] = Agent(test_model)

        with pytest.raises(AttributeError, match="init_subagents"):
            agent.list_subagents()

    def test_delegate_sync_delegates_to_manager(self, test_model: TestModel) -> None:
        """delegate_sync() delegates to SubagentManager.delegate_sync()."""
        config = _make_config(name="sync-agent")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("sync result")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            result = agent.delegate_sync("sync-agent", "Do something")

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "sync result"
        assert result.subagent_name == "sync-agent"

    def test_delegate_sync_unknown_raises(self, test_model: TestModel) -> None:
        """delegate_sync() to unknown config raises SubagentNotFoundError."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()

        with pytest.raises(SubagentNotFoundError, match="unknown"):
            agent.delegate_sync("unknown", "Some task")

    async def test_delegate_delegates_to_manager(self, test_model: TestModel) -> None:
        """delegate() delegates to SubagentManager.delegate() (async)."""
        config = _make_config(name="async-agent")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("async result")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            result = await agent.delegate("async-agent", "Async task")

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "async result"

    async def test_delegate_unknown_raises(self, test_model: TestModel) -> None:
        """delegate() to unknown config raises SubagentNotFoundError."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()

        with pytest.raises(SubagentNotFoundError, match="missing"):
            await agent.delegate("missing", "Some task")

    async def test_delegate_async_returns_handle(self, test_model: TestModel) -> None:
        """delegate_async() returns DelegationHandle."""
        config = _make_config(name="bg-agent")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("bg result")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            handle = await agent.delegate_async("bg-agent", "Background task")

        assert isinstance(handle, DelegationHandle)
        assert handle.subagent_name == "bg-agent"

        # Await the result
        result = await handle.result()
        assert result.success is True
        assert result.output == "bg result"

    async def test_delegate_async_unknown_raises(self, test_model: TestModel) -> None:
        """delegate_async() to unknown config raises SubagentNotFoundError."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()

        with pytest.raises(SubagentNotFoundError, match="nope"):
            await agent.delegate_async("nope", "Some task")


# ---------------------------------------------------------------------------
# Tests: Token Usage Aggregation
# ---------------------------------------------------------------------------


class TestAgentSubagentTokenAggregation:
    """Tests for token usage aggregation from subagent delegations."""

    def test_delegate_sync_aggregates_to_parent_tracker(self, test_model: TestModel) -> None:
        """delegate_sync aggregates subagent usage to parent's UsageTracker."""
        config = _make_config(name="tracked-agent")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("tracked output")

        # Record initial usage
        initial_usage = agent.get_usage()
        initial_total = initial_usage.total_tokens

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            agent.delegate_sync("tracked-agent", "Track this")

        # Usage should have increased
        updated_usage = agent.get_usage()
        assert updated_usage.total_tokens >= initial_total

    async def test_delegate_aggregates_to_parent_tracker(self, test_model: TestModel) -> None:
        """delegate() aggregates subagent usage to parent's UsageTracker."""
        config = _make_config(name="async-tracked")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("async tracked")

        initial_total = agent.get_usage().total_tokens

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            await agent.delegate("async-tracked", "Track async")

        assert agent.get_usage().total_tokens >= initial_total

    def test_usage_breakdown_on_manager(self, test_model: TestModel) -> None:
        """SubagentManager tracks per-subagent usage breakdown."""
        config = _make_config(name="breakdown-agent")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("breakdown output")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            agent.delegate_sync("breakdown-agent", "Break it down")

        breakdown = agent.subagent_manager.get_usage_breakdown()
        assert "breakdown-agent" in breakdown


# ---------------------------------------------------------------------------
# Tests: Backward Compatibility
# ---------------------------------------------------------------------------


class TestAgentSubagentsBackwardCompatibility:
    """Tests for backward compatibility -- Agent works fine without subagents."""

    def test_agent_without_subagents_works(self, test_model: TestModel) -> None:
        """Agent created without subagents parameter works normally."""
        agent: Agent[None, str] = Agent(test_model)

        assert agent.config is not None
        assert agent.usage_tracker is not None
        assert agent.token_counter is not None
        assert agent.context_manager is not None

    def test_agent_run_sync_without_subagents(self, test_model: TestModel) -> None:
        """Agent can run_sync without subagents parameter."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)
        result = agent.run_sync("Hello")
        assert result.output == "Hello!"

    async def test_agent_run_without_subagents(self, test_model: TestModel) -> None:
        """Agent can run without subagents parameter."""
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

    def test_subagent_manager_not_created_on_construction(self, test_model: TestModel) -> None:
        """No SubagentManager is created when subagents param is not passed."""
        agent: Agent[None, str] = Agent(test_model)
        assert agent._subagent_manager is None


# ---------------------------------------------------------------------------
# Tests: Integration (Agent + Subagents end-to-end)
# ---------------------------------------------------------------------------


class TestAgentSubagentsIntegration:
    """Integration tests for Agent with subagents end-to-end."""

    def test_full_lifecycle_init_register_list_delegate(self, test_model: TestModel) -> None:
        """Full lifecycle: init, register, list, delegate."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()

        # Register a subagent
        config = _make_config(name="lifecycle-agent")
        agent.register_subagent(config)

        # List all
        configs = agent.list_subagents()
        assert len(configs) == 1
        assert configs[0].name == "lifecycle-agent"

        # Delegate (sync)
        sub = _make_test_agent("lifecycle output")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            result = agent.delegate_sync("lifecycle-agent", "Do the lifecycle thing")

        assert result.success is True
        assert result.output == "lifecycle output"

    def test_constructor_configs_and_later_registration(self, test_model: TestModel) -> None:
        """Subagents from constructor and later registration coexist."""
        config1 = _make_config(name="initial-agent")
        agent: Agent[None, str] = Agent(test_model, subagents=[config1])

        # Register another later
        config2 = _make_config(name="later-agent")
        agent.register_subagent(config2)

        assert len(agent.list_subagents()) == 2
        assert agent.subagent_manager.get("initial-agent") is not None
        assert agent.subagent_manager.get("later-agent") is not None

    def test_subagent_manager_receives_parent_agent(self, test_model: TestModel) -> None:
        """SubagentManager receives the parent agent reference."""
        config = _make_config(name="parent-check")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])

        assert agent.subagent_manager._parent_agent is agent

    def test_subagent_manager_explicit_init_also_gets_parent(self, test_model: TestModel) -> None:
        """Explicit init_subagents() also receives the parent agent reference."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_subagents()

        manager = agent.subagent_manager
        assert manager._parent_agent is agent

    def test_nesting_error_from_subagent(self, test_model: TestModel) -> None:
        """Subagent trying to spawn sub-subagent raises nesting error.

        The nesting prevention is enforced by the spawner module when
        ``_is_subagent`` is set on the config. This test verifies the
        flag is set correctly via SubagentManager.
        """
        config = _make_config(name="nested-check")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])

        # Spawn a subagent through the manager
        from mamba_agents.subagents.errors import SubagentNestingError
        from mamba_agents.subagents.spawner import spawn

        subagent = spawn(config, agent)

        # The spawned subagent should have _is_subagent=True
        assert subagent.config._is_subagent is True

        # Trying to spawn from the subagent should raise
        with pytest.raises(SubagentNestingError):
            spawn(config, subagent)
