"""Subagent data models and configuration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from mamba_agents.agent.config import AgentConfig
from mamba_agents.prompts.config import TemplateConfig
from mamba_agents.tokens.tracker import TokenUsage

if TYPE_CHECKING:
    from mamba_agents.agent.result import AgentResult


class SubagentConfig(BaseModel):
    """Configuration for a subagent definition.

    Defines how a subagent should be created and what capabilities
    it has when executing delegated tasks.

    Attributes:
        name: Unique subagent identifier.
        description: When to delegate to this subagent.
        model: Model override. None inherits from parent agent.
        tools: Explicit tool allowlist. None inherits from parent.
        disallowed_tools: Tools to deny access to.
        system_prompt: Custom system prompt for the subagent.
        skills: Skills to pre-load at subagent startup.
        max_turns: Maximum conversation turns before termination.
        config: Full agent config override.
    """

    name: str = Field(
        description="Unique subagent identifier",
    )
    description: str = Field(
        description="When to delegate to this subagent",
    )
    model: str | None = Field(
        default=None,
        description="Model override (None=inherit from parent)",
    )
    tools: list[str | Callable[..., Any]] | None = Field(
        default=None,
        description="Explicit tool allowlist",
    )
    disallowed_tools: list[str] | None = Field(
        default=None,
        description="Tools to deny",
    )
    system_prompt: str | TemplateConfig | None = Field(
        default=None,
        description="Custom system prompt",
    )
    skills: list[str] | None = Field(
        default=None,
        description="Skills to pre-load at startup",
    )
    max_turns: int = Field(
        default=50,
        description="Maximum conversation turns",
    )
    config: AgentConfig | None = Field(
        default=None,
        description="Full agent config override",
    )


@dataclass
class SubagentResult:
    """Result from a subagent delegation.

    Stores the output, usage statistics, and metadata from a
    completed subagent execution.

    Attributes:
        output: Subagent's final response text.
        agent_result: Full pydantic-ai result wrapper.
        usage: Token usage for this delegation.
        duration: Execution time in seconds.
        subagent_name: Which subagent handled it.
        success: Whether delegation completed successfully.
        error: Error message if failed.
    """

    output: str
    agent_result: AgentResult[Any]
    usage: TokenUsage
    duration: float
    subagent_name: str
    success: bool
    error: str | None = None


@dataclass
class DelegationHandle:
    """Handle for tracking async subagent delegation.

    Wraps an asyncio.Task to provide a convenient API for checking
    status, awaiting results, and cancelling running subagents.

    Attributes:
        subagent_name: Name of the subagent handling the task.
        task: The task description that was delegated.
    """

    subagent_name: str
    task: str
    _task: asyncio.Task[SubagentResult] | None = field(default=None, repr=False)

    @property
    def is_complete(self) -> bool:
        """Check if the delegation has completed without blocking.

        Returns:
            True if the task is done or no task was assigned.
        """
        if self._task is None:
            return True
        return self._task.done()

    async def result(self) -> SubagentResult:
        """Await the delegation result.

        Returns:
            The SubagentResult from the completed subagent.

        Raises:
            asyncio.CancelledError: If the task was cancelled.
            RuntimeError: If no task is associated with this handle.
        """
        if self._task is None:
            msg = "No task associated with this delegation handle"
            raise RuntimeError(msg)
        return await self._task

    def cancel(self) -> None:
        """Cancel the running subagent delegation.

        If the task is already completed or no task exists, this is a no-op.
        """
        if self._task is not None and not self._task.done():
            self._task.cancel()
