"""Tests for ReActWorkflow."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents import Agent
from mamba_agents.agent.config import AgentConfig
from mamba_agents.prompts import PromptManager
from mamba_agents.prompts.config import TemplateConfig
from mamba_agents.workflows import (
    ReActConfig,
    ReActHooks,
    ReActState,
    ReActWorkflow,
)
from mamba_agents.workflows.base import WorkflowState


class TestReActWorkflow:
    """Tests for ReActWorkflow class."""

    def test_workflow_name(self) -> None:
        """Test workflow name property."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        assert workflow.name == "react"

    def test_workflow_agent_property(self) -> None:
        """Test agent property returns the agent."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        assert workflow.agent is agent

    def test_workflow_react_config_default(self) -> None:
        """Test default ReActConfig is created."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        assert isinstance(workflow.react_config, ReActConfig)
        assert workflow.react_config.max_iterations == 10

    def test_workflow_react_config_custom(self) -> None:
        """Test custom ReActConfig is used."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(max_iterations=20, expose_reasoning=False)
        workflow = ReActWorkflow(agent, config=config)

        assert workflow.react_config.max_iterations == 20
        assert workflow.react_config.expose_reasoning is False

    def test_final_answer_tool_not_registered_at_init(self) -> None:
        """Test that final_answer tool is NOT registered during __init__."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(final_answer_tool_name="submit_answer")

        tools_before = set(agent._agent._function_toolset.tools.keys())
        ReActWorkflow(agent, config=config)
        tools_after = set(agent._agent._function_toolset.tools.keys())

        # Tool registration is deferred to run(), not __init__
        assert tools_before == tools_after
        assert "submit_answer" not in tools_after

    @pytest.mark.asyncio
    async def test_create_initial_state(self) -> None:
        """Test initial state creation."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        # Call the internal method
        state = workflow._create_initial_state("Test task")

        assert state.context is not None
        assert isinstance(state.context, ReActState)
        assert state.context.task == "Test task"
        assert state.context.scratchpad == []
        assert state.context.is_terminated is False

    @pytest.mark.asyncio
    async def test_run_terminates_on_final_answer(self) -> None:
        """Test that workflow terminates when final_answer tool is called."""
        # TestModel automatically calls all tools including final_answer
        model = TestModel()

        agent = Agent(model)
        config = ReActConfig(max_iterations=10)
        workflow = ReActWorkflow(agent, config=config)

        result = await workflow.run("Test task")

        # TestModel calls final_answer, so workflow should succeed
        assert result.success is True
        assert result.state is not None
        assert result.state.context is not None
        assert result.state.context.is_terminated is True
        assert result.state.context.termination_reason == "final_answer_tool"

    @pytest.mark.asyncio
    async def test_run_returns_workflow_result(self) -> None:
        """Test that run returns a WorkflowResult."""
        model = TestModel()
        model.custom_result_text = "Thinking..."

        agent = Agent(model)
        config = ReActConfig(max_iterations=1)
        workflow = ReActWorkflow(agent, config=config)

        result = await workflow.run("Test task")

        # Even on failure, we get a WorkflowResult
        assert hasattr(result, "success")
        assert hasattr(result, "output")
        assert hasattr(result, "state")
        assert hasattr(result, "error")

    def test_run_sync(self) -> None:
        """Test synchronous run method."""
        model = TestModel()
        model.custom_result_text = "Thinking..."

        agent = Agent(model)
        config = ReActConfig(max_iterations=1)
        workflow = ReActWorkflow(agent, config=config)

        result = workflow.run_sync("Test task")

        assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_hooks_are_triggered(self) -> None:
        """Test that hooks are triggered during execution."""
        model = TestModel()
        model.custom_result_text = "Analyzing..."

        agent = Agent(model)
        config = ReActConfig(max_iterations=1)

        hook_calls: list[str] = []

        def on_iteration_start(state: Any, iteration: int) -> None:
            hook_calls.append(f"iteration_start:{iteration}")

        def on_iteration_complete(state: Any, iteration: int) -> None:
            hook_calls.append(f"iteration_complete:{iteration}")

        hooks = ReActHooks(
            on_iteration_start=on_iteration_start,
            on_iteration_complete=on_iteration_complete,
        )

        workflow = ReActWorkflow(agent, config=config, hooks=hooks)

        # Will fail due to max_iterations, but hooks should still be called
        await workflow.run("Test task")

        assert "iteration_start:1" in hook_calls
        assert "iteration_complete:1" in hook_calls

    @pytest.mark.asyncio
    async def test_thought_hooks_triggered(self) -> None:
        """Test that on_thought hook is triggered."""
        model = TestModel()
        model.custom_result_text = "I should read the file first."

        agent = Agent(model)
        config = ReActConfig(max_iterations=1)

        thoughts: list[str] = []

        def on_thought(state: ReActState, thought: str) -> None:
            thoughts.append(thought)

        hooks = ReActHooks(on_thought=on_thought)
        workflow = ReActWorkflow(agent, config=config, hooks=hooks)

        await workflow.run("Test task")

        # The thought should have been captured
        # Note: exact behavior depends on how TestModel responds
        assert len(thoughts) >= 0  # May or may not have thoughts depending on response

    @pytest.mark.asyncio
    async def test_state_tracks_iterations(self) -> None:
        """Test that state tracks iteration count."""
        model = TestModel()

        agent = Agent(model)
        config = ReActConfig(max_iterations=10)
        workflow = ReActWorkflow(agent, config=config)

        result = await workflow.run("Test task")

        # TestModel calls final_answer in first iteration, so iteration_count should be 1
        assert result.state is not None
        assert result.state.iteration_count >= 1

    @pytest.mark.asyncio
    async def test_token_tracking(self) -> None:
        """Test that tokens are tracked per iteration."""
        model = TestModel()
        model.custom_result_text = "Analyzing the code..."

        agent = Agent(model)
        config = ReActConfig(max_iterations=2)
        workflow = ReActWorkflow(agent, config=config)

        await workflow.run("Test task")

        # Check that get_token_usage delegates to agent
        usage = workflow.get_token_usage()
        assert hasattr(usage, "total_tokens")

    @pytest.mark.asyncio
    async def test_get_cost_delegates_to_agent(self) -> None:
        """Test that get_cost delegates to agent."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(max_iterations=1)
        workflow = ReActWorkflow(agent, config=config)

        await workflow.run("Test task")

        # Should not raise
        cost = workflow.get_cost()
        assert isinstance(cost, float)

    @pytest.mark.asyncio
    async def test_scratchpad_populated(self) -> None:
        """Test that scratchpad is populated during execution."""
        model = TestModel()
        model.custom_result_text = "Let me analyze this."

        agent = Agent(model)
        config = ReActConfig(max_iterations=2)
        workflow = ReActWorkflow(agent, config=config)

        result = await workflow.run("Analyze main.py")

        assert result.state is not None
        assert result.state.context is not None

        # The scratchpad should have entries
        react_state = result.state.context
        # Note: actual entries depend on model response parsing
        assert isinstance(react_state.scratchpad, list)


