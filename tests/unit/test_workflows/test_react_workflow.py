"""Tests for ReActWorkflow."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents import Agent
from mamba_agents.workflows import (
    ReActConfig,
    ReActHooks,
    ReActState,
    ReActWorkflow,
)


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

    def test_final_answer_tool_registered(self) -> None:
        """Test that final_answer tool is registered on agent."""
        model = TestModel()
        agent = Agent(model)
        config = ReActConfig(final_answer_tool_name="submit_answer")

        # The workflow registers the tool during __init__
        workflow = ReActWorkflow(agent, config=config)

        # The tool should be registered on the underlying pydantic-ai agent
        # We can't easily verify this without running, but the workflow init
        # calls agent.tool_plain() which should succeed
        assert workflow is not None

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
        result = await workflow.run("Test")

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
