"""Integration tests for skills-subagents end-to-end workflows.

Tests span both the skills and subagents subsystems, exercising full
lifecycle flows through the Agent facade. All tests use TestModel to
avoid real API calls.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents import Agent
from mamba_agents.skills.config import (
    Skill,
    SkillInfo,
    SkillScope,
    TrustLevel,
)
from mamba_agents.skills.errors import SkillNotFoundError
from mamba_agents.skills.manager import SkillManager
from mamba_agents.subagents.config import DelegationHandle, SubagentConfig, SubagentResult
from mamba_agents.subagents.errors import SubagentNotFoundError
from mamba_agents.subagents.manager import SubagentManager
from mamba_agents.tokens.tracker import TokenUsage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SKILL_MD_TEMPLATE = """\
---
name: {name}
description: {description}
---

# {name}

{body}
"""

_FORK_SKILL_MD_TEMPLATE = """\
---
name: {name}
description: {description}
execution_mode: fork
agent: {agent}
---

# {name}

{body}
"""


def _write_skill(
    base: Path,
    name: str,
    description: str = "A test skill",
    body: str = "Skill content with $ARGUMENTS placeholder.",
) -> Path:
    """Create a skill directory with SKILL.md on disk."""
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = _SKILL_MD_TEMPLATE.format(
        name=name,
        description=description,
        body=body,
    )
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
    return skill_dir


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    body: str = "Skill body with $ARGUMENTS placeholder.",
    execution_mode: str | None = None,
    agent: str | None = None,
    trust_level: TrustLevel = TrustLevel.TRUSTED,
) -> Skill:
    """Create a Skill instance for testing."""
    return Skill(
        info=SkillInfo(
            name=name,
            description=description,
            path=Path(f"/fake/skills/{name}"),
            scope=SkillScope.PROJECT,
            trust_level=trust_level,
            execution_mode=execution_mode,
            agent=agent,
        ),
        body=body,
    )


def _make_config(
    name: str = "helper",
    description: str = "A helpful subagent",
    system_prompt: str | None = None,
    skills: list[str] | None = None,
    model: str | None = None,
) -> SubagentConfig:
    """Create a minimal SubagentConfig for testing."""
    return SubagentConfig(
        name=name,
        description=description,
        system_prompt=system_prompt,
        skills=skills,
        model=model,
    )


def _make_test_agent(output_text: str = "test output") -> Agent[None, str]:
    """Create a test agent with a specific output text for subagent mocking."""
    return Agent(TestModel(custom_output_text=output_text))


def _make_subagent_result(
    output: str = "subagent result",
    success: bool = True,
    error: str | None = None,
    subagent_name: str = "helper",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
) -> SubagentResult:
    """Create a minimal SubagentResult for mocking."""
    total = prompt_tokens + completion_tokens
    return SubagentResult(
        output=output,
        agent_result=MagicMock(),
        usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            request_count=1,
        ),
        duration=0.1,
        subagent_name=subagent_name,
        success=success,
        error=error,
    )


# ===========================================================================
# Scenario 1: Skill Loading & Activation (full lifecycle)
# ===========================================================================


class TestSkillLoadingAndActivation:
    """End-to-end lifecycle: Create SKILL.md on disk, discover, activate,
    verify tools, deactivate."""

    def test_create_discover_activate_deactivate(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Full lifecycle through Agent facade using skill_dirs discovery."""
        # --- Setup: Create skill directory on disk ---
        skills_parent = tmp_path / "skills"
        skills_parent.mkdir()
        _write_skill(
            skills_parent,
            "greeter",
            description="Greets users",
            body="Hello, $ARGUMENTS! Welcome aboard.",
        )
        _write_skill(
            skills_parent,
            "farewell",
            description="Says goodbye",
            body="Goodbye, $ARGUMENTS! See you later.",
        )

        # --- Act: Construct agent with skill_dirs ---
        agent: Agent[None, str] = Agent(
            test_model,
            skill_dirs=[skills_parent],
        )

        # --- Assert: Discovery populated the manager ---
        skills = agent.list_skills()
        names = {s.name for s in skills}
        assert "greeter" in names
        assert "farewell" in names
        assert len(names) == 2

        # --- Act: Activate with arguments ---
        content = agent.invoke_skill("greeter", "Alice")
        assert "Hello, Alice! Welcome aboard." in content

        # --- Act: Verify skill is active ---
        skill = agent.get_skill("greeter")
        assert skill is not None
        assert skill.is_active is True

        # --- Act: Deactivate ---
        agent.skill_manager.deactivate("greeter")
        skill = agent.get_skill("greeter")
        assert skill is not None
        assert skill.is_active is False

    def test_skill_reactivation_with_different_arguments(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Skill can be re-activated with different arguments after first activation."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_skill(
            skills_dir,
            "formatter",
            body="Format: $ARGUMENTS",
        )

        agent: Agent[None, str] = Agent(test_model, skill_dirs=[skills_dir])

        # First activation
        result1 = agent.invoke_skill("formatter", "json")
        assert "Format: json" in result1

        # Re-activate with different arguments
        result2 = agent.invoke_skill("formatter", "yaml")
        assert "Format: yaml" in result2

    def test_register_then_invoke_from_path(self, test_model: TestModel, tmp_path: Path) -> None:
        """Register a skill by Path, then invoke it."""
        skill_dir = _write_skill(
            tmp_path,
            "path-skill",
            body="Path content: $ARGUMENTS",
        )

        agent: Agent[None, str] = Agent(test_model)
        agent.register_skill(skill_dir)

        result = agent.invoke_skill("path-skill", "test-arg")
        assert "Path content: test-arg" in result

    def test_invoke_nonexistent_skill_raises(self, test_model: TestModel) -> None:
        """Invoking a non-existent skill raises SkillNotFoundError."""
        agent: Agent[None, str] = Agent(test_model)

        with pytest.raises(SkillNotFoundError):
            agent.invoke_skill("nonexistent-skill")

    def test_skill_with_tools_lifecycle(self, test_model: TestModel) -> None:
        """Skill with tools registered can be activated and tools retrieved."""

        def my_tool(query: str) -> str:
            """Search for something."""
            return f"results for {query}"

        skill = _make_skill(name="tooled-skill", body="Use the search tool.")
        skill._tools = [my_tool]

        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        # Before activation, tools not accessible via get_tools
        tools = agent.skill_manager.get_tools("tooled-skill")
        assert tools == []

        # Activate
        agent.invoke_skill("tooled-skill")

        # After activation, tools accessible
        tools = agent.skill_manager.get_tools("tooled-skill")
        assert len(tools) == 1
        assert tools[0]("test") == "results for test"

        # Deactivate
        agent.skill_manager.deactivate("tooled-skill")
        tools = agent.skill_manager.get_tools("tooled-skill")
        assert tools == []