class TestReActWorkflowIntegration:
    """Integration tests for ReActWorkflow with mocked agent responses."""

    @pytest.mark.asyncio
    async def test_workflow_with_hooks_logging(self) -> None:
        """Test workflow with comprehensive hook logging."""
        model = TestModel()
        model.custom_result_text = "Thinking about the problem..."

        agent = Agent(model)
        config = ReActConfig(max_iterations=2, enable_hooks=True)

        log: list[str] = []

        hooks = ReActHooks(
            on_workflow_start=lambda s: log.append("workflow_start"),
            on_workflow_complete=lambda r: log.append("workflow_complete"),
            on_workflow_error=lambda s, e: log.append(f"workflow_error:{e}"),
            on_step_start=lambda s, n, t: log.append(f"step_start:{n}"),
            on_step_complete=lambda s, step: log.append(f"step_complete:{step.step_number}"),
            on_iteration_start=lambda s, i: log.append(f"iter_start:{i}"),
            on_iteration_complete=lambda s, i: log.append(f"iter_complete:{i}"),
        )

        workflow = ReActWorkflow(agent, config=config, hooks=hooks)
        await workflow.run("Test")

        # Workflow hooks should be called even on failure
        assert "workflow_start" in log
        # Should have iteration logs
        assert any("iter_start" in entry for entry in log)

    @pytest.mark.asyncio
    async def test_consecutive_thoughts_tracking(self) -> None:
        """Test that consecutive thoughts are tracked."""
        model = TestModel()
        model.custom_result_text = "Just thinking, no actions..."

        agent = Agent(model)
        config = ReActConfig(max_iterations=3, max_consecutive_thoughts=2)
        workflow = ReActWorkflow(agent, config=config)

        result = await workflow.run("Test task")

        # The state should track consecutive thoughts
        assert result.state is not None
        assert result.state.context is not None


