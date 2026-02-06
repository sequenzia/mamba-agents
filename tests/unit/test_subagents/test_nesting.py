"""Tests for no-nesting enforcement in the subagents subsystem.

Verifies that subagents cannot spawn sub-subagents, that the
``_is_subagent`` flag is correctly managed, and that
``SubagentNestingError`` provides clear diagnostics.
"""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.core import Agent
from mamba_agents.subagents.config import SubagentConfig
from mamba_agents.subagents.errors import SubagentError, SubagentNestingError
from mamba_agents.subagents.manager import SubagentManager
from mamba_agents.subagents.spawner import _enforce_no_nesting, spawn


@pytest.fixture
def parent_agent(test_model: TestModel) -> Agent[None, str]:
    """Create a normal (non-subagent) parent agent."""
    return Agent(test_model)


@pytest.fixture
def child_agent(parent_agent: Agent[None, str]) -> Agent[None, str]:
    """Spawn a subagent from the parent agent."""
    config = SubagentConfig(name="child", description="A child subagent")
    return spawn(config, parent_agent)


# ---------------------------------------------------------------------------
# _is_subagent flag behaviour
# ---------------------------------------------------------------------------


class TestIsSubagentFlag:
    """Tests for the ``_is_subagent`` PrivateAttr on AgentConfig."""

    def test_normal_agent_has_flag_false(self, parent_agent: Agent[None, str]) -> None:
        """Normal agents start with ``_is_subagent=False``."""
        assert parent_agent.config._is_subagent is False

    def test_spawned_subagent_has_flag_true(self, child_agent: Agent[None, str]) -> None:
        """Spawned subagents have ``_is_subagent=True``."""
        assert child_agent.config._is_subagent is True

    def test_flag_is_not_in_model_dump(self) -> None:
        """``_is_subagent`` is a PrivateAttr, invisible in ``model_dump()``."""
        config = AgentConfig()
        config._is_subagent = True

        dump = config.model_dump()

        assert "_is_subagent" not in dump

    def test_flag_default_is_false_on_fresh_config(self) -> None:
        """A freshly-created AgentConfig defaults to ``_is_subagent=False``."""
        config = AgentConfig()
        assert config._is_subagent is False

    def test_parent_flag_unchanged_after_spawn(self, parent_agent: Agent[None, str]) -> None:
        """Spawning a subagent does not modify the parent agent's flag."""
        config = SubagentConfig(name="test-child", description="Test child")
        spawn(config, parent_agent)

        assert parent_agent.config._is_subagent is False


# ---------------------------------------------------------------------------
# _enforce_no_nesting direct tests
# ---------------------------------------------------------------------------


class TestEnforceNoNesting:
    """Tests for the ``_enforce_no_nesting`` guard function."""

    def test_normal_agent_does_not_raise(self, parent_agent: Agent[None, str]) -> None:
        """Normal agents pass the nesting check without error."""
        _enforce_no_nesting(parent_agent)  # Should not raise

    def test_subagent_raises_nesting_error(self, child_agent: Agent[None, str]) -> None:
        """Subagents (``_is_subagent=True``) raise ``SubagentNestingError``."""
        with pytest.raises(SubagentNestingError):
            _enforce_no_nesting(child_agent)

    def test_nesting_error_includes_parent_name(self, child_agent: Agent[None, str]) -> None:
        """The error includes the parent name for debugging context."""
        with pytest.raises(SubagentNestingError) as exc_info:
            _enforce_no_nesting(child_agent)

        # parent_name is derived from the agent's model_name
        assert exc_info.value.parent_name is not None

    def test_nesting_error_includes_new_subagent_placeholder(
        self, child_agent: Agent[None, str]
    ) -> None:
        """The error uses ``<new-subagent>`` as the attempted subagent name."""
        with pytest.raises(SubagentNestingError) as exc_info:
            _enforce_no_nesting(child_agent)

        assert exc_info.value.name == "<new-subagent>"


# ---------------------------------------------------------------------------
# spawn() nesting rejection
# ---------------------------------------------------------------------------


class TestSpawnNestingRejection:
    """Tests for spawn() rejecting nesting attempts."""

    def test_subagent_cannot_spawn_sub_subagent(self, child_agent: Agent[None, str]) -> None:
        """Calling ``spawn()`` from a subagent raises ``SubagentNestingError``."""
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="Should be rejected",
        )

        with pytest.raises(SubagentNestingError):
            spawn(grandchild_config, child_agent)

    def test_error_is_subagent_nesting_error_type(self, child_agent: Agent[None, str]) -> None:
        """The raised exception is exactly ``SubagentNestingError``."""
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="Type check",
        )

        with pytest.raises(SubagentNestingError) as exc_info:
            spawn(grandchild_config, child_agent)

        # Verify it is the correct error class, not just SubagentError
        assert type(exc_info.value) is SubagentNestingError

    def test_nesting_error_is_subagent_error_subclass(self, child_agent: Agent[None, str]) -> None:
        """``SubagentNestingError`` is a subclass of ``SubagentError``."""
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="Inheritance check",
        )

        with pytest.raises(SubagentError):
            spawn(grandchild_config, child_agent)

    def test_nesting_error_message_is_clear(self, child_agent: Agent[None, str]) -> None:
        """Error message clearly explains the nesting violation."""
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="Clarity check",
        )

        with pytest.raises(SubagentNestingError, match="sub-subagent"):
            spawn(grandchild_config, child_agent)

    def test_nesting_error_mentions_nesting_not_allowed(
        self, child_agent: Agent[None, str]
    ) -> None:
        """Error message mentions that nesting is not allowed."""
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="Not allowed check",
        )

        with pytest.raises(SubagentNestingError, match=r"[Nn]esting is not allowed"):
            spawn(grandchild_config, child_agent)


