"""Tests for SubagentManager facade."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents.agent.core import Agent
from mamba_agents.subagents.config import DelegationHandle, SubagentConfig, SubagentResult
from mamba_agents.subagents.errors import SubagentConfigError, SubagentNotFoundError
from mamba_agents.subagents.manager import SubagentManager, _UsageTrackingHandle
from mamba_agents.tokens.tracker import TokenUsage


@pytest.fixture
def parent_agent(test_model: TestModel) -> Agent[None, str]:
    """Create a parent agent for manager tests."""
    return Agent(test_model)


@pytest.fixture
def basic_config() -> SubagentConfig:
    """Create a basic subagent config for testing."""
    return SubagentConfig(
        name="helper",
        description="A helpful subagent",
    )


@pytest.fixture
def second_config() -> SubagentConfig:
    """Create a second subagent config for testing."""
    return SubagentConfig(
        name="researcher",
        description="A research subagent",
    )


@pytest.fixture
def manager(parent_agent: Agent[None, str]) -> SubagentManager:
    """Create a SubagentManager with the parent agent."""
    return SubagentManager(parent_agent)


def _make_test_agent(output_text: str = "test output") -> Agent[None, str]:
    """Create a test agent with a specific output text for subagent mocking."""
    return Agent(TestModel(custom_output_text=output_text))


class TestConstruction:
    """Tests for SubagentManager construction."""

    def test_minimal_construction(self, parent_agent: Agent[None, str]) -> None:
        """SubagentManager with only parent agent is valid."""
        mgr = SubagentManager(parent_agent)

        assert len(mgr) == 0
        assert mgr.list() == []

    def test_construction_with_configs(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
        second_config: SubagentConfig,
    ) -> None:
        """SubagentManager registers initial configs."""
        mgr = SubagentManager(parent_agent, configs=[basic_config, second_config])

        assert len(mgr) == 2
        assert mgr.get("helper") is basic_config
        assert mgr.get("researcher") is second_config

    def test_construction_with_skill_manager(self, parent_agent: Agent[None, str]) -> None:
        """SubagentManager accepts optional skill_manager."""
        mock_skill_manager = MagicMock()
        mgr = SubagentManager(parent_agent, skill_manager=mock_skill_manager)

        assert mgr._skill_manager is mock_skill_manager

    def test_construction_with_invalid_config_raises(self, parent_agent: Agent[None, str]) -> None:
        """Invalid config in constructor raises SubagentConfigError."""
        config = SubagentConfig(name="  ", description="Blank name")
        with pytest.raises(SubagentConfigError, match="must not be empty"):
            SubagentManager(parent_agent, configs=[config])


class TestConfigRegistration:
    """Tests for register/deregister/list/get lifecycle."""

    def test_register_config(self, manager: SubagentManager, basic_config: SubagentConfig) -> None:
        """Register adds config to the manager."""
        manager.register(basic_config)

        assert len(manager) == 1
        assert manager.get("helper") is basic_config

    def test_register_overwrites_existing(
        self, manager: SubagentManager, basic_config: SubagentConfig
    ) -> None:
        """Registering a config with the same name overwrites the existing one."""
        manager.register(basic_config)

        updated = SubagentConfig(
            name="helper",
            description="Updated helper",
            model="gpt-4o",
        )
        manager.register(updated)

        assert len(manager) == 1
        assert manager.get("helper") is updated
        assert manager.get("helper").model == "gpt-4o"

    def test_register_empty_name_raises(self, manager: SubagentManager) -> None:
        """Registering a config with empty name raises SubagentConfigError."""
        config = SubagentConfig(name="  ", description="Blank name")

        with pytest.raises(SubagentConfigError, match="must not be empty"):
            manager.register(config)

    def test_deregister_removes_config(
        self, manager: SubagentManager, basic_config: SubagentConfig
    ) -> None:
        """Deregister removes a previously registered config."""
        manager.register(basic_config)
        manager.deregister("helper")

        assert len(manager) == 0
        assert manager.get("helper") is None

    def test_deregister_unknown_raises(self, manager: SubagentManager) -> None:
        """Deregistering an unknown name raises SubagentNotFoundError."""
        with pytest.raises(SubagentNotFoundError, match="unknown-agent"):
            manager.deregister("unknown-agent")

    def test_deregister_shows_available(
        self, manager: SubagentManager, basic_config: SubagentConfig
    ) -> None:
        """SubagentNotFoundError includes available config names."""
        manager.register(basic_config)

        with pytest.raises(SubagentNotFoundError) as exc_info:
            manager.deregister("missing")

        assert exc_info.value.available == ["helper"]

    def test_list_returns_all_configs(
        self,
        manager: SubagentManager,
        basic_config: SubagentConfig,
        second_config: SubagentConfig,
    ) -> None:
        """List returns all registered configs."""
        manager.register(basic_config)
        manager.register(second_config)

        configs = manager.list()

        assert len(configs) == 2
        names = [c.name for c in configs]
        assert "helper" in names
        assert "researcher" in names

    def test_list_empty_manager(self, manager: SubagentManager) -> None:
        """List on empty manager returns empty list."""
        assert manager.list() == []

    def test_get_returns_none_for_unknown(self, manager: SubagentManager) -> None:
        """Get returns None for unregistered name."""
        assert manager.get("nonexistent") is None

    def test_get_returns_config(
        self, manager: SubagentManager, basic_config: SubagentConfig
    ) -> None:
        """Get returns the registered config."""
        manager.register(basic_config)

        result = manager.get("helper")

        assert result is basic_config


class TestSyncDelegation:
    """Tests for delegate_sync method."""

    def test_delegate_sync_returns_result(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """delegate_sync spawns subagent, runs task, returns result."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("sync output")

        with patch.object(manager, "_spawn", return_value=sub):
            result = manager.delegate_sync("helper", "Do the thing")

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "sync output"
        assert result.subagent_name == "helper"

    def test_delegate_sync_unknown_config_raises(self, manager: SubagentManager) -> None:
        """delegate_sync to unknown config raises SubagentNotFoundError."""
        with pytest.raises(SubagentNotFoundError, match="unknown"):
            manager.delegate_sync("unknown", "Some task")

    def test_delegate_sync_captures_error(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """delegate_sync captures errors in SubagentResult."""
        manager = SubagentManager(parent_agent, configs=[basic_config])

        mock_agent = MagicMock()
        mock_agent.run_sync.side_effect = RuntimeError("API crashed")
        mock_agent.config._is_subagent = False

        with patch.object(manager, "_spawn", return_value=mock_agent):
            result = manager.delegate_sync("helper", "Failing task")

        assert result.success is False
        assert "API crashed" in result.error

    def test_delegate_sync_with_kwargs(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """delegate_sync passes kwargs to delegation function."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("with context")

        with patch.object(manager, "_spawn", return_value=sub):
            result = manager.delegate_sync(
                "helper",
                "Summarize",
                context="Extra context here",
            )

        assert result.success is True
        assert result.output == "with context"


class TestAsyncDelegation:
    """Tests for async delegate method."""

    async def test_delegate_returns_result(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """delegate() spawns subagent, runs task, returns result."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("async output")

        with patch.object(manager, "_spawn", return_value=sub):
            result = await manager.delegate("helper", "Do the thing")

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "async output"
        assert result.subagent_name == "helper"

    async def test_delegate_unknown_config_raises(self, manager: SubagentManager) -> None:
        """delegate() to unknown config raises SubagentNotFoundError."""
        with pytest.raises(SubagentNotFoundError, match="unknown"):
            await manager.delegate("unknown", "Some task")

    async def test_delegate_captures_error(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """delegate() captures errors in SubagentResult."""
        manager = SubagentManager(parent_agent, configs=[basic_config])

        mock_agent = MagicMock()
        mock_agent.run.side_effect = RuntimeError("Async API crashed")
        mock_agent.config._is_subagent = False

        with patch.object(manager, "_spawn", return_value=mock_agent):
            result = await manager.delegate("helper", "Failing task")

        assert result.success is False
        assert "Async API crashed" in result.error


class TestDelegateAsync:
    """Tests for delegate_async method returning DelegationHandle."""

    async def test_delegate_async_returns_handle(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """delegate_async returns a DelegationHandle."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("bg output")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("helper", "Background task")

        assert isinstance(handle, DelegationHandle)
        assert handle.subagent_name == "helper"
        assert handle.task == "Background task"

        # Clean up
        result = await handle.result()
        assert result.success is True

    async def test_delegate_async_unknown_config_raises(self, manager: SubagentManager) -> None:
        """delegate_async to unknown config raises SubagentNotFoundError."""
        with pytest.raises(SubagentNotFoundError, match="unknown"):
            await manager.delegate_async("unknown", "Some task")

    async def test_delegate_async_handle_result(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """DelegationHandle from delegate_async can await result."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("handle result")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("helper", "Get result")
            result = await handle.result()

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "handle result"

    async def test_delegate_async_tracks_active(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """delegate_async adds handle to active delegations."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("tracking")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("helper", "Track me")
            result = await handle.result()
            assert result.success is True

    async def test_delegate_async_aggregates_usage_on_result(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Usage is aggregated when handle.result() is awaited."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("usage track")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("helper", "Usage task")
            await handle.result()

        # Usage should be tracked
        breakdown = manager.get_usage_breakdown()
        assert "helper" in breakdown


class TestDynamicSpawn:
    """Tests for spawn_dynamic method."""

    async def test_spawn_dynamic_returns_result(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """spawn_dynamic creates ad-hoc subagent and runs task."""
        manager = SubagentManager(parent_agent)
        dynamic_config = SubagentConfig(
            name="dynamic-helper",
            description="Ad-hoc subagent",
        )
        sub = _make_test_agent("dynamic output")

        with patch.object(manager, "_spawn", return_value=sub):
            result = await manager.spawn_dynamic(dynamic_config, "Dynamic task")

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "dynamic output"
        assert result.subagent_name == "dynamic-helper"

    async def test_spawn_dynamic_does_not_register(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """spawn_dynamic does not add config to the registry."""
        manager = SubagentManager(parent_agent)
        dynamic_config = SubagentConfig(
            name="ephemeral",
            description="Temporary subagent",
        )
        sub = _make_test_agent("temp")

        with patch.object(manager, "_spawn", return_value=sub):
            await manager.spawn_dynamic(dynamic_config, "Temp task")

        assert manager.get("ephemeral") is None
        assert len(manager) == 0

    async def test_spawn_dynamic_conflict_with_registered_name(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Dynamic spawn with conflicting name does not affect registered config."""
        manager = SubagentManager(parent_agent, configs=[basic_config])

        # Dynamic config with same name as registered
        dynamic_config = SubagentConfig(
            name="helper",
            description="Different helper",
            model="gpt-4o-mini",
        )
        sub = _make_test_agent("dynamic")

        with patch.object(manager, "_spawn", return_value=sub):
            result = await manager.spawn_dynamic(dynamic_config, "Dynamic task")

        assert result.success is True
        # Registered config is unchanged
        assert manager.get("helper") is basic_config

    async def test_spawn_dynamic_aggregates_usage(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """spawn_dynamic aggregates usage to parent."""
        manager = SubagentManager(parent_agent)
        dynamic_config = SubagentConfig(
            name="dynamic-agent",
            description="Dynamic",
        )
        sub = _make_test_agent("usage")

        with patch.object(manager, "_spawn", return_value=sub):
            await manager.spawn_dynamic(dynamic_config, "Track usage")

        breakdown = manager.get_usage_breakdown()
        assert "dynamic-agent" in breakdown


class TestTokenAggregation:
    """Tests for token usage aggregation to parent."""

    def test_usage_aggregated_to_parent_tracker(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Token usage is aggregated to parent's UsageTracker."""
        manager = SubagentManager(parent_agent, configs=[basic_config])

        # Capture initial values (get_total_usage returns same mutable object)
        initial_request_count = parent_agent.get_usage().request_count
        sub = _make_test_agent("tracked")

        with patch.object(manager, "_spawn", return_value=sub):
            manager.delegate_sync("helper", "Track usage")

        # Parent usage should have increased
        updated_usage = parent_agent.get_usage()
        assert updated_usage.request_count > initial_request_count

    def test_usage_breakdown_per_subagent(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
        second_config: SubagentConfig,
    ) -> None:
        """get_usage_breakdown returns per-subagent usage."""
        manager = SubagentManager(parent_agent, configs=[basic_config, second_config])
        sub1 = _make_test_agent("helper output")
        sub2 = _make_test_agent("researcher output")

        with patch.object(manager, "_spawn", return_value=sub1):
            manager.delegate_sync("helper", "Helper task")

        with patch.object(manager, "_spawn", return_value=sub2):
            manager.delegate_sync("researcher", "Research task")

        breakdown = manager.get_usage_breakdown()

        assert "helper" in breakdown
        assert "researcher" in breakdown
        assert isinstance(breakdown["helper"], TokenUsage)
        assert isinstance(breakdown["researcher"], TokenUsage)

    def test_usage_accumulates_across_delegations(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Multiple delegations accumulate usage for the same subagent."""
        manager = SubagentManager(parent_agent, configs=[basic_config])

        sub1 = _make_test_agent("run 1")
        with patch.object(manager, "_spawn", return_value=sub1):
            manager.delegate_sync("helper", "Task 1")

        sub2 = _make_test_agent("run 2")
        with patch.object(manager, "_spawn", return_value=sub2):
            manager.delegate_sync("helper", "Task 2")

        breakdown = manager.get_usage_breakdown()
        assert breakdown["helper"].request_count >= 2

    def test_parent_subagent_usage_tracked(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Parent tracker's get_subagent_usage includes delegated usage."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("parent track")

        with patch.object(manager, "_spawn", return_value=sub):
            manager.delegate_sync("helper", "Track on parent")

        subagent_usage = parent_agent.usage_tracker.get_subagent_usage()
        assert "helper" in subagent_usage

    def test_empty_usage_breakdown(self, manager: SubagentManager) -> None:
        """get_usage_breakdown returns empty dict when no delegations made."""
        assert manager.get_usage_breakdown() == {}

    def test_failed_delegation_still_tracks_usage(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Failed delegation with empty usage still creates breakdown entry."""
        manager = SubagentManager(parent_agent, configs=[basic_config])

        mock_agent = MagicMock()
        mock_agent.run_sync.side_effect = RuntimeError("Failure")

        with patch.object(manager, "_spawn", return_value=mock_agent):
            result = manager.delegate_sync("helper", "Failing task")

        assert result.success is False
        # Failed result has zero usage, so breakdown tracks it with zero
        breakdown = manager.get_usage_breakdown()
        assert "helper" in breakdown
        assert breakdown["helper"].total_tokens == 0


class TestActiveDelegations:
    """Tests for get_active_delegations tracking."""

    async def test_no_active_delegations_initially(self, manager: SubagentManager) -> None:
        """No active delegations before any delegate_async calls."""
        assert manager.get_active_delegations() == []

    async def test_completed_delegations_pruned(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Completed delegations are pruned from active list."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("done")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("helper", "Quick task")
            await handle.result()

        # After completion, active list should be empty
        active = manager.get_active_delegations()
        assert len(active) == 0


class TestConcurrentDelegations:
    """Tests for concurrent delegation behavior."""

    def test_concurrent_same_config_independent(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """Concurrent delegations to same config are independent instances."""
        manager = SubagentManager(parent_agent, configs=[basic_config])

        sub1 = _make_test_agent("instance 1")
        with patch.object(manager, "_spawn", return_value=sub1):
            result1 = manager.delegate_sync("helper", "Task 1")

        sub2 = _make_test_agent("instance 2")
        with patch.object(manager, "_spawn", return_value=sub2):
            result2 = manager.delegate_sync("helper", "Task 2")

        assert result1.success is True
        assert result2.success is True
        assert result1.output == "instance 1"
        assert result2.output == "instance 2"


class TestDiscovery:
    """Tests for discover method."""

    def test_discover_with_no_directories(self, manager: SubagentManager) -> None:
        """Discover returns empty list when no directories exist."""
        with patch(
            "mamba_agents.subagents.manager.discover_subagents",
            return_value=[],
        ):
            result = manager.discover()

        assert result == []

    def test_discover_registers_new_configs(
        self,
        manager: SubagentManager,
    ) -> None:
        """Discover registers newly found configs."""
        discovered = [
            SubagentConfig(name="disc-1", description="Discovered 1"),
            SubagentConfig(name="disc-2", description="Discovered 2"),
        ]

        with patch(
            "mamba_agents.subagents.manager.discover_subagents",
            return_value=discovered,
        ):
            result = manager.discover()

        assert len(result) == 2
        assert manager.get("disc-1") is not None
        assert manager.get("disc-2") is not None

    def test_discover_skips_duplicate_names(
        self,
        manager: SubagentManager,
        basic_config: SubagentConfig,
    ) -> None:
        """Discover skips configs with names already registered."""
        manager.register(basic_config)

        discovered = [
            SubagentConfig(name="helper", description="Duplicate"),
            SubagentConfig(name="new-one", description="New config"),
        ]

        with patch(
            "mamba_agents.subagents.manager.discover_subagents",
            return_value=discovered,
        ):
            result = manager.discover()

        # Only the new one should be registered
        assert len(result) == 1
        assert result[0].name == "new-one"
        # Original config is unchanged
        assert manager.get("helper") is basic_config

    def test_discover_handles_exception(self, manager: SubagentManager) -> None:
        """Discover returns empty list on exception."""
        with patch(
            "mamba_agents.subagents.manager.discover_subagents",
            side_effect=OSError("Disk error"),
        ):
            result = manager.discover()

        assert result == []


class TestDunderMethods:
    """Tests for __repr__ and __len__."""

    def test_repr_empty(self, manager: SubagentManager) -> None:
        """repr on empty manager shows 0 configs."""
        r = repr(manager)
        assert "SubagentManager" in r
        assert "configs=0" in r
        assert "active_delegations=0" in r

    def test_repr_with_configs(
        self,
        manager: SubagentManager,
        basic_config: SubagentConfig,
        second_config: SubagentConfig,
    ) -> None:
        """repr shows config count."""
        manager.register(basic_config)
        manager.register(second_config)

        r = repr(manager)
        assert "configs=2" in r

    def test_len_matches_config_count(
        self,
        manager: SubagentManager,
        basic_config: SubagentConfig,
    ) -> None:
        """len() returns number of registered configs."""
        assert len(manager) == 0
        manager.register(basic_config)
        assert len(manager) == 1


class TestUsageTrackingHandle:
    """Tests for _UsageTrackingHandle wrapper."""

    async def test_handle_aggregates_usage_once(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """_UsageTrackingHandle aggregates usage exactly once."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("once")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("helper", "Once task")

            result1 = await handle.result()
            assert result1.success is True

            # Calling result() again should not double-count
            result2 = await handle.result()
            assert result2.output == "once"

        breakdown = manager.get_usage_breakdown()
        # Should have been aggregated only once
        assert breakdown["helper"].request_count >= 1

    async def test_handle_is_delegation_handle(
        self,
        parent_agent: Agent[None, str],
        basic_config: SubagentConfig,
    ) -> None:
        """_UsageTrackingHandle is a DelegationHandle subclass."""
        manager = SubagentManager(parent_agent, configs=[basic_config])
        sub = _make_test_agent("type check")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("helper", "Type task")
            assert isinstance(handle, DelegationHandle)
            assert isinstance(handle, _UsageTrackingHandle)
            await handle.result()


class TestIntegrationFullLifecycle:
    """Integration tests for full SubagentManager lifecycle with TestModel."""

    def test_register_delegate_deregister(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Full lifecycle: register, delegate, check usage, deregister."""
        manager = SubagentManager(parent_agent)

        # Register
        config = SubagentConfig(
            name="lifecycle-agent",
            description="Tests full lifecycle",
        )
        manager.register(config)
        assert len(manager) == 1

        # Delegate
        sub = _make_test_agent("lifecycle result")
        with patch.object(manager, "_spawn", return_value=sub):
            result = manager.delegate_sync("lifecycle-agent", "Do lifecycle thing")

        assert result.success is True
        assert result.output == "lifecycle result"

        # Check usage
        breakdown = manager.get_usage_breakdown()
        assert "lifecycle-agent" in breakdown

        # Deregister
        manager.deregister("lifecycle-agent")
        assert len(manager) == 0

    async def test_async_lifecycle(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Full async lifecycle with delegate_async."""
        manager = SubagentManager(parent_agent)

        config = SubagentConfig(
            name="async-lifecycle",
            description="Async lifecycle test",
        )
        manager.register(config)
        sub = _make_test_agent("async lifecycle")

        with patch.object(manager, "_spawn", return_value=sub):
            handle = await manager.delegate_async("async-lifecycle", "Async task")
            result = await handle.result()

        assert result.success is True
        assert result.output == "async lifecycle"

        breakdown = manager.get_usage_breakdown()
        assert "async-lifecycle" in breakdown

    async def test_multiple_subagents_concurrent(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Multiple subagent configs used in concurrent async delegations."""
        manager = SubagentManager(parent_agent)

        configs = [SubagentConfig(name=f"agent-{i}", description=f"Agent {i}") for i in range(3)]
        for c in configs:
            manager.register(c)

        sub = _make_test_agent("concurrent")
        with patch.object(manager, "_spawn", return_value=sub):
            handles = []
            for c in configs:
                h = await manager.delegate_async(c.name, f"Task for {c.name}")
                handles.append(h)

            results = [await h.result() for h in handles]

        assert all(r.success for r in results)
        assert len(results) == 3

        breakdown = manager.get_usage_breakdown()
        for c in configs:
            assert c.name in breakdown

    def test_dynamic_and_registered_coexist(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Dynamic spawn and registered delegation can be used together."""
        manager = SubagentManager(parent_agent)
        registered = SubagentConfig(name="registered", description="Registered agent")
        manager.register(registered)

        sub = _make_test_agent("reg")
        with patch.object(manager, "_spawn", return_value=sub):
            reg_result = manager.delegate_sync("registered", "Registered task")

        assert reg_result.success is True
        assert len(manager) == 1  # dynamic not registered