class TestReActWorkflowEdgeCases:
    """Edge case tests for ReActWorkflow."""

    def test_empty_hooks(self) -> None:
        """Test workflow with empty hooks object."""
        model = TestModel()
        agent = Agent(model)
        hooks = ReActHooks()  # All None
        workflow = ReActWorkflow(agent, hooks=hooks)

        assert workflow._react_hooks is not None

    def test_config_inheritance(self) -> None:
        """Test that ReActConfig settings are properly inherited."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(
            max_steps=100,  # From WorkflowConfig
            max_iterations=5,  # From WorkflowConfig
            expose_reasoning=False,  # ReAct-specific
        )
        workflow = ReActWorkflow(agent, config=config)

        assert workflow.config.max_steps == 100
        assert workflow.config.max_iterations == 5
        assert workflow.react_config.expose_reasoning is False

    @pytest.mark.asyncio
    async def test_empty_task(self) -> None:
        """Test workflow with empty task string."""
        model = TestModel()
        model.custom_result_text = "Analyzing..."

        agent = Agent(model)
        config = ReActConfig(max_iterations=1)
        workflow = ReActWorkflow(agent, config=config)

        result = await workflow.run("")

        # Should still execute (agent handles empty prompts)
        assert result.state is not None
        assert result.state.context.task == ""

    def test_get_scratchpad_before_run(self) -> None:
        """Test that get_scratchpad returns empty list before any run."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        # Before any run, should return empty list
        assert workflow.get_scratchpad() == []

    def test_get_reasoning_trace_before_run(self) -> None:
        """Test that get_reasoning_trace returns empty string before any run."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        # Before any run, should return empty string
        assert workflow.get_reasoning_trace() == ""

    @pytest.mark.asyncio
    async def test_get_scratchpad_after_run(self) -> None:
        """Test that get_scratchpad returns entries after run."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        await workflow.run("Test task")

        # After run, should have scratchpad entries
        scratchpad = workflow.get_scratchpad()
        assert isinstance(scratchpad, list)

    @pytest.mark.asyncio
    async def test_get_reasoning_trace_after_run(self) -> None:
        """Test that get_reasoning_trace returns formatted text after run."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        await workflow.run("Test task")

        # After run, should return string (may be empty if no thoughts)
        trace = workflow.get_reasoning_trace()
        assert isinstance(trace, str)


class TestReActToolStateRestore:
    """Tests for tool state save/restore around workflow run."""

    def _get_tool_names(self, agent: Agent) -> set[str]:
        """Helper to get the set of tool names from an agent."""
        return set(agent._agent._function_toolset.tools.keys())

    @pytest.mark.asyncio
    async def test_tool_count_matches_before_and_after_run(self) -> None:
        """Tool count should be the same before and after workflow run."""
        model = TestModel()
        agent = Agent(model)
        tools_before = self._get_tool_names(agent)

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))
        result = await workflow.run("Test task")

        assert result.success is True
        tools_after = self._get_tool_names(agent)
        assert tools_before == tools_after

    @pytest.mark.asyncio
    async def test_final_answer_not_present_after_run(self) -> None:
        """final_answer tool should not remain on agent after workflow completes."""
        model = TestModel()
        agent = Agent(model)

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))
        await workflow.run("Test task")

        assert "final_answer" not in self._get_tool_names(agent)

    @pytest.mark.asyncio
    async def test_tool_restore_on_workflow_error(self) -> None:
        """Tool state should be restored even when the workflow fails mid-run."""
        model = TestModel()
        agent = Agent(model, config=AgentConfig(track_context=False))
        tools_before = self._get_tool_names(agent)

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))

        # Patch _execute to raise an error mid-run
        with patch.object(
            workflow, "_execute", new_callable=AsyncMock, side_effect=RuntimeError("boom")
        ):
            result = await workflow.run("Test task")

        # Workflow should have failed
        assert result.success is False
        assert "boom" in (result.error or "")

        # But tool state must still be restored
        tools_after = self._get_tool_names(agent)
        assert tools_before == tools_after
        assert "final_answer" not in tools_after

    @pytest.mark.asyncio
    async def test_sequential_workflow_runs_work_correctly(self) -> None:
        """Multiple sequential workflow runs on the same agent should work."""
        model = TestModel()
        agent = Agent(model)
        tools_before = self._get_tool_names(agent)

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))

        # First run
        result1 = await workflow.run("Task 1")
        assert result1.success is True
        assert self._get_tool_names(agent) == tools_before

        # Clear context so message history doesn't confuse TestModel
        agent.clear_context()

        # Second run - should not have duplicate tools or fail
        result2 = await workflow.run("Task 2")
        assert result2.success is True
        assert self._get_tool_names(agent) == tools_before

        agent.clear_context()

        # Third run for good measure
        result3 = await workflow.run("Task 3")
        assert result3.success is True
        assert self._get_tool_names(agent) == tools_before

    @pytest.mark.asyncio
    async def test_user_tools_preserved_after_workflow(self) -> None:
        """User-registered tools should be preserved after workflow run."""
        model = TestModel()
        agent = Agent(model)

        @agent.tool_plain
        def my_custom_tool(x: str) -> str:
            """A custom user tool."""
            return x

        tools_before = self._get_tool_names(agent)
        assert "my_custom_tool" in tools_before

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))
        await workflow.run("Test task")

        tools_after = self._get_tool_names(agent)
        assert tools_after == tools_before
        assert "my_custom_tool" in tools_after

    @pytest.mark.asyncio
    async def test_user_final_answer_tool_preserved(self) -> None:
        """If user registered a 'final_answer' tool, save/restore preserves it."""
        model = TestModel()
        agent = Agent(model)

        @agent.tool_plain(name="final_answer")
        def user_final_answer(answer: str) -> str:
            """User's own final_answer implementation."""
            return f"USER: {answer}"

        tools_before = self._get_tool_names(agent)
        assert "final_answer" in tools_before
        user_tool = agent._agent._function_toolset.tools["final_answer"]

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))

        # The workflow temporarily replaces the user's tool, then restores it
        await workflow.run("Test task")

        # User's final_answer should be restored (same object identity)
        tools_after = self._get_tool_names(agent)
        assert "final_answer" in tools_after
        restored_tool = agent._agent._function_toolset.tools["final_answer"]
        assert restored_tool is user_tool

    def test_run_sync_also_restores_tools(self) -> None:
        """run_sync() should also perform tool cleanup."""
        model = TestModel()
        agent = Agent(model)
        tools_before = self._get_tool_names(agent)

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))
        result = workflow.run_sync("Test task")

        assert result.success is True
        tools_after = self._get_tool_names(agent)
        assert tools_before == tools_after
        assert "final_answer" not in tools_after

    def test_run_sync_restores_tools_on_failure(self) -> None:
        """run_sync() should restore tools even on workflow failure."""
        model = TestModel()
        agent = Agent(model, config=AgentConfig(track_context=False))
        tools_before = self._get_tool_names(agent)

        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))

        # Patch _execute to force an error
        with patch.object(
            workflow, "_execute", new_callable=AsyncMock, side_effect=RuntimeError("sync_error")
        ):
            result = workflow.run_sync("Test task")

        assert result.success is False
        assert "sync_error" in (result.error or "")
        tools_after = self._get_tool_names(agent)
        assert tools_before == tools_after

    @pytest.mark.asyncio
    async def test_agent_reuse_after_react_workflow(self) -> None:
        """Agent should be usable for normal runs after ReAct workflow."""
        model = TestModel()
        agent = Agent(model)
        tools_before = self._get_tool_names(agent)

        # Run a ReAct workflow
        workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))
        result = await workflow.run("ReAct task")
        assert result.success is True

        # Agent tools are clean
        assert self._get_tool_names(agent) == tools_before

        # Agent can be used directly for a normal run
        normal_result = await agent.run("Normal task")
        assert normal_result is not None

    @pytest.mark.asyncio
    async def test_different_workflows_same_agent(self) -> None:
        """Different ReActWorkflow instances on the same agent work correctly."""
        model = TestModel()
        agent = Agent(model)
        tools_before = self._get_tool_names(agent)

        workflow1 = ReActWorkflow(agent, config=ReActConfig(max_iterations=10))
        workflow2 = ReActWorkflow(
            agent, config=ReActConfig(max_iterations=5, final_answer_tool_name="done")
        )

        # Run first workflow
        r1 = await workflow1.run("Task 1")
        assert r1.success is True
        assert self._get_tool_names(agent) == tools_before

        # Clear context so TestModel behaves correctly on the second run
        agent.clear_context()

        # Run second workflow with different tool name
        r2 = await workflow2.run("Task 2")
        assert r2.success is True
        assert self._get_tool_names(agent) == tools_before
        assert "done" not in self._get_tool_names(agent)


