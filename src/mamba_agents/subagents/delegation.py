"""Synchronous and asynchronous subagent delegation.

Handles delegating tasks to subagent ``Agent`` instances with both
synchronous (wait for result) and asynchronous (fire-and-forget) patterns.
Captures all errors into ``SubagentResult`` rather than raising, except for
unrecoverable configuration errors.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from mamba_agents.subagents.config import DelegationHandle, SubagentResult
from mamba_agents.subagents.errors import SubagentConfigError, SubagentError
from mamba_agents.tokens.tracker import TokenUsage

if TYPE_CHECKING:
    from mamba_agents.agent.core import Agent


def _extract_usage(agent_result: Any) -> TokenUsage:
    """Extract token usage from an AgentResult.

    Args:
        agent_result: The AgentResult wrapper from a completed agent run.

    Returns:
        TokenUsage with extracted token counts.
    """
    try:
        usage = agent_result.usage()
        prompt_tokens = (
            getattr(usage, "input_tokens", None)
            or getattr(usage, "request_tokens", None)
            or 0
        )
        completion_tokens = (
            getattr(usage, "output_tokens", None)
            or getattr(usage, "response_tokens", None)
            or 0
        )
        total_tokens = usage.total_tokens or (prompt_tokens + completion_tokens)
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            request_count=1,
        )
    except Exception:
        return TokenUsage()


def _validate_task(task: str) -> None:
    """Validate that the task string is not empty.

    Args:
        task: The task description to validate.

    Raises:
        SubagentError: If the task string is empty.
    """
    if not task or not task.strip():
        raise SubagentError("Task string must not be empty")


def _build_prompt(task: str, context: str | None = None) -> str:
    """Build the effective prompt by appending context if provided.

    Args:
        task: The task description.
        context: Optional context string to append.

    Returns:
        The combined prompt string.
    """
    if context:
        return f"{task}\n\n{context}"
    return task


async def delegate(
    agent: Agent[Any, Any],
    task: str,
    *,
    subagent_name: str = "",
    context_messages: list[dict[str, Any]] | None = None,
    context: str | None = None,
) -> SubagentResult:
    """Delegate a task to a subagent and await the result.

    Runs the subagent asynchronously via ``agent.run()`` and captures
    the output, token usage, duration, and any errors into a
    ``SubagentResult``.

    All errors during execution are captured in the result rather than
    raised, making delegation fault-tolerant. Only unrecoverable errors
    (e.g., ``SubagentConfigError``) are re-raised.

    Args:
        agent: The subagent ``Agent`` instance to delegate to.
        task: The task description for the subagent.
        subagent_name: Name of the subagent (for tracking).
        context_messages: Optional message history to inject as the
            subagent's initial conversation context.
        context: Optional context string appended to the task.

    Returns:
        SubagentResult with output, usage, duration, and success status.

    Raises:
        SubagentError: If the task string is empty.
        SubagentConfigError: If an unrecoverable configuration error occurs.
    """
    _validate_task(task)

    prompt = _build_prompt(task, context)

    # Build kwargs for agent.run()
    run_kwargs: dict[str, Any] = {}

    # Inject context messages as message history if provided
    if context_messages:
        from mamba_agents.agent.message_utils import dicts_to_model_messages

        run_kwargs["message_history"] = dicts_to_model_messages(context_messages)

    start = time.monotonic()
    try:
        result = await agent.run(prompt, **run_kwargs)
        duration = time.monotonic() - start

        usage = _extract_usage(result)
        output = str(result.output) if result.output is not None else ""

        return SubagentResult(
            output=output,
            agent_result=result,
            usage=usage,
            duration=duration,
            subagent_name=subagent_name,
            success=True,
        )
    except SubagentConfigError:
        # Unrecoverable config errors are re-raised
        raise
    except Exception as exc:
        duration = time.monotonic() - start

        # Detect max turns exceeded from pydantic-ai's UsageLimitExceeded
        error_msg = str(exc)
        try:
            from pydantic_ai.exceptions import UsageLimitExceeded

            if isinstance(exc, UsageLimitExceeded):
                error_msg = "Max turns exceeded"
        except ImportError:
            pass

        return SubagentResult(
            output="",
            agent_result=None,  # type: ignore[arg-type]
            usage=TokenUsage(),
            duration=duration,
            subagent_name=subagent_name,
            success=False,
            error=error_msg,
        )


def delegate_sync(
    agent: Agent[Any, Any],
    task: str,
    *,
    subagent_name: str = "",
    context_messages: list[dict[str, Any]] | None = None,
    context: str | None = None,
) -> SubagentResult:
    """Delegate a task to a subagent synchronously.

    Wraps ``agent.run_sync()`` for use in synchronous code paths.
    Captures all errors into ``SubagentResult``.

    Args:
        agent: The subagent ``Agent`` instance to delegate to.
        task: The task description for the subagent.
        subagent_name: Name of the subagent (for tracking).
        context_messages: Optional message history to inject as the
            subagent's initial conversation context.
        context: Optional context string appended to the task.

    Returns:
        SubagentResult with output, usage, duration, and success status.

    Raises:
        SubagentError: If the task string is empty.
        SubagentConfigError: If an unrecoverable configuration error occurs.
    """
    _validate_task(task)

    prompt = _build_prompt(task, context)

    # Build kwargs for agent.run_sync()
    run_kwargs: dict[str, Any] = {}

    # Inject context messages as message history if provided
    if context_messages:
        from mamba_agents.agent.message_utils import dicts_to_model_messages

        run_kwargs["message_history"] = dicts_to_model_messages(context_messages)

    start = time.monotonic()
    try:
        result = agent.run_sync(prompt, **run_kwargs)
        duration = time.monotonic() - start

        usage = _extract_usage(result)
        output = str(result.output) if result.output is not None else ""

        return SubagentResult(
            output=output,
            agent_result=result,
            usage=usage,
            duration=duration,
            subagent_name=subagent_name,
            success=True,
        )
    except SubagentConfigError:
        # Unrecoverable config errors are re-raised
        raise
    except Exception as exc:
        duration = time.monotonic() - start

        error_msg = str(exc)
        try:
            from pydantic_ai.exceptions import UsageLimitExceeded

            if isinstance(exc, UsageLimitExceeded):
                error_msg = "Max turns exceeded"
        except ImportError:
            pass

        return SubagentResult(
            output="",
            agent_result=None,  # type: ignore[arg-type]
            usage=TokenUsage(),
            duration=duration,
            subagent_name=subagent_name,
            success=False,
            error=error_msg,
        )


async def delegate_async(
    agent: Agent[Any, Any],
    task: str,
    *,
    subagent_name: str = "",
    context_messages: list[dict[str, Any]] | None = None,
    context: str | None = None,
) -> DelegationHandle:
    """Delegate a task to a subagent asynchronously.

    Returns a ``DelegationHandle`` immediately while the subagent runs
    in the background via ``asyncio.create_task()``.

    Args:
        agent: The subagent ``Agent`` instance to delegate to.
        task: The task description for the subagent.
        subagent_name: Name of the subagent (for tracking).
        context_messages: Optional message history to inject as the
            subagent's initial conversation context.
        context: Optional context string appended to the task.

    Returns:
        DelegationHandle for tracking and awaiting the result.

    Raises:
        SubagentError: If the task string is empty.
    """
    _validate_task(task)

    async_task = asyncio.create_task(
        delegate(
            agent,
            task,
            subagent_name=subagent_name,
            context_messages=context_messages,
            context=context,
        )
    )

    return DelegationHandle(
        subagent_name=subagent_name,
        task=task,
        _task=async_task,
    )