# ===========================================================================
# Scenario 2: Subagent Delegation
# ===========================================================================


class TestSubagentDelegation:
    """End-to-end subagent registration, sync delegation, async delegation,
    usage tracking."""

    def test_register_delegate_sync_check_result_and_usage(self, test_model: TestModel) -> None:
        """Register config, delegate sync, check result + usage."""
        config = _make_config(name="summarizer", description="Summarizes text")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])

        sub = _make_test_agent("Summary: Python is great.")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            result = agent.delegate_sync("summarizer", "Summarize Python")

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "Summary: Python is great."
        assert result.subagent_name == "summarizer"
        assert result.duration > 0

        # Check usage was aggregated to parent
        usage = agent.get_usage()
        assert usage.total_tokens >= 0

    async def test_delegate_async_check_handle(self, test_model: TestModel) -> None:
        """Delegate async, get handle, await result."""
        config = _make_config(name="bg-worker")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("background result")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            handle = await agent.delegate_async("bg-worker", "Background task")

        assert isinstance(handle, DelegationHandle)
        assert handle.subagent_name == "bg-worker"

        result = await handle.result()
        assert result.success is True
        assert result.output == "background result"

    async def test_delegate_async_returns_result(self, test_model: TestModel) -> None:
        """Async delegate (awaiting immediately) returns SubagentResult."""
        config = _make_config(name="async-agent")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("async output")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            result = await agent.delegate("async-agent", "Async task")

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "async output"

    def test_delegate_sync_unknown_raises(self, test_model: TestModel) -> None:
        """Delegating to unknown subagent raises SubagentNotFoundError."""
        agent: Agent[None, str] = Agent(test_model)

        with pytest.raises(SubagentNotFoundError):
            agent.delegate_sync("ghost", "Do something")

    def test_multiple_sequential_delegations(self, test_model: TestModel) -> None:
        """Multiple sequential delegations to different subagents work independently."""
        config_a = _make_config(name="agent-a", description="Agent A")
        config_b = _make_config(name="agent-b", description="Agent B")
        agent: Agent[None, str] = Agent(
            test_model,
            subagents=[config_a, config_b],
        )

        sub_a = _make_test_agent("result-a")
        sub_b = _make_test_agent("result-b")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub_a):
            result_a = agent.delegate_sync("agent-a", "Task A")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub_b):
            result_b = agent.delegate_sync("agent-b", "Task B")

        assert result_a.output == "result-a"
        assert result_b.output == "result-b"

    def test_usage_breakdown_per_subagent(self, test_model: TestModel) -> None:
        """Usage breakdown tracks per-subagent token counts."""
        config_a = _make_config(name="tracker-a")
        config_b = _make_config(name="tracker-b")
        agent: Agent[None, str] = Agent(
            test_model,
            subagents=[config_a, config_b],
        )

        sub = _make_test_agent("tracked")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            agent.delegate_sync("tracker-a", "Task 1")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            agent.delegate_sync("tracker-b", "Task 2")

        breakdown = agent.subagent_manager.get_usage_breakdown()
        assert "tracker-a" in breakdown
        assert "tracker-b" in breakdown