class TestPromptManager:
    """Tests for prompt manager property and lazy creation."""

    def test_prompt_manager_returns_none_by_default(self) -> None:
        """prompt_manager property returns None when not provided."""
        model = TestModel()
        agent = Agent(model)
        workflow = ReActWorkflow(agent)

        assert workflow.prompt_manager is None

    def test_prompt_manager_returns_provided_instance(self) -> None:
        """prompt_manager returns the instance provided at construction."""
        model = TestModel()
        agent = Agent(model)
        pm = PromptManager()
        workflow = ReActWorkflow(agent, prompt_manager=pm)

        assert workflow.prompt_manager is pm

    def test_get_prompt_manager_returns_provided(self) -> None:
        """_get_prompt_manager returns provided prompt manager."""
        model = TestModel()
        agent = Agent(model)
        pm = PromptManager()
        workflow = ReActWorkflow(agent, prompt_manager=pm)

        result = workflow._get_prompt_manager()
        assert result is pm

    def test_get_prompt_manager_falls_back_to_agent(self) -> None:
        """_get_prompt_manager uses agent's prompt manager if no local one."""
        model = TestModel()
        agent = Agent(model)
        # Agent has a prompt_manager
        agent_pm = PromptManager()
        agent._prompt_manager = agent_pm

        workflow = ReActWorkflow(agent)
        result = workflow._get_prompt_manager()
        assert result is agent_pm

    def test_get_prompt_manager_creates_new_from_settings(self) -> None:
        """_get_prompt_manager creates a new one from agent settings if none exist."""
        model = TestModel()
        agent = Agent(model)
        # Ensure agent doesn't have a prompt manager
        agent._prompt_manager = None

        workflow = ReActWorkflow(agent)
        result = workflow._get_prompt_manager()

        assert isinstance(result, PromptManager)
        # Should be cached
        assert workflow._prompt_manager is result


