"""Tests for subagent delegation logic."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents.agent.core import Agent
from mamba_agents.subagents.config import DelegationHandle, SubagentResult
from mamba_agents.subagents.delegation import (
    _build_prompt,
    _extract_usage,
    _validate_task,
    delegate,
    delegate_async,
    delegate_sync,
)
from mamba_agents.subagents.errors import SubagentConfigError, SubagentError
from mamba_agents.tokens.tracker import TokenUsage


@pytest.fixture
def test_agent(test_model: TestModel) -> Agent[None, str]:
    """Create a test agent for delegation tests."""
    return Agent(test_model)


@pytest.fixture
def test_agent_with_response() -> Agent[None, str]:
    """Create a test agent with a specific response."""
    model = TestModel(custom_output_text="delegation result")
    return Agent(model)


class TestValidateTask:
    """Tests for _validate_task helper."""

    def test_empty_string_raises(self) -> None:
        """Empty string raises SubagentError."""
        with pytest.raises(SubagentError, match="must not be empty"):
            _validate_task("")

    def test_whitespace_only_raises(self) -> None:
        """Whitespace-only string raises SubagentError."""
        with pytest.raises(SubagentError, match="must not be empty"):
            _validate_task("   ")

    def test_valid_task_passes(self) -> None:
        """Valid task string does not raise."""
        _validate_task("Summarize the document")


class TestBuildPrompt:
    """Tests for _build_prompt helper."""

    def test_task_only(self) -> None:
        """Task without context returns task unchanged."""
        assert _build_prompt("Do something") == "Do something"

    def test_task_with_context(self) -> None:
        """Task with context string appends context."""
        result = _build_prompt("Do something", context="Extra info")
        assert result == "Do something\n\nExtra info"

    def test_none_context_ignored(self) -> None:
        """None context returns task unchanged."""
        assert _build_prompt("Do something", context=None) == "Do something"

    def test_empty_context_ignored(self) -> None:
        """Empty context string returns task unchanged."""
        assert _build_prompt("Do something", context="") == "Do something"


class TestExtractUsage:
    """Tests for _extract_usage helper."""

    def test_extracts_from_agent_result(self) -> None:
        """Extracts token usage from a valid AgentResult."""
        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50
        mock_usage.total_tokens = 150

        mock_result = MagicMock()
        mock_result.usage.return_value = mock_usage

        usage = _extract_usage(mock_result)

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150
        assert usage.request_count == 1

    def test_returns_empty_on_error(self) -> None:
        """Returns empty TokenUsage when extraction fails."""
        mock_result = MagicMock()
        mock_result.usage.side_effect = Exception("broken")

        usage = _extract_usage(mock_result)

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_fallback_request_tokens(self) -> None:
        """Falls back to request_tokens if input_tokens missing."""
        mock_usage = MagicMock()
        mock_usage.input_tokens = None
        mock_usage.request_tokens = 80
        mock_usage.output_tokens = None
        mock_usage.response_tokens = 40
        mock_usage.total_tokens = 120

        mock_result = MagicMock()
        mock_result.usage.return_value = mock_usage

        usage = _extract_usage(mock_result)

        assert usage.prompt_tokens == 80
        assert usage.completion_tokens == 40
        assert usage.total_tokens == 120


class TestSyncDelegation:
    """Tests for synchronous delegation via delegate_sync."""

    def test_sync_delegation_returns_subagent_result(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Sync delegation runs subagent and returns SubagentResult."""
        with test_agent.override(model=TestModel(custom_output_text="sync output")):
            result = delegate_sync(
                test_agent,
                "Summarize this",
                subagent_name="test-sub",
            )

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "sync output"
        assert result.subagent_name == "test-sub"
        assert result.error is None

    def test_sync_delegation_includes_usage(
        self, test_agent: Agent[None, str]
    ) -> None:
        """SubagentResult includes usage from the delegation."""
        with test_agent.override(model=TestModel(custom_output_text="usage test")):
            result = delegate_sync(test_agent, "Test task")

        assert isinstance(result.usage, TokenUsage)

    def test_sync_delegation_includes_duration(
        self, test_agent: Agent[None, str]
    ) -> None:
        """SubagentResult includes duration."""
        with test_agent.override(model=TestModel(custom_output_text="duration test")):
            result = delegate_sync(test_agent, "Test task")

        assert result.duration >= 0.0

    def test_sync_delegation_includes_success_flag(
        self, test_agent: Agent[None, str]
    ) -> None:
        """SubagentResult includes success flag."""
        with test_agent.override(model=TestModel(custom_output_text="success test")):
            result = delegate_sync(test_agent, "Test task")

        assert result.success is True

    def test_sync_delegation_with_context_string(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Context string is appended to the task."""
        with test_agent.override(model=TestModel(custom_output_text="context test")):
            result = delegate_sync(
                test_agent,
                "Summarize",
                context="Additional context here",
            )

        assert result.success is True
        assert result.output == "context test"

    def test_sync_delegation_empty_task_raises(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Empty task string raises SubagentError."""
        with pytest.raises(SubagentError, match="must not be empty"):
            delegate_sync(test_agent, "")

    def test_sync_delegation_captures_error(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Model errors are captured in SubagentResult."""
        # Patch agent.run_sync to raise an exception
        with patch.object(test_agent, "run_sync", side_effect=RuntimeError("API failed")):
            result = delegate_sync(test_agent, "Failing task")

        assert result.success is False
        assert result.error is not None
        assert "API failed" in result.error
        assert result.output == ""

    def test_sync_delegation_config_error_raised(
        self, test_agent: Agent[None, str]
    ) -> None:
        """SubagentConfigError is re-raised, not captured."""
        with (
            patch.object(
                test_agent,
                "run_sync",
                side_effect=SubagentConfigError("bad-agent", "invalid config"),
            ),
            pytest.raises(SubagentConfigError, match="bad-agent"),
        ):
            delegate_sync(test_agent, "Config error task")


class TestAsyncDelegation:
    """Tests for asynchronous delegation via delegate."""

    async def test_async_delegation_returns_subagent_result(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Async delegate() runs subagent and returns SubagentResult."""
        with test_agent.override(model=TestModel(custom_output_text="async output")):
            result = await delegate(
                test_agent,
                "Summarize this",
                subagent_name="async-sub",
            )

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "async output"
        assert result.subagent_name == "async-sub"

    async def test_async_delegation_includes_usage(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Async delegation includes token usage."""
        with test_agent.override(model=TestModel(custom_output_text="usage")):
            result = await delegate(test_agent, "Usage test")

        assert isinstance(result.usage, TokenUsage)

    async def test_async_delegation_includes_duration(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Async delegation includes duration."""
        with test_agent.override(model=TestModel(custom_output_text="duration")):
            result = await delegate(test_agent, "Duration test")

        assert result.duration >= 0.0

    async def test_async_delegation_with_context_string(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Context string appended to task in async delegation."""
        with test_agent.override(model=TestModel(custom_output_text="ctx")):
            result = await delegate(
                test_agent,
                "Summarize",
                context="Extra context",
            )

        assert result.success is True

    async def test_async_delegation_with_context_messages(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Context messages injected as subagent's initial history."""
        messages = [
            {"role": "user", "content": "Previous question"},
            {"role": "assistant", "content": "Previous answer"},
        ]

        with test_agent.override(model=TestModel(custom_output_text="with history")):
            result = await delegate(
                test_agent,
                "Follow up question",
                context_messages=messages,
            )

        assert result.success is True
        assert result.output == "with history"

    async def test_async_delegation_empty_task_raises(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Empty task string raises SubagentError in async delegation."""
        with pytest.raises(SubagentError, match="must not be empty"):
            await delegate(test_agent, "")

    async def test_async_delegation_captures_error(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Model errors are captured in async SubagentResult."""
        with patch.object(test_agent, "run", side_effect=RuntimeError("API timeout")):
            result = await delegate(test_agent, "Failing task")

        assert result.success is False
        assert "API timeout" in result.error

    async def test_async_delegation_config_error_raised(
        self, test_agent: Agent[None, str]
    ) -> None:
        """SubagentConfigError is re-raised in async delegation."""
        with (
            patch.object(
                test_agent,
                "run",
                side_effect=SubagentConfigError("bad-agent", "broken"),
            ),
            pytest.raises(SubagentConfigError),
        ):
            await delegate(test_agent, "Config error task")


class TestDelegateAsync:
    """Tests for delegate_async returning DelegationHandle."""

    async def test_returns_delegation_handle(
        self, test_agent: Agent[None, str]
    ) -> None:
        """delegate_async returns DelegationHandle immediately."""
        with test_agent.override(model=TestModel(custom_output_text="async handle")):
            handle = await delegate_async(
                test_agent,
                "Background task",
                subagent_name="bg-sub",
            )

        assert isinstance(handle, DelegationHandle)
        assert handle.subagent_name == "bg-sub"
        assert handle.task == "Background task"

        # Clean up — await to prevent unhandled task warnings
        await handle.result()

    async def test_handle_result_returns_subagent_result(
        self, test_agent: Agent[None, str]
    ) -> None:
        """DelegationHandle.result() returns SubagentResult."""
        with test_agent.override(model=TestModel(custom_output_text="handle result")):
            handle = await delegate_async(test_agent, "Get result")
            result = await handle.result()

        assert isinstance(result, SubagentResult)
        assert result.success is True
        assert result.output == "handle result"

    async def test_handle_is_complete_before_done(
        self, test_agent: Agent[None, str]
    ) -> None:
        """DelegationHandle.is_complete reflects task status."""
        with test_agent.override(model=TestModel(custom_output_text="complete check")):
            handle = await delegate_async(test_agent, "Check completion")

            # Eventually completes
            result = await handle.result()
            assert handle.is_complete is True
            assert result.success is True

    async def test_handle_cancel(self, test_agent: Agent[None, str]) -> None:
        """DelegationHandle.cancel() cancels running subagent task."""
        # Create a slow-running scenario by patching agent.run
        async def slow_run(*args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(100)  # pragma: no cover

        with patch.object(test_agent, "run", side_effect=slow_run):
            handle = await delegate_async(test_agent, "Cancellable task")

            assert handle.is_complete is False
            handle.cancel()

            # Allow cancellation to propagate
            await asyncio.sleep(0)

            assert handle.is_complete is True

            with pytest.raises(asyncio.CancelledError):
                await handle.result()

    async def test_cancel_after_completion_is_noop(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Cancel after completion is a no-op, result already available."""
        with test_agent.override(model=TestModel(custom_output_text="already done")):
            handle = await delegate_async(test_agent, "Quick task")

            # Wait for completion
            result = await handle.result()
            assert result.success is True

            # Cancel after done — should be a no-op
            handle.cancel()
            assert handle.is_complete is True

            # Result is still available
            # Note: Can't await result() again on a completed asyncio.Task
            # because it just returns the same result
            result2 = await handle.result()
            assert result2.output == "already done"

    async def test_empty_task_raises_in_delegate_async(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Empty task raises SubagentError before creating handle."""
        with pytest.raises(SubagentError, match="must not be empty"):
            await delegate_async(test_agent, "")

    async def test_concurrent_async_delegations(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Multiple concurrent async delegations each get independent handles."""
        with test_agent.override(model=TestModel(custom_output_text="concurrent")):
            handles = []
            for i in range(5):
                handle = await delegate_async(
                    test_agent,
                    f"Task {i}",
                    subagent_name=f"sub-{i}",
                )
                handles.append(handle)

            # Each handle is independent
            assert len(handles) == 5
            for i, handle in enumerate(handles):
                assert handle.subagent_name == f"sub-{i}"
                assert handle.task == f"Task {i}"

            # All complete successfully
            results = [await h.result() for h in handles]
            for result in results:
                assert isinstance(result, SubagentResult)
                assert result.success is True

    async def test_delegate_async_with_context(
        self, test_agent: Agent[None, str]
    ) -> None:
        """delegate_async passes context string through."""
        with test_agent.override(model=TestModel(custom_output_text="ctx async")):
            handle = await delegate_async(
                test_agent,
                "Background task",
                context="Additional info",
            )
            result = await handle.result()

        assert result.success is True

    async def test_delegate_async_with_context_messages(
        self, test_agent: Agent[None, str]
    ) -> None:
        """delegate_async passes context messages through."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        with test_agent.override(model=TestModel(custom_output_text="msgs async")):
            handle = await delegate_async(
                test_agent,
                "Follow up",
                context_messages=messages,
            )
            result = await handle.result()

        assert result.success is True


class TestDelegationHandleLifecycle:
    """Tests for the full lifecycle of DelegationHandle."""

    async def test_handle_lifecycle_create_await_complete(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Full lifecycle: create handle, await result, check complete."""
        with test_agent.override(model=TestModel(custom_output_text="lifecycle")):
            handle = await delegate_async(test_agent, "Lifecycle test")

            # Eventually completes
            result = await handle.result()
            assert handle.is_complete is True
            assert result.success is True
            assert result.output == "lifecycle"

    async def test_handle_lifecycle_create_cancel(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Lifecycle: create handle, cancel before completion."""
        async def slow_run(*args: Any, **kwargs: Any) -> Any:
            await asyncio.sleep(100)  # pragma: no cover

        with patch.object(test_agent, "run", side_effect=slow_run):
            handle = await delegate_async(test_agent, "Cancel lifecycle")

            # Cancel
            handle.cancel()
            await asyncio.sleep(0)

            assert handle.is_complete is True

            with pytest.raises(asyncio.CancelledError):
                await handle.result()


class TestErrorCapture:
    """Tests for error capture in SubagentResult."""

    async def test_runtime_error_captured(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Runtime errors are captured in SubagentResult."""
        with patch.object(test_agent, "run", side_effect=RuntimeError("Unexpected error")):
            result = await delegate(test_agent, "Error task")

        assert result.success is False
        assert "Unexpected error" in result.error
        assert result.output == ""
        assert result.duration >= 0.0

    async def test_model_api_error_captured(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Model API errors are captured in SubagentResult."""
        with patch.object(
            test_agent,
            "run",
            side_effect=ConnectionError("Model server unreachable"),
        ):
            result = await delegate(test_agent, "API error task")

        assert result.success is False
        assert "unreachable" in result.error

    def test_sync_runtime_error_captured(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Sync delegation captures runtime errors."""
        with patch.object(
            test_agent, "run_sync", side_effect=ValueError("Bad input")
        ):
            result = delegate_sync(test_agent, "Sync error task")

        assert result.success is False
        assert "Bad input" in result.error

    async def test_usage_limit_exceeded_gives_max_turns_msg(
        self, test_agent: Agent[None, str]
    ) -> None:
        """UsageLimitExceeded gives 'Max turns exceeded' error message."""
        from pydantic_ai.exceptions import UsageLimitExceeded

        with patch.object(
            test_agent,
            "run",
            side_effect=UsageLimitExceeded("Exceeded request limit"),
        ):
            result = await delegate(test_agent, "Exceeds turns")

        assert result.success is False
        assert result.error == "Max turns exceeded"

    def test_sync_usage_limit_exceeded_gives_max_turns_msg(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Sync delegation also maps UsageLimitExceeded to max turns message."""
        from pydantic_ai.exceptions import UsageLimitExceeded

        with patch.object(
            test_agent,
            "run_sync",
            side_effect=UsageLimitExceeded("Exceeded"),
        ):
            result = delegate_sync(test_agent, "Sync max turns")

        assert result.success is False
        assert result.error == "Max turns exceeded"


class TestTokenUsageExtraction:
    """Integration tests for token usage extraction from AgentResult."""

    async def test_usage_extracted_from_real_agent_result(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Token usage is extracted from a real AgentResult."""
        with test_agent.override(model=TestModel(custom_output_text="token test")):
            result = await delegate(test_agent, "Extract tokens")

        assert isinstance(result.usage, TokenUsage)
        # TestModel provides some usage data
        assert result.usage.request_count == 1

    def test_sync_usage_extracted_from_real_agent_result(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Token usage extracted in sync delegation from real AgentResult."""
        with test_agent.override(model=TestModel(custom_output_text="sync token")):
            result = delegate_sync(test_agent, "Sync extract tokens")

        assert isinstance(result.usage, TokenUsage)
        assert result.usage.request_count == 1

    async def test_agent_result_accessible(
        self, test_agent: Agent[None, str]
    ) -> None:
        """The full AgentResult is accessible in SubagentResult."""
        with test_agent.override(model=TestModel(custom_output_text="agent result")):
            result = await delegate(test_agent, "Check agent result")

        assert result.agent_result is not None
        assert result.agent_result.output == "agent result"

    async def test_failed_delegation_has_empty_usage(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Failed delegation returns empty TokenUsage."""
        with patch.object(
            test_agent, "run", side_effect=RuntimeError("fail")
        ):
            result = await delegate(test_agent, "Fail task")

        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 0
        assert result.usage.total_tokens == 0


class TestContextInjection:
    """Tests for context injection into subagent."""

    async def test_context_messages_injected_as_history(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Context messages are passed as message_history to agent.run()."""
        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]

        with test_agent.override(model=TestModel(custom_output_text="with context")):
            result = await delegate(
                test_agent,
                "Tell me more about Python",
                context_messages=messages,
            )

        assert result.success is True
        assert result.output == "with context"

    def test_sync_context_messages_injected(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Context messages work in sync delegation too."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        with test_agent.override(model=TestModel(custom_output_text="sync ctx")):
            result = delegate_sync(
                test_agent,
                "Continue",
                context_messages=messages,
            )

        assert result.success is True

    async def test_context_string_appended_to_task(
        self, test_agent: Agent[None, str]
    ) -> None:
        """Context string is appended to task prompt."""
        with test_agent.override(model=TestModel(custom_output_text="appended")):
            result = await delegate(
                test_agent,
                "Summarize",
                context="Here is the document text.",
            )

        assert result.success is True
