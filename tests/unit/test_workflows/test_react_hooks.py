"""Tests for ReActHooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from pydantic_agent.workflows import ReActHooks, ReActState, WorkflowHooks


class TestReActHooks:
    """Tests for ReActHooks class."""

    def test_inherits_from_workflow_hooks(self) -> None:
        """Test that ReActHooks inherits from WorkflowHooks."""
        assert issubclass(ReActHooks, WorkflowHooks)

    def test_default_hooks_are_none(self) -> None:
        """Test that all hooks default to None."""
        hooks = ReActHooks()

        # Inherited hooks
        assert hooks.on_workflow_start is None
        assert hooks.on_workflow_complete is None
        assert hooks.on_workflow_error is None
        assert hooks.on_step_start is None
        assert hooks.on_step_complete is None
        assert hooks.on_step_error is None
        assert hooks.on_iteration_start is None
        assert hooks.on_iteration_complete is None

        # ReAct-specific hooks
        assert hooks.on_thought is None
        assert hooks.on_action is None
        assert hooks.on_observation is None
        assert hooks.on_compaction is None

    def test_set_react_hooks(self) -> None:
        """Test setting ReAct-specific hooks."""
        thought_callback = lambda state, thought: None
        action_callback = lambda state, name, args: None
        observation_callback = lambda state, obs, is_error: None
        compaction_callback = lambda result: None

        hooks = ReActHooks(
            on_thought=thought_callback,
            on_action=action_callback,
            on_observation=observation_callback,
            on_compaction=compaction_callback,
        )

        assert hooks.on_thought is thought_callback
        assert hooks.on_action is action_callback
        assert hooks.on_observation is observation_callback
        assert hooks.on_compaction is compaction_callback

    def test_set_inherited_hooks(self) -> None:
        """Test setting inherited workflow hooks."""
        start_callback = lambda state: None
        complete_callback = lambda result: None

        hooks = ReActHooks(
            on_workflow_start=start_callback,
            on_workflow_complete=complete_callback,
        )

        assert hooks.on_workflow_start is start_callback
        assert hooks.on_workflow_complete is complete_callback

    @pytest.mark.asyncio
    async def test_trigger_thought_calls_hook(self) -> None:
        """Test that trigger_thought calls the on_thought hook."""
        called_with: list[tuple] = []

        def on_thought(state: ReActState, thought: str) -> None:
            called_with.append((state, thought))

        hooks = ReActHooks(on_thought=on_thought)
        state = ReActState(task="Test task")

        await hooks.trigger_thought(state, "I should check the file")

        assert len(called_with) == 1
        assert called_with[0][0] is state
        assert called_with[0][1] == "I should check the file"

    @pytest.mark.asyncio
    async def test_trigger_thought_no_op_when_none(self) -> None:
        """Test that trigger_thought is no-op when hook is None."""
        hooks = ReActHooks()
        state = ReActState(task="Test task")

        # Should not raise
        await hooks.trigger_thought(state, "Some thought")

    @pytest.mark.asyncio
    async def test_trigger_action_calls_hook(self) -> None:
        """Test that trigger_action calls the on_action hook."""
        called_with: list[tuple] = []

        def on_action(state: ReActState, name: str, args: dict) -> None:
            called_with.append((state, name, args))

        hooks = ReActHooks(on_action=on_action)
        state = ReActState(task="Test task")

        await hooks.trigger_action(state, "read_file", {"path": "main.py"})

        assert len(called_with) == 1
        assert called_with[0][0] is state
        assert called_with[0][1] == "read_file"
        assert called_with[0][2] == {"path": "main.py"}

    @pytest.mark.asyncio
    async def test_trigger_observation_calls_hook(self) -> None:
        """Test that trigger_observation calls the on_observation hook."""
        called_with: list[tuple] = []

        def on_observation(state: ReActState, obs: str, is_error: bool) -> None:
            called_with.append((state, obs, is_error))

        hooks = ReActHooks(on_observation=on_observation)
        state = ReActState(task="Test task")

        await hooks.trigger_observation(state, "File contents here", False)

        assert len(called_with) == 1
        assert called_with[0][0] is state
        assert called_with[0][1] == "File contents here"
        assert called_with[0][2] is False

    @pytest.mark.asyncio
    async def test_trigger_observation_with_error(self) -> None:
        """Test trigger_observation with error flag."""
        called_with: list[tuple] = []

        def on_observation(state: ReActState, obs: str, is_error: bool) -> None:
            called_with.append((state, obs, is_error))

        hooks = ReActHooks(on_observation=on_observation)
        state = ReActState(task="Test task")

        await hooks.trigger_observation(state, "Error: file not found", True)

        assert len(called_with) == 1
        assert called_with[0][2] is True

    @pytest.mark.asyncio
    async def test_trigger_compaction_calls_hook(self) -> None:
        """Test that trigger_compaction calls the on_compaction hook."""
        called_with: list[Any] = []

        def on_compaction(result: Any) -> None:
            called_with.append(result)

        hooks = ReActHooks(on_compaction=on_compaction)

        # Mock compaction result
        @dataclass
        class MockCompactionResult:
            tokens_before: int = 1000
            tokens_after: int = 500

        mock_result = MockCompactionResult()
        await hooks.trigger_compaction(mock_result)

        assert len(called_with) == 1
        assert called_with[0] is mock_result

    @pytest.mark.asyncio
    async def test_async_hooks_work(self) -> None:
        """Test that async hook functions work correctly."""
        called = []

        async def async_thought_hook(state: ReActState, thought: str) -> None:
            called.append(("thought", thought))

        async def async_action_hook(
            state: ReActState, name: str, args: dict
        ) -> None:
            called.append(("action", name))

        hooks = ReActHooks(
            on_thought=async_thought_hook,
            on_action=async_action_hook,
        )
        state = ReActState(task="Test task")

        await hooks.trigger_thought(state, "Thinking...")
        await hooks.trigger_action(state, "read_file", {})

        assert len(called) == 2
        assert called[0] == ("thought", "Thinking...")
        assert called[1] == ("action", "read_file")

    def test_combine_with_inherited_hooks(self) -> None:
        """Test creating hooks with both inherited and ReAct-specific."""
        inherited_call_count = {"start": 0}
        react_call_count = {"thought": 0}

        def on_workflow_start(state: Any) -> None:
            inherited_call_count["start"] += 1

        def on_thought(state: ReActState, thought: str) -> None:
            react_call_count["thought"] += 1

        hooks = ReActHooks(
            on_workflow_start=on_workflow_start,
            on_thought=on_thought,
        )

        assert hooks.on_workflow_start is not None
        assert hooks.on_thought is not None

        # Verify they're the correct functions
        assert hooks.on_workflow_start is on_workflow_start
        assert hooks.on_thought is on_thought