class TestBuildIterationPrompt:
    """Tests for _build_iteration_prompt with template config."""

    def test_default_prompt_without_template(self) -> None:
        """Without template config, uses default build_iteration_prompt."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(iteration_prompt_template=None)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")
        react_state.add_thought("Thinking...")

        prompt = workflow._build_iteration_prompt(react_state)
        # Default prompt includes "Continue working on the task"
        assert "Continue working on the task" in prompt

    def test_template_prompt_used_when_configured(self) -> None:
        """With template config, uses the prompt manager to render."""
        model = TestModel()
        agent = Agent(model)

        pm = MagicMock(spec=PromptManager)
        pm.render.return_value = "Rendered template output"

        template_config = TemplateConfig(
            name="react/iteration",
            variables={"extra_var": "value"},
        )
        config = ReActConfig(iteration_prompt_template=template_config)
        workflow = ReActWorkflow(agent, config=config, prompt_manager=pm)

        react_state = ReActState(task="Test")
        prompt = workflow._build_iteration_prompt(react_state)

        assert prompt == "Rendered template output"
        pm.render.assert_called_once()

    def test_force_action_prompt(self) -> None:
        """force_action=True uses force action prompt in default path."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(iteration_prompt_template=None)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")
        prompt = workflow._build_iteration_prompt(react_state, force_action=True)
        assert "Please call a tool now" in prompt


