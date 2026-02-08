"""Tests for subagent data models."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from mamba_agents.agent.config import AgentConfig
from mamba_agents.prompts.config import TemplateConfig
from mamba_agents.subagents.config import DelegationHandle, SubagentConfig, SubagentResult
from mamba_agents.tokens.tracker import TokenUsage


class TestSubagentConfig:
    """Tests for SubagentConfig model."""

    def test_minimal_construction(self) -> None:
        """Test construction with only required fields."""
        config = SubagentConfig(
            name="test-agent",
            description="Handles test tasks",
        )

        assert config.name == "test-agent"
        assert config.description == "Handles test tasks"
        assert config.model is None
        assert config.tools is None
        assert config.disallowed_tools is None
        assert config.system_prompt is None
        assert config.skills is None
        assert config.max_turns == 50
        assert config.config is None

    def test_all_optional_fields(self) -> None:
        """Test construction with all optional fields populated."""

        def dummy_tool() -> str:
            return "result"

        template = TemplateConfig(name="system/test")
        agent_config = AgentConfig(max_iterations=20)

        config = SubagentConfig(
            name="full-agent",
            description="Full configuration test",
            model="gpt-4o",
            tools=["read_file", "write_file", dummy_tool],
            disallowed_tools=["run_bash"],
            system_prompt=template,
            skills=["code-review", "testing"],
            max_turns=100,
            config=agent_config,
        )

        assert config.name == "full-agent"
        assert config.description == "Full configuration test"
        assert config.model == "gpt-4o"
        assert config.tools is not None
        assert len(config.tools) == 3
        assert config.tools[0] == "read_file"
        assert config.tools[1] == "write_file"
        assert config.tools[2] is dummy_tool
        assert config.disallowed_tools == ["run_bash"]
        assert isinstance(config.system_prompt, TemplateConfig)
        assert config.skills == ["code-review", "testing"]
        assert config.max_turns == 100
        assert config.config is not None
        assert config.config.max_iterations == 20

    def test_system_prompt_as_string(self) -> None:
        """Test that system_prompt accepts a plain string."""
        config = SubagentConfig(
            name="string-prompt",
            description="Uses string prompt",
            system_prompt="You are a helpful assistant.",
        )

        assert config.system_prompt == "You are a helpful assistant."

    def test_empty_tools_list_valid(self) -> None:
        """Test that empty tools list is valid (read-only subagent)."""
        config = SubagentConfig(
            name="readonly",
            description="Read-only subagent with no tools",
            tools=[],
        )

        assert config.tools == []

    def test_missing_name_raises_validation_error(self) -> None:
        """Test that missing name raises a pydantic validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SubagentConfig(description="No name provided")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

    def test_missing_description_raises_validation_error(self) -> None:
        """Test that missing description raises a pydantic validation error."""
        with pytest.raises(ValidationError) as exc_info:
            SubagentConfig(name="no-description")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("description",) for e in errors)

    def test_model_copy(self) -> None:
        """Test that config can be copied with modifications."""
        original = SubagentConfig(
            name="original",
            description="Original config",
        )
        modified = original.model_copy(update={"name": "modified"})

        assert original.name == "original"
        assert modified.name == "modified"
        assert modified.description == "Original config"


class TestSubagentResult:
    """Tests for SubagentResult dataclass."""

    def _make_result(self, **overrides: Any) -> SubagentResult:
        """Create a SubagentResult with sensible defaults."""
        mock_agent_result = MagicMock()
        mock_agent_result.output = "test output"

        defaults: dict[str, Any] = {
            "output": "Task completed successfully",
            "agent_result": mock_agent_result,
            "usage": TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            "duration": 2.5,
            "subagent_name": "test-agent",
            "success": True,
            "error": None,
        }
        defaults.update(overrides)
        return SubagentResult(**defaults)

    def test_successful_result(self) -> None:
        """Test construction of a successful result."""
        result = self._make_result()

        assert result.output == "Task completed successfully"
        assert result.usage.total_tokens == 150
        assert result.duration == 2.5
        assert result.subagent_name == "test-agent"
        assert result.success is True
        assert result.error is None

    def test_failed_result_with_error(self) -> None:
        """Test construction of a failed result with error message."""
        result = self._make_result(
            output="",
            success=False,
            error="Max turns exceeded",
        )

        assert result.success is False
        assert result.error == "Max turns exceeded"
        assert result.output == ""

    def test_result_stores_usage(self) -> None:
        """Test that result properly stores token usage."""
        usage = TokenUsage(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            request_count=3,
        )
        result = self._make_result(usage=usage)

        assert result.usage.prompt_tokens == 200
        assert result.usage.completion_tokens == 100
        assert result.usage.total_tokens == 300
        assert result.usage.request_count == 3

    def test_result_stores_agent_result(self) -> None:
        """Test that result properly stores the agent result wrapper."""
        mock_agent_result = MagicMock()
        mock_agent_result.output = "wrapped output"
        result = self._make_result(agent_result=mock_agent_result)

        assert result.agent_result.output == "wrapped output"