# ---------------------------------------------------------------------------
# SubagentManager nesting enforcement
# ---------------------------------------------------------------------------


class TestManagerNestingEnforcement:
    """Tests for nesting enforcement via SubagentManager."""

    def test_manager_delegate_sync_from_subagent_raises(
        self, child_agent: Agent[None, str]
    ) -> None:
        """SubagentManager on a subagent raises nesting error on delegation."""
        manager = SubagentManager(child_agent)
        config = SubagentConfig(name="nested-sub", description="Should fail")
        manager.register(config)

        with pytest.raises(SubagentNestingError):
            manager.delegate_sync("nested-sub", "Do something")

    async def test_manager_delegate_async_from_subagent_raises(
        self, child_agent: Agent[None, str]
    ) -> None:
        """Async delegate from subagent-based manager raises nesting error."""
        manager = SubagentManager(child_agent)
        config = SubagentConfig(name="nested-async", description="Should fail")
        manager.register(config)

        with pytest.raises(SubagentNestingError):
            await manager.delegate("nested-async", "Do something async")

    async def test_manager_spawn_dynamic_from_subagent_raises(
        self, child_agent: Agent[None, str]
    ) -> None:
        """spawn_dynamic from subagent-based manager raises nesting error."""
        manager = SubagentManager(child_agent)
        dynamic_config = SubagentConfig(
            name="dynamic-nested",
            description="Dynamic nesting attempt",
        )

        with pytest.raises(SubagentNestingError):
            await manager.spawn_dynamic(dynamic_config, "Dynamic task")


# ---------------------------------------------------------------------------
# Multi-level nesting attempts
# ---------------------------------------------------------------------------


class TestMultiLevelNesting:
    """Tests verifying nesting is blocked regardless of how deep it could go."""

    def test_two_levels_deep_rejected(self, parent_agent: Agent[None, str]) -> None:
        """Level 1 -> Level 2 spawn is rejected."""
        child_config = SubagentConfig(name="level-1", description="Level 1")
        child = spawn(child_config, parent_agent)

        level2_config = SubagentConfig(name="level-2", description="Level 2")

        with pytest.raises(SubagentNestingError):
            spawn(level2_config, child)

    def test_nesting_check_happens_before_tool_resolution(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Nesting check is the first thing in spawn(), before tool resolution."""
        child_config = SubagentConfig(name="child", description="Child")
        child = spawn(child_config, parent_agent)

        # Even with tools that would otherwise succeed, nesting check blocks first
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="With tools",
            tools=["nonexistent_tool"],  # Would fail if nesting check didn't come first
        )

        with pytest.raises(SubagentNestingError):
            spawn(grandchild_config, child)

    def test_nesting_check_happens_before_prompt_building(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Nesting check blocks before system prompt building."""
        child_config = SubagentConfig(name="child", description="Child")
        child = spawn(child_config, parent_agent)

        # Even with skills that would fail, nesting check blocks first
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="With skills",
            skills=["nonexistent_skill"],  # Would fail if nesting check didn't come first
        )

        with pytest.raises(SubagentNestingError):
            spawn(grandchild_config, child)


# ---------------------------------------------------------------------------
# Error attributes and serialization
# ---------------------------------------------------------------------------


class TestNestingErrorAttributes:
    """Tests for SubagentNestingError attribute correctness."""

    def test_error_name_attribute(self, child_agent: Agent[None, str]) -> None:
        """Error ``name`` attribute is set to ``<new-subagent>``."""
        with pytest.raises(SubagentNestingError) as exc_info:
            _enforce_no_nesting(child_agent)

        assert exc_info.value.name == "<new-subagent>"

    def test_error_parent_name_from_model_name(self, child_agent: Agent[None, str]) -> None:
        """Error ``parent_name`` is derived from the agent's model name."""
        with pytest.raises(SubagentNestingError) as exc_info:
            _enforce_no_nesting(child_agent)

        # TestModel agents have a model_name (could be None -> "unknown")
        parent_name = exc_info.value.parent_name
        assert parent_name is not None
        assert isinstance(parent_name, str)

    def test_error_is_picklable(self) -> None:
        """SubagentNestingError supports pickle via ``__reduce__``."""
        import pickle

        err = SubagentNestingError(name="test-sub", parent_name="test-parent")
        restored = pickle.loads(pickle.dumps(err))

        assert restored.name == "test-sub"
        assert restored.parent_name == "test-parent"
        assert "sub-subagent" in str(restored)

    def test_error_repr_is_informative(self) -> None:
        """repr() includes name and parent_name."""
        err = SubagentNestingError(name="my-sub", parent_name="my-parent")

        r = repr(err)
        assert "SubagentNestingError" in r
        assert "my-sub" in r
        assert "my-parent" in r

    def test_error_str_describes_violation(self) -> None:
        """str() clearly describes the nesting violation."""
        err = SubagentNestingError(name="nested-sub", parent_name="parent-agent")

        msg = str(err)
        assert "nested-sub" in msg
        assert "parent-agent" in msg
        assert "sub-subagent" in msg
        assert "not allowed" in msg.lower()