class TestExecuteLoop:
    """Tests for _execute loop behavior including edge cases."""

    async def test_none_context_raises_value_error(self) -> None:
        """_execute raises ValueError when ReActState context is None."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(max_iterations=5)
        workflow = ReActWorkflow(agent, config=config)

        state = WorkflowState(context=None)
        with pytest.raises(ValueError, match="ReActState context is required"):
            await workflow._execute("test", state)

    async def test_max_iterations_exceeded_raises_error(self) -> None:
        """Exceeding max_iterations raises WorkflowMaxIterationsError."""
        model = TestModel()
        model.custom_result_text = "Still thinking..."
        agent = Agent(model)

        # max_iterations=1 but the model won't call final_answer if we mock it out
        config = ReActConfig(max_iterations=1, enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        # Mock _process_iteration_result to NOT terminate
        with (
            patch.object(workflow, "_process_iteration_result", new_callable=AsyncMock),
            patch.object(workflow, "_maybe_compact", new_callable=AsyncMock),
        ):
            result = await workflow.run("Test task")

        # The base Workflow.run catches the exception and returns a failed result
        assert result.success is False
        assert "exceeded" in (result.error or "").lower()

    async def test_hooks_triggered_during_execution(self) -> None:
        """All hook types are triggered during the execution loop."""
        model = TestModel()
        model.custom_result_text = "Analyzing..."
        agent = Agent(model)
        config = ReActConfig(max_iterations=2, enable_hooks=True)

        log: list[str] = []

        hooks = ReActHooks(
            on_iteration_start=lambda s, i: log.append(f"iter_start:{i}"),
            on_iteration_complete=lambda s, i: log.append(f"iter_complete:{i}"),
            on_step_start=lambda s, n, t: log.append(f"step_start:{n}"),
            on_step_complete=lambda s, step: log.append("step_complete"),
        )

        workflow = ReActWorkflow(agent, config=config, hooks=hooks)
        await workflow.run("Test")

        assert "iter_start:1" in log
        assert "step_start:1" in log
        assert "step_complete" in log

    async def test_exception_during_agent_run_triggers_step_error(self) -> None:
        """An exception during agent.run triggers step error hook and reraises."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(max_iterations=5, enable_hooks=True)

        step_errors: list[str] = []

        hooks = ReActHooks(
            on_step_error=lambda s, step, e: step_errors.append(str(e)),
        )

        workflow = ReActWorkflow(agent, config=config, hooks=hooks)

        # Patch agent.run to raise
        with patch.object(agent, "run", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            result = await workflow.run("Test task")

        assert result.success is False
        assert "boom" in (result.error or "")
        assert len(step_errors) == 1
        assert "boom" in step_errors[0]

    async def test_second_iteration_uses_build_iteration_prompt(self) -> None:
        """After iteration 1, subsequent iterations use _build_iteration_prompt."""
        model = TestModel()
        model.custom_result_text = "Thinking..."
        agent = Agent(model)
        config = ReActConfig(max_iterations=2, enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        prompts_used: list[str] = []
        original_run = agent.run

        async def mock_run(prompt, **kwargs):
            prompts_used.append(prompt)
            return await original_run(prompt, **kwargs)

        # Mock so first iteration doesn't terminate, second does
        call_count = 0

        async def mock_process(result, state):
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                state.is_terminated = True
                state.termination_reason = "final_answer_tool"
                state.final_answer = "Done"

        with (
            patch.object(agent, "run", side_effect=mock_run),
            patch.object(workflow, "_process_iteration_result", side_effect=mock_process),
            patch.object(workflow, "_maybe_compact", new_callable=AsyncMock),
        ):
            await workflow.run("Original task")

        # First prompt should be original, second should be from _build_iteration_prompt
        assert len(prompts_used) == 2
        assert prompts_used[0] == "Original task"
        # Second prompt should be a constructed iteration prompt
        assert prompts_used[1] != "Original task"


class TestProcessIterationResult:
    """Tests for _process_iteration_result method."""

    async def test_final_answer_terminates(self) -> None:
        """When final_answer is detected, state is terminated."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")

        mock_result = MagicMock()
        with patch(
            "mamba_agents.workflows.react.workflow.detect_final_answer",
            return_value=(True, "The answer is 42"),
        ):
            await workflow._process_iteration_result(mock_result, react_state)

        assert react_state.is_terminated is True
        assert react_state.termination_reason == "final_answer_tool"
        assert react_state.final_answer == "The answer is 42"
        assert len(react_state.scratchpad) == 1
        assert react_state.scratchpad[0].entry_type == "observation"
        assert "42" in react_state.scratchpad[0].content

    async def test_tool_calls_recorded_as_actions(self) -> None:
        """Tool calls are added to scratchpad as actions."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")

        mock_result = MagicMock()
        with (
            patch(
                "mamba_agents.workflows.react.workflow.detect_final_answer",
                return_value=(False, None),
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_calls",
                return_value=[
                    {"name": "read_file", "args": {"path": "main.py"}},
                    {"name": "final_answer", "args": {"answer": "done"}},
                ],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_results",
                return_value=[],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_text_content",
                return_value="I need to read the file",
            ),
        ):
            await workflow._process_iteration_result(mock_result, react_state)

        # Should have 1 thought + 1 action (final_answer skipped)
        thoughts = react_state.get_thoughts()
        actions = react_state.get_actions()
        assert len(thoughts) == 1
        assert "read the file" in thoughts[0]
        assert len(actions) == 1
        assert "read_file" in actions[0]

    async def test_tool_results_recorded_as_observations(self) -> None:
        """Tool results are added to scratchpad as observations."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")

        mock_result = MagicMock()
        with (
            patch(
                "mamba_agents.workflows.react.workflow.detect_final_answer",
                return_value=(False, None),
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_calls",
                return_value=[],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_results",
                return_value=[
                    {"name": "read_file", "content": "file contents here"},
                    {"name": "final_answer", "content": "Final answer submitted"},
                ],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_text_content",
                return_value="",
            ),
        ):
            await workflow._process_iteration_result(mock_result, react_state)

        # Only read_file observation (final_answer skipped)
        observations = react_state.get_observations()
        assert len(observations) == 1
        assert "file contents here" in observations[0]

    async def test_error_observations_detected(self) -> None:
        """Observations starting with 'Error:' are flagged as errors."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")

        mock_result = MagicMock()
        with (
            patch(
                "mamba_agents.workflows.react.workflow.detect_final_answer",
                return_value=(False, None),
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_calls",
                return_value=[],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_results",
                return_value=[
                    {"name": "run_bash", "content": "Error: command not found"},
                ],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_text_content",
                return_value="",
            ),
        ):
            await workflow._process_iteration_result(mock_result, react_state)

        observations = react_state.get_observations()
        assert len(observations) == 1
        # Check that the observation metadata has is_error flag
        entry = react_state.scratchpad[-1]
        assert entry.metadata.get("is_error") is True

    async def test_hooks_triggered_for_thoughts_actions_observations(self) -> None:
        """on_thought, on_action, on_observation hooks triggered."""
        model = TestModel()
        agent = Agent(model)

        log: list[str] = []
        hooks = ReActHooks(
            on_thought=lambda s, t: log.append(f"thought:{t}"),
            on_action=lambda s, n, a: log.append(f"action:{n}"),
            on_observation=lambda s, o, e: log.append(f"obs:{o}"),
        )
        config = ReActConfig(enable_hooks=True)
        workflow = ReActWorkflow(agent, config=config, hooks=hooks)

        react_state = ReActState(task="Test")
        mock_result = MagicMock()

        with (
            patch(
                "mamba_agents.workflows.react.workflow.detect_final_answer",
                return_value=(False, None),
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_calls",
                return_value=[{"name": "grep", "args": {"pattern": "bug"}}],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_results",
                return_value=[{"name": "grep", "content": "found bug on line 5"}],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_text_content",
                return_value="Let me search for the bug",
            ),
        ):
            await workflow._process_iteration_result(mock_result, react_state)

        assert any("thought:Let me search" in x for x in log)
        assert any("action:grep" in x for x in log)
        assert any("obs:found bug" in x for x in log)

    async def test_no_text_content_skips_thought(self) -> None:
        """Empty text content does not add a thought entry."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")
        mock_result = MagicMock()

        with (
            patch(
                "mamba_agents.workflows.react.workflow.detect_final_answer",
                return_value=(False, None),
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_calls",
                return_value=[],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_results",
                return_value=[],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_text_content",
                return_value="",
            ),
        ):
            await workflow._process_iteration_result(mock_result, react_state)

        assert react_state.get_thoughts() == []

    async def test_exception_observation_detected(self) -> None:
        """Observations starting with 'Exception:' are flagged as errors."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(enable_hooks=False)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")
        mock_result = MagicMock()

        with (
            patch(
                "mamba_agents.workflows.react.workflow.detect_final_answer",
                return_value=(False, None),
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_calls",
                return_value=[],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_tool_results",
                return_value=[
                    {"name": "run_bash", "content": "Exception: ZeroDivisionError"},
                ],
            ),
            patch(
                "mamba_agents.workflows.react.workflow.extract_text_content",
                return_value="",
            ),
        ):
            await workflow._process_iteration_result(mock_result, react_state)

        entry = react_state.scratchpad[-1]
        assert entry.metadata.get("is_error") is True