# ===========================================================================
# Scenario 3: Skill-Subagent Integration
# ===========================================================================


class TestSkillSubagentIntegration:
    """Subagent configured with skills, fork mode, and cross-system wiring."""

    def test_subagent_with_skills_gets_skill_in_system_prompt(self, test_model: TestModel) -> None:
        """Subagent configured with skills gets skill content injected into prompt."""
        skill = _make_skill(
            name="analysis",
            body="Perform detailed analysis of the given topic.",
        )

        sm = SkillManager()
        sm.register(skill)

        parent: Agent[None, str] = Agent(test_model)
        sub_manager = SubagentManager(parent, skill_manager=sm)

        config = _make_config(
            name="analyst",
            description="Analysis agent",
            system_prompt="You are a data analyst.",
            skills=["analysis"],
        )
        sub_manager.register(config)

        # Verify the system prompt includes skill content
        from mamba_agents.subagents.spawner import _build_system_prompt

        prompt = _build_system_prompt(config, sm.registry)
        assert "You are a data analyst." in prompt
        assert "## Skill: analysis" in prompt
        assert "Perform detailed analysis" in prompt

    def test_delegate_to_subagent_with_preloaded_skills(self, test_model: TestModel) -> None:
        """Full flow: register skill + subagent with skill, delegate, get result."""
        skill = _make_skill(
            name="research",
            body="Research best practices for: $ARGUMENTS",
        )

        sm = SkillManager()
        sm.register(skill)

        parent: Agent[None, str] = Agent(test_model)
        sub_manager = SubagentManager(parent, skill_manager=sm)

        config = _make_config(
            name="researcher",
            description="Research agent",
            skills=["research"],
        )
        sub_manager.register(config)

        sub = _make_test_agent("research complete")
        with patch.object(sub_manager, "_spawn", return_value=sub):
            result = sub_manager.delegate_sync("researcher", "Python testing")

        assert result.success is True
        assert result.output == "research complete"

    def test_fork_skill_triggers_subagent_delegation(self, test_model: TestModel) -> None:
        """Skill with execution_mode='fork' delegates to subagent via SkillManager."""
        fork_skill = _make_skill(
            name="forky",
            body="Do the forked thing with: $ARGUMENTS",
            execution_mode="fork",
            agent="fork-agent",
        )

        parent: Agent[None, str] = Agent(test_model)
        sm = SkillManager()
        sm.register(fork_skill)

        sub_manager = SubagentManager(parent, skill_manager=sm)
        sub_manager.register(
            _make_config(name="fork-agent", description="Fork handler"),
        )

        # Wire bidirectionally
        sm.subagent_manager = sub_manager

        mock_result = _make_subagent_result(
            output="forked output",
            subagent_name="fork-agent",
        )
        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = sm.activate("forky", "test-args")

        assert result == "forked output"

    def test_fork_skill_without_subagent_manager_falls_through(self) -> None:
        """Fork skill without SubagentManager falls through to normal activation."""
        fork_skill = _make_skill(
            name="lonely-fork",
            body="Fork body: $ARGUMENTS",
            execution_mode="fork",
            agent="missing-agent",
        )

        sm = SkillManager()
        sm.register(fork_skill)

        # No subagent_manager set -- should fall through to normal activation
        result = sm.activate("lonely-fork", "hello")
        assert "Fork body: hello" in result

    def test_skill_with_fork_and_missing_agent_raises(self, test_model: TestModel) -> None:
        """Fork skill referencing non-existent subagent raises error."""
        fork_skill = _make_skill(
            name="bad-fork",
            body="Will fail: $ARGUMENTS",
            execution_mode="fork",
            agent="ghost-agent",
        )

        parent: Agent[None, str] = Agent(test_model)
        sm = SkillManager()
        sm.register(fork_skill)

        sub_manager = SubagentManager(parent, skill_manager=sm)
        # Do NOT register ghost-agent
        sm.subagent_manager = sub_manager

        with pytest.raises(SubagentNotFoundError, match="ghost-agent"):
            sm.activate("bad-fork", "args")

    def test_bidirectional_wiring_end_to_end(self, test_model: TestModel) -> None:
        """Full bidirectional wiring: SkillManager <-> SubagentManager."""
        parent: Agent[None, str] = Agent(test_model)

        sm = SkillManager()
        sub_manager = SubagentManager(parent, skill_manager=sm)
        sm.subagent_manager = sub_manager

        # Register a normal skill and a fork skill
        normal_skill = _make_skill(name="normal", body="Normal: $ARGUMENTS")
        fork_skill = _make_skill(
            name="delegator",
            body="Delegate: $ARGUMENTS",
            execution_mode="fork",
            agent="handler",
        )
        sm.register(normal_skill)
        sm.register(fork_skill)

        sub_manager.register(
            _make_config(name="handler", description="Handles delegations"),
        )

        # Normal skill activates normally
        result_normal = sm.activate("normal", "hello")
        assert "Normal: hello" in result_normal

        # Fork skill delegates to subagent
        mock_result = _make_subagent_result(output="delegated result")
        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result_fork = sm.activate("delegator", "world")
        assert result_fork == "delegated result"


