"""Regression tests for resolved fragility points.

Each test validates that a specific fragility point documented in the codebase
analysis has been resolved and prevents regressions. Tests are named with the
``test_regression_`` prefix so they can be run in isolation via
``pytest -k regression``.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.core import Agent
from mamba_agents.skills.config import Skill, SkillInfo, SkillScope, TrustLevel
from mamba_agents.skills.integration import activate_with_fork
from mamba_agents.skills.manager import SkillManager
from mamba_agents.skills.registry import SkillRegistry
from mamba_agents.subagents.config import SubagentConfig, SubagentResult
from mamba_agents.subagents.manager import SubagentManager
from mamba_agents.tokens.tracker import TokenUsage, UsageTracker
from mamba_agents.workflows.react.config import ReActConfig
from mamba_agents.workflows.react.workflow import ReActWorkflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(
    name: str = "test-skill",
    body: str = "# Test Skill\n\nContent for: $ARGUMENTS",
    execution_mode: str | None = None,
    agent: str | None = None,
    trust_level: TrustLevel = TrustLevel.TRUSTED,
) -> Skill:
    """Create a Skill instance for testing."""
    return Skill(
        info=SkillInfo(
            name=name,
            description=f"Test skill: {name}",
            path=Path(f"/fake/skills/{name}"),
            scope=SkillScope.PROJECT,
            execution_mode=execution_mode,
            agent=agent,
            trust_level=trust_level,
        ),
        body=body,
    )


def _make_subagent_result(
    output: str = "subagent output",
    success: bool = True,
) -> SubagentResult:
    """Create a SubagentResult for mocking."""
    return SubagentResult(
        output=output,
        agent_result=MagicMock(),
        usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, request_count=1),
        duration=0.1,
        subagent_name="test-sub",
        success=success,
    )


# ---------------------------------------------------------------------------
# Regression 1: Skills invocable during agent.run()
# ---------------------------------------------------------------------------


class TestRegressionSkillsInvocableDuringAgentRun:
    """Fragility: Skills were not wired into agent.run().

    The fix registers an ``invoke_skill`` pydantic-ai tool at the end of
    ``init_skills()`` when skills are present. TestModel with
    ``call_tools='all'`` automatically calls the tool during ``run()``.
    """

    async def test_regression_skills_invocable_during_agent_run(
        self, tmp_path: Path
    ) -> None:
        """Agent.run() can invoke registered skills via the invoke_skill tool."""
        # Create a skill directory with a valid SKILL.md
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: A test skill\n---\n\n"
            "# My Skill\n\nSkill output for: $ARGUMENTS\n",
            encoding="utf-8",
        )

        # Create agent with TestModel that calls all tools
        model = TestModel(call_tools="all")
        agent: Agent[None, str] = Agent(model, skills=[skill_dir])

        # Verify invoke_skill tool is registered
        tool_names = set(agent._agent._function_toolset.tools.keys())
        assert "invoke_skill" in tool_names, (
            "invoke_skill tool must be registered after init_skills() with skills"
        )

        # Run the agent -- TestModel will call invoke_skill
        result = await agent.run("Use my skill")

        # The invoke_skill tool was called and the agent completed
        assert result is not None
        assert result.output is not None


# ---------------------------------------------------------------------------
# Regression 2: Fork mode in async context
# ---------------------------------------------------------------------------


class TestRegressionForkModeAsyncContext:
    """Fragility: activate_with_fork() used ThreadPoolExecutor + asyncio.run().

    The fix makes ``activate_with_fork()`` a native ``async def`` that uses
    ``await subagent_manager.delegate()`` directly, avoiding deadlocks in
    async contexts (FastAPI, ASGI, nested event loops).
    """

    async def test_regression_fork_mode_in_async_context(self) -> None:
        """activate_with_fork works inside a running event loop without deadlock."""
        model = TestModel()
        parent_agent: Agent[None, str] = Agent(model)

        sub_manager = SubagentManager(parent_agent)
        sub_manager.register(
            SubagentConfig(name="helper", description="Helper agent")
        )

        fork_skill = _make_skill(
            name="fork-skill",
            execution_mode="fork",
            agent="helper",
            body="Forked task: $ARGUMENTS",
        )

        mock_result = _make_subagent_result(output="forked output")

        # We are already inside a running event loop (pytest-asyncio).
        # The old implementation with ThreadPoolExecutor + asyncio.run()
        # would deadlock here. The new async-native implementation works.
        with patch.object(
            sub_manager, "delegate", new_callable=AsyncMock, return_value=mock_result
        ):
            result = await activate_with_fork(
                fork_skill,
                "test args",
                sub_manager,
            )

        assert result == "forked output"


# ---------------------------------------------------------------------------
# Regression 3: No lazy init side effects
# ---------------------------------------------------------------------------


class TestRegressionNoLazyInitSideEffects:
    """Fragility: Accessing agent.skill_manager created the manager on first access.

    The fix uses explicit ``init_skills()``/``init_subagents()`` methods. The
    ``skill_manager`` and ``subagent_manager`` properties now raise
    ``AttributeError`` if not initialized, and ``has_skill_manager`` /
    ``has_subagent_manager`` return False without triggering initialization.
    """

    def test_regression_no_lazy_init_side_effects_skills(self) -> None:
        """Accessing has_skill_manager does not create SkillManager."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model)

        # has_skill_manager should be False without triggering init
        assert agent.has_skill_manager is False

        # Accessing skill_manager property should raise AttributeError
        with pytest.raises(AttributeError, match="SkillManager has not been initialized"):
            _ = agent.skill_manager

        # After the failed access, still no manager created
        assert agent._skill_manager is None

    def test_regression_no_lazy_init_side_effects_subagents(self) -> None:
        """Accessing has_subagent_manager does not create SubagentManager."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model)

        # has_subagent_manager should be False without triggering init
        assert agent.has_subagent_manager is False

        # Accessing subagent_manager property should raise AttributeError
        with pytest.raises(AttributeError, match="SubagentManager has not been initialized"):
            _ = agent.subagent_manager

        # After the failed access, still no manager created
        assert agent._subagent_manager is None


# ---------------------------------------------------------------------------
# Regression 4: UsageTracker public API for subagent usage
# ---------------------------------------------------------------------------


class TestRegressionUsageTrackerPublicAPI:
    """Fragility: SubagentManager mutated parent UsageTracker._subagent_totals directly.

    The fix adds ``record_subagent_usage(name, usage)`` as the public API
    on ``UsageTracker``. External callers should use this method rather
    than directly accessing the private ``_subagent_totals`` dict.
    """

    def test_regression_usage_tracker_public_api(self) -> None:
        """record_subagent_usage aggregates usage via public API."""
        tracker = UsageTracker()

        # Record subagent usage via the public API
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            request_count=3,
        )
        tracker.record_subagent_usage("my-subagent", usage)

        # Verify via get_subagent_usage (public getter)
        breakdown = tracker.get_subagent_usage()
        assert "my-subagent" in breakdown
        assert breakdown["my-subagent"].prompt_tokens == 100
        assert breakdown["my-subagent"].completion_tokens == 50
        assert breakdown["my-subagent"].total_tokens == 150
        assert breakdown["my-subagent"].request_count == 3

        # Verify it also updates the aggregate totals
        total = tracker.get_total_usage()
        assert total.prompt_tokens == 100
        assert total.completion_tokens == 50
        assert total.total_tokens == 150
        assert total.request_count == 3

    def test_regression_usage_tracker_public_api_accumulates(self) -> None:
        """Multiple calls to record_subagent_usage accumulate correctly."""
        tracker = UsageTracker()

        usage1 = TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15, request_count=1)
        usage2 = TokenUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30, request_count=2)

        tracker.record_subagent_usage("sub-a", usage1)
        tracker.record_subagent_usage("sub-a", usage2)

        breakdown = tracker.get_subagent_usage()
        assert breakdown["sub-a"].prompt_tokens == 30
        assert breakdown["sub-a"].total_tokens == 45
        assert breakdown["sub-a"].request_count == 3


# ---------------------------------------------------------------------------
# Regression 5: No circular initialization between SkillManager & SubagentManager
# ---------------------------------------------------------------------------


class TestRegressionNoCircularInitialization:
    """Fragility: SkillManager and SubagentManager referenced each other.

    The fix removes the bidirectional reference. SkillManager no longer has
    a ``subagent_manager`` property. SubagentManager accepts an optional
    ``SkillRegistry`` (not SkillManager) for skill pre-loading. The
    integration module mediates between the two without coupling.
    """

    def test_regression_no_circular_init_skill_manager_first(self) -> None:
        """SkillManager can be created without SubagentManager."""
        sm = SkillManager()
        assert sm is not None
        assert len(sm) == 0

        # SkillManager should not have a subagent_manager attribute
        assert not hasattr(sm, "subagent_manager")

    def test_regression_no_circular_init_subagent_manager_first(self) -> None:
        """SubagentManager can be created without SkillManager."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model)

        sub_manager = SubagentManager(parent_agent=agent, skill_registry=None)
        assert sub_manager is not None
        assert len(sub_manager) == 0

    def test_regression_no_circular_init_both_orders(self) -> None:
        """Both managers can be created in either order without errors."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model)

        # Order 1: SkillManager first, then SubagentManager with its registry
        sm1 = SkillManager()
        sub1 = SubagentManager(parent_agent=agent, skill_registry=sm1.registry)
        assert sm1 is not None
        assert sub1 is not None

        # Order 2: SubagentManager first (no registry), then SkillManager
        sub2 = SubagentManager(parent_agent=agent, skill_registry=None)
        sm2 = SkillManager()
        assert sub2 is not None
        assert sm2 is not None

    def test_regression_agent_init_skills_then_subagents(self) -> None:
        """Agent.init_skills() then init_subagents() works."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model)

        agent.init_skills(skills=[])
        agent.init_subagents(subagents=[])

        assert agent.has_skill_manager is True
        assert agent.has_subagent_manager is True

    def test_regression_agent_init_subagents_then_skills(self) -> None:
        """Agent.init_subagents() then init_skills() works."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model)

        agent.init_subagents(subagents=[])
        agent.init_skills(skills=[])

        assert agent.has_subagent_manager is True
        assert agent.has_skill_manager is True


# ---------------------------------------------------------------------------
# Regression 6: ReAct tool cleanup
# ---------------------------------------------------------------------------


class TestRegressionReActToolCleanup:
    """Fragility: ReActWorkflow permanently registered final_answer tool on agent.

    The fix moves tool registration from ``__init__()`` to ``run()``, using
    ``_save_tool_state()`` / ``_restore_tool_state()`` in a try/finally block
    to ensure the agent's tool set is restored after workflow completion.
    """

    async def test_regression_react_tool_cleanup(self) -> None:
        """Tool count is unchanged after ReActWorkflow.run() completes."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model)

        tool_names_before = set(agent._agent._function_toolset.tools.keys())
        tool_count_before = len(tool_names_before)

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))

        # ReActWorkflow.__init__ should NOT register final_answer
        tool_names_after_init = set(agent._agent._function_toolset.tools.keys())
        assert tool_names_after_init == tool_names_before, (
            "ReActWorkflow.__init__() must not register tools on the agent"
        )

        # Run the workflow
        result = await workflow.run("Test task")
        assert result.success is True

        # After run: tools must be exactly as before
        tool_names_after_run = set(agent._agent._function_toolset.tools.keys())
        assert tool_names_after_run == tool_names_before, (
            "ReActWorkflow.run() must restore the agent's tool set after completion"
        )
        assert len(tool_names_after_run) == tool_count_before
        assert "final_answer" not in tool_names_after_run

    async def test_regression_react_tool_cleanup_on_failure(self) -> None:
        """Tool state is restored even when workflow run fails."""
        model = TestModel()
        agent: Agent[None, str] = Agent(model, config=AgentConfig(track_context=False))

        tool_names_before = set(agent._agent._function_toolset.tools.keys())

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))

        with patch.object(
            workflow, "_execute", new_callable=AsyncMock, side_effect=RuntimeError("boom")
        ):
            result = await workflow.run("Test task")

        assert result.success is False

        tool_names_after = set(agent._agent._function_toolset.tools.keys())
        assert tool_names_after == tool_names_before, (
            "Tool state must be restored even on workflow failure"
        )