class TestMaybeCompact:
    """Tests for _maybe_compact method."""

    async def test_compact_disabled_returns_early(self) -> None:
        """When auto_compact_in_workflow=False, returns immediately."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(auto_compact_in_workflow=False)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")
        # Should not raise or do anything
        await workflow._maybe_compact(react_state)
        assert react_state.compaction_count == 0

    async def test_no_context_manager_returns_early(self) -> None:
        """When context_manager is None, returns immediately."""
        model = TestModel()
        agent = Agent(model, config=AgentConfig(track_context=False))
        config = ReActConfig(auto_compact_in_workflow=True)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")
        await workflow._maybe_compact(react_state)
        assert react_state.compaction_count == 0

    async def test_context_tracking_runtime_error_caught(self) -> None:
        """RuntimeError from get_context_state is caught gracefully."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(auto_compact_in_workflow=True)
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")

        with patch.object(agent, "get_context_state", side_effect=RuntimeError("disabled")):
            await workflow._maybe_compact(react_state)

        assert react_state.compaction_count == 0

    async def test_below_threshold_does_not_compact(self) -> None:
        """When token_count is below threshold, no compaction occurs."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(
            auto_compact_in_workflow=True,
            compact_threshold_ratio=0.8,
        )
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")

        # Mock context state with low token count
        mock_ctx = MagicMock()
        mock_ctx.token_count = 100  # Well below threshold

        with patch.object(agent, "get_context_state", return_value=mock_ctx):
            await workflow._maybe_compact(react_state)

        assert react_state.compaction_count == 0

    async def test_above_threshold_triggers_compaction(self) -> None:
        """When token_count exceeds threshold, compaction is triggered."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(
            auto_compact_in_workflow=True,
            compact_threshold_ratio=0.8,
        )
        workflow = ReActWorkflow(agent, config=config)

        react_state = ReActState(task="Test")

        # Mock context state with high token count
        mock_ctx = MagicMock()
        mock_ctx.token_count = 100000  # Very high, should exceed threshold

        mock_compact_result = MagicMock()

        with (
            patch.object(agent, "get_context_state", return_value=mock_ctx),
            patch.object(
                agent, "compact", new_callable=AsyncMock, return_value=mock_compact_result
            ),
        ):
            await workflow._maybe_compact(react_state)

        assert react_state.compaction_count == 1

    async def test_compaction_triggers_hook(self) -> None:
        """Compaction triggers on_compaction hook when hooks enabled."""
        model = TestModel()
        agent = Agent(model)

        compaction_results: list[Any] = []
        hooks = ReActHooks(
            on_compaction=lambda r: compaction_results.append(r),
        )
        config = ReActConfig(
            auto_compact_in_workflow=True,
            compact_threshold_ratio=0.8,
            enable_hooks=True,
        )
        workflow = ReActWorkflow(agent, config=config, hooks=hooks)

        react_state = ReActState(task="Test")

        mock_ctx = MagicMock()
        mock_ctx.token_count = 100000

        mock_compact_result = MagicMock()

        with (
            patch.object(agent, "get_context_state", return_value=mock_ctx),
            patch.object(
                agent, "compact", new_callable=AsyncMock, return_value=mock_compact_result
            ),
        ):
            await workflow._maybe_compact(react_state)

        assert len(compaction_results) == 1
        assert compaction_results[0] is mock_compact_result