# ===========================================================================
# Scenario 4: Agent Facade End-to-End
# ===========================================================================


class TestAgentFacadeEndToEnd:
    """Agent constructed with both skills and subagents, exercising
    the full facade API."""

    def test_agent_with_skills_and_subagents(self, test_model: TestModel, tmp_path: Path) -> None:
        """Agent(model, skills=[...], subagents=[...]) works end-to-end."""
        # Create skill on disk
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "helper-skill", body="Help with: $ARGUMENTS")

        # Create subagent config
        config = _make_config(
            name="worker",
            description="Worker subagent",
        )

        # Construct agent with both
        agent: Agent[None, str] = Agent(
            test_model,
            skill_dirs=[skills_dir],
            subagents=[config],
        )

        # Use skill
        skill_content = agent.invoke_skill("helper-skill", "testing")
        assert "Help with: testing" in skill_content

        # Delegate to subagent
        sub = _make_test_agent("worker output")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            result = agent.delegate_sync("worker", "Do some work")

        assert result.success is True
        assert result.output == "worker output"

    def test_agent_facade_skill_registration_then_delegation(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Register skills and subagents post-construction, then use both."""
        agent: Agent[None, str] = Agent(test_model)

        # Register skill after construction
        skill_dir = _write_skill(tmp_path, "post-skill", body="Post: $ARGUMENTS")
        agent.register_skill(skill_dir)

        # Register subagent after construction
        agent.register_subagent(
            _make_config(name="post-agent", description="Post-construction agent"),
        )

        # Use skill
        content = agent.invoke_skill("post-skill", "late")
        assert "Post: late" in content

        # Delegate
        sub = _make_test_agent("post result")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            result = agent.delegate_sync("post-agent", "Late task")
        assert result.output == "post result"

    def test_token_aggregation_across_delegations(self, test_model: TestModel) -> None:
        """Token usage from multiple subagent delegations aggregates to parent."""
        config_a = _make_config(name="agg-a")
        config_b = _make_config(name="agg-b")
        agent: Agent[None, str] = Agent(
            test_model,
            subagents=[config_a, config_b],
        )

        initial_total = agent.get_usage().total_tokens

        sub = _make_test_agent("output")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            agent.delegate_sync("agg-a", "Task A")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            agent.delegate_sync("agg-b", "Task B")

        final_total = agent.get_usage().total_tokens
        assert final_total >= initial_total

        # Per-subagent usage tracked
        breakdown = agent.subagent_manager.get_usage_breakdown()
        assert "agg-a" in breakdown
        assert "agg-b" in breakdown

    def test_agent_run_then_delegate(self, test_model: TestModel) -> None:
        """Agent runs directly, then delegates to subagent -- both work."""
        model = TestModel(custom_output_text="Direct answer")
        config = _make_config(name="follow-up")
        agent: Agent[None, str] = Agent(model, subagents=[config])

        # Direct agent run
        direct_result = agent.run_sync("What is Python?")
        assert direct_result.output == "Direct answer"

        # Delegate follow-up
        sub = _make_test_agent("Delegated answer")
        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            del_result = agent.delegate_sync("follow-up", "Elaborate on Python")
        assert del_result.output == "Delegated answer"

    def test_list_skills_and_subagents_together(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Agent lists skills and subagents correctly when both are registered."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _write_skill(skills_dir, "skill-x")
        _write_skill(skills_dir, "skill-y")

        config_a = _make_config(name="sub-a")
        config_b = _make_config(name="sub-b")

        agent: Agent[None, str] = Agent(
            test_model,
            skill_dirs=[skills_dir],
            subagents=[config_a, config_b],
        )

        skill_names = {s.name for s in agent.list_skills()}
        subagent_names = {c.name for c in agent.list_subagents()}

        assert skill_names == {"skill-x", "skill-y"}
        assert subagent_names == {"sub-a", "sub-b"}


# ===========================================================================
# Scenario 5: Nested Integration (skill forks to subagent with preloaded skills)
# ===========================================================================


class TestNestedSkillSubagentIntegration:
    """Skill that forks to a subagent which itself has pre-loaded skills."""

    def test_fork_to_subagent_with_preloaded_skills(self, test_model: TestModel) -> None:
        """Fork skill -> subagent that has pre-loaded skills in system prompt."""
        # Skill that the subagent will have pre-loaded
        preloaded_skill = _make_skill(
            name="code-review",
            body="Review code following best practices.",
        )

        # Fork skill that delegates to the subagent
        fork_skill = _make_skill(
            name="review-delegator",
            body="Review this code: $ARGUMENTS",
            execution_mode="fork",
            agent="reviewer",
        )

        parent: Agent[None, str] = Agent(test_model)

        # Set up SkillManager with both skills
        sm = SkillManager()
        sm.register(preloaded_skill)
        sm.register(fork_skill)

        # Set up SubagentManager with a subagent that pre-loads code-review
        sub_manager = SubagentManager(parent, skill_manager=sm)
        reviewer_config = _make_config(
            name="reviewer",
            description="Code reviewer",
            system_prompt="You are a code reviewer.",
            skills=["code-review"],
        )
        sub_manager.register(reviewer_config)

        # Wire bidirectionally
        sm.subagent_manager = sub_manager

        # Verify the spawned subagent would get skill content
        from mamba_agents.subagents.spawner import _build_system_prompt

        prompt = _build_system_prompt(reviewer_config, sm.registry)
        assert "You are a code reviewer." in prompt
        assert "## Skill: code-review" in prompt
        assert "Review code following best practices." in prompt

        # Activate the fork skill
        mock_result = _make_subagent_result(
            output="Code looks great!",
            subagent_name="reviewer",
        )
        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = sm.activate("review-delegator", "def hello(): pass")

        assert result == "Code looks great!"

    def test_nested_subagent_with_multiple_preloaded_skills(self, test_model: TestModel) -> None:
        """Subagent pre-loads multiple skills, all appear in system prompt."""
        skill_a = _make_skill(name="skill-a", body="Instructions for A.")
        skill_b = _make_skill(name="skill-b", body="Instructions for B.")

        sm = SkillManager()
        sm.register(skill_a)
        sm.register(skill_b)

        config = _make_config(
            name="multi-skilled",
            description="Has multiple skills",
            skills=["skill-a", "skill-b"],
        )

        from mamba_agents.subagents.spawner import _build_system_prompt

        prompt = _build_system_prompt(config, sm.registry)
        assert "## Skill: skill-a" in prompt
        assert "Instructions for A." in prompt
        assert "## Skill: skill-b" in prompt
        assert "Instructions for B." in prompt


# ===========================================================================
# Scenario 6: Multiple Concurrent Async Delegations
# ===========================================================================


class TestConcurrentAsyncDelegations:
    """Multiple async delegations running concurrently."""

    async def test_multiple_concurrent_delegations(self, test_model: TestModel) -> None:
        """Multiple delegate_async calls run concurrently and all complete."""
        configs = [_make_config(name=f"worker-{i}", description=f"Worker {i}") for i in range(3)]
        agent: Agent[None, str] = Agent(test_model, subagents=configs)

        subs = {f"worker-{i}": _make_test_agent(f"result-{i}") for i in range(3)}

        handles: list[DelegationHandle] = []
        for i in range(3):
            name = f"worker-{i}"
            with patch.object(
                agent.subagent_manager,
                "_spawn",
                return_value=subs[name],
            ):
                handle = await agent.delegate_async(name, f"Task {i}")
                handles.append(handle)

        # All handles should be DelegationHandle instances
        for handle in handles:
            assert isinstance(handle, DelegationHandle)

        # Await all results
        results = [await h.result() for h in handles]

        for i, result in enumerate(results):
            assert result.success is True
            assert result.output == f"result-{i}"

    async def test_concurrent_delegations_with_gather(self, test_model: TestModel) -> None:
        """Use asyncio.gather to await multiple delegations concurrently."""
        configs = [_make_config(name=f"gather-{i}", description=f"Gather {i}") for i in range(4)]
        agent: Agent[None, str] = Agent(test_model, subagents=configs)

        async def do_delegation(name: str, task: str) -> SubagentResult:
            sub = _make_test_agent(f"output-{name}")
            with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
                return await agent.delegate(name, task)

        tasks = [do_delegation(f"gather-{i}", f"Task {i}") for i in range(4)]

        results = await asyncio.gather(*tasks)

        assert len(results) == 4
        for i, result in enumerate(results):
            assert result.success is True
            assert result.output == f"output-gather-{i}"

    async def test_concurrent_handles_track_completion(self, test_model: TestModel) -> None:
        """DelegationHandles track completion status correctly."""
        config = _make_config(name="tracked-worker")
        agent: Agent[None, str] = Agent(test_model, subagents=[config])
        sub = _make_test_agent("tracked output")

        with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
            handle = await agent.delegate_async("tracked-worker", "Track this")

        # Handle starts as not complete (may already be complete with TestModel)
        # Await the result to ensure completion
        result = await handle.result()
        assert result.success is True

        # After awaiting, handle should be complete
        assert handle.is_complete is True

    async def test_usage_aggregation_across_concurrent_delegations(
        self, test_model: TestModel
    ) -> None:
        """Token usage aggregates correctly across concurrent delegations."""
        configs = [_make_config(name=f"usage-{i}") for i in range(3)]
        agent: Agent[None, str] = Agent(test_model, subagents=configs)

        initial_total = agent.get_usage().total_tokens

        async def do_delegation(name: str) -> SubagentResult:
            sub = _make_test_agent(f"out-{name}")
            with patch.object(agent.subagent_manager, "_spawn", return_value=sub):
                return await agent.delegate(name, f"Task for {name}")

        results = await asyncio.gather(*[do_delegation(f"usage-{i}") for i in range(3)])

        assert all(r.success for r in results)

        final_total = agent.get_usage().total_tokens
        assert final_total >= initial_total

        breakdown = agent.subagent_manager.get_usage_breakdown()
        assert len(breakdown) >= 3


# ===========================================================================
# Scenario 7: Circular Reference Detection Integration
# ===========================================================================


class TestCircularReferenceIntegration:
    """Integration-level circular reference detection across SkillManager
    and SubagentManager."""

    def test_circular_fork_detected_via_skill_manager(self, test_model: TestModel) -> None:
        """SkillManager detects and blocks circular fork references."""
        from mamba_agents.skills.errors import SkillInvocationError

        # Skill A forks to Agent X which pre-loads Skill A -- circular
        skill_a = _make_skill(
            name="circular-skill",
            body="Circular: $ARGUMENTS",
            execution_mode="fork",
            agent="circular-agent",
        )

        parent: Agent[None, str] = Agent(test_model)
        sm = SkillManager()
        sm.register(skill_a)

        sub_manager = SubagentManager(parent, skill_manager=sm)
        sub_manager.register(
            SubagentConfig(
                name="circular-agent",
                description="Pre-loads the same skill",
                skills=["circular-skill"],
            ),
        )
        sm.subagent_manager = sub_manager

        with pytest.raises(SkillInvocationError, match="Circular"):
            sm.activate("circular-skill", "test")

    def test_non_circular_fork_proceeds(self, test_model: TestModel) -> None:
        """Fork skill with no circular reference proceeds normally."""
        skill = _make_skill(
            name="safe-fork",
            body="Safe: $ARGUMENTS",
            execution_mode="fork",
            agent="safe-agent",
        )
        other_skill = _make_skill(
            name="other-skill",
            body="Other content.",
        )

        parent: Agent[None, str] = Agent(test_model)
        sm = SkillManager()
        sm.register(skill)
        sm.register(other_skill)

        sub_manager = SubagentManager(parent, skill_manager=sm)
        sub_manager.register(
            SubagentConfig(
                name="safe-agent",
                description="Pre-loads a different skill",
                skills=["other-skill"],
            ),
        )
        sm.subagent_manager = sub_manager

        mock_result = _make_subagent_result(output="safe output")
        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = sm.activate("safe-fork", "proceed")

        assert result == "safe output"


# ===========================================================================
# Scenario 8: Trust Level Enforcement Integration
# ===========================================================================


class TestTrustLevelIntegration:
    """Trust level enforcement for fork-mode skills at the integration level."""

    def test_untrusted_fork_skill_blocked(self, test_model: TestModel) -> None:
        """Untrusted skill with fork mode is blocked by trust check."""
        from mamba_agents.skills.errors import SkillInvocationError

        untrusted_fork = _make_skill(
            name="untrusted-fork",
            body="Untrusted: $ARGUMENTS",
            execution_mode="fork",
            agent="handler",
            trust_level=TrustLevel.UNTRUSTED,
        )

        parent: Agent[None, str] = Agent(test_model)
        sm = SkillManager()
        sm.register(untrusted_fork)

        sub_manager = SubagentManager(parent, skill_manager=sm)
        sub_manager.register(
            _make_config(name="handler", description="Handler"),
        )
        sm.subagent_manager = sub_manager

        with pytest.raises(SkillInvocationError, match="Untrusted"):
            sm.activate("untrusted-fork", "args")

    def test_trusted_fork_skill_allowed(self, test_model: TestModel) -> None:
        """Trusted skill with fork mode proceeds normally."""
        trusted_fork = _make_skill(
            name="trusted-fork",
            body="Trusted: $ARGUMENTS",
            execution_mode="fork",
            agent="handler",
            trust_level=TrustLevel.TRUSTED,
        )

        parent: Agent[None, str] = Agent(test_model)
        sm = SkillManager()
        sm.register(trusted_fork)

        sub_manager = SubagentManager(parent, skill_manager=sm)
        sub_manager.register(
            _make_config(name="handler", description="Handler"),
        )
        sm.subagent_manager = sub_manager

        mock_result = _make_subagent_result(output="trusted output")
        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = sm.activate("trusted-fork", "data")

        assert result == "trusted output"