class TestDelegationHandle:
    """Tests for DelegationHandle dataclass."""

    def test_construction_without_task(self) -> None:
        """Test construction without an asyncio task."""
        handle = DelegationHandle(
            subagent_name="test-agent",
            task="Summarize the document",
        )

        assert handle.subagent_name == "test-agent"
        assert handle.task == "Summarize the document"
        assert handle._task is None

    def test_is_complete_without_task(self) -> None:
        """Test is_complete returns True when no task is assigned."""
        handle = DelegationHandle(
            subagent_name="test-agent",
            task="Some task",
        )

        assert handle.is_complete is True

    def test_is_complete_with_pending_task(self) -> None:
        """Test is_complete returns False for a pending task."""
        loop = asyncio.new_event_loop()
        try:
            future: asyncio.Future[SubagentResult] = loop.create_future()
            task = asyncio.ensure_future(future, loop=loop)

            handle = DelegationHandle(
                subagent_name="test-agent",
                task="Pending task",
                _task=task,
            )

            assert handle.is_complete is False

            # Clean up
            task.cancel()
        finally:
            loop.close()

    def test_is_complete_with_done_task(self) -> None:
        """Test is_complete returns True for a completed task."""
        loop = asyncio.new_event_loop()
        try:
            future: asyncio.Future[SubagentResult] = loop.create_future()
            mock_result = MagicMock(spec=SubagentResult)
            future.set_result(mock_result)
            task = asyncio.ensure_future(future, loop=loop)

            handle = DelegationHandle(
                subagent_name="test-agent",
                task="Done task",
                _task=task,
            )

            assert handle.is_complete is True
        finally:
            loop.close()

    async def test_result_awaits_completion(self) -> None:
        """Test that result() awaits the underlying task."""
        mock_result = MagicMock(spec=SubagentResult)
        mock_result.output = "completed"

        async def coro() -> SubagentResult:
            return mock_result

        task = asyncio.create_task(coro())

        handle = DelegationHandle(
            subagent_name="test-agent",
            task="Awaitable task",
            _task=task,
        )

        result = await handle.result()
        assert result.output == "completed"

    async def test_result_without_task_raises_error(self) -> None:
        """Test that result() raises RuntimeError when no task is set."""
        handle = DelegationHandle(
            subagent_name="test-agent",
            task="No task",
        )

        with pytest.raises(RuntimeError, match="No task associated"):
            await handle.result()

    async def test_result_on_cancelled_task_raises_error(self) -> None:
        """Test that result() on a cancelled task raises CancelledError."""

        async def long_running() -> SubagentResult:
            await asyncio.sleep(100)
            return MagicMock(spec=SubagentResult)  # pragma: no cover

        task = asyncio.create_task(long_running())
        handle = DelegationHandle(
            subagent_name="test-agent",
            task="Cancellable task",
            _task=task,
        )

        handle.cancel()
        # Allow cancellation to propagate
        await asyncio.sleep(0)

        with pytest.raises(asyncio.CancelledError):
            await handle.result()

    def test_cancel_running_task(self) -> None:
        """Test that cancel() cancels a running task."""
        loop = asyncio.new_event_loop()
        try:
            future: asyncio.Future[SubagentResult] = loop.create_future()
            task = asyncio.ensure_future(future, loop=loop)

            handle = DelegationHandle(
                subagent_name="test-agent",
                task="Running task",
                _task=task,
            )

            assert not task.cancelled()
            handle.cancel()
            assert task.cancelled()
        finally:
            loop.close()

    def test_cancel_completed_task_is_noop(self) -> None:
        """Test that cancel() on an already-completed task is a no-op."""
        loop = asyncio.new_event_loop()
        try:
            future: asyncio.Future[SubagentResult] = loop.create_future()
            mock_result = MagicMock(spec=SubagentResult)
            future.set_result(mock_result)
            task = asyncio.ensure_future(future, loop=loop)

            handle = DelegationHandle(
                subagent_name="test-agent",
                task="Completed task",
                _task=task,
            )

            assert handle.is_complete is True
            # Should not raise
            handle.cancel()
            assert not task.cancelled()
            assert handle.is_complete is True
        finally:
            loop.close()

    def test_cancel_without_task_is_noop(self) -> None:
        """Test that cancel() without a task is a no-op."""
        handle = DelegationHandle(
            subagent_name="test-agent",
            task="No task handle",
        )

        # Should not raise
        handle.cancel()

    def test_repr_excludes_task(self) -> None:
        """Test that _task is excluded from repr."""
        handle = DelegationHandle(
            subagent_name="test-agent",
            task="Some task",
        )

        repr_str = repr(handle)
        assert "subagent_name" in repr_str
        assert "_task" not in repr_str
