"""ReAct workflow hooks for observability."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from mamba_agents.workflows.hooks import WorkflowHooks

if TYPE_CHECKING:
    from mamba_agents.context.compaction.base import CompactionResult
    from mamba_agents.workflows.react.state import ReActState

# Type aliases for ReAct-specific hooks
ThoughtHook = Callable[["ReActState", str], Awaitable[None] | None]
ActionHook = Callable[["ReActState", str, dict[str, Any]], Awaitable[None] | None]
ObservationHook = Callable[["ReActState", str, bool], Awaitable[None] | None]
CompactionHook = Callable[["CompactionResult"], Awaitable[None] | None]


class ReActHooks(WorkflowHooks["ReActState", str]):
    """Extended hooks for ReAct workflow observability.

    Inherits the 8 base workflow hooks and adds 4 ReAct-specific hooks:
    - on_thought: Called when a reasoning trace is generated.
    - on_action: Called when a tool is about to be executed.
    - on_observation: Called when a tool result is received.
    - on_compaction: Called when context is compacted.

    All hooks can be sync or async functions.

    Example:
        >>> def log_thought(state: ReActState, thought: str) -> None:
        ...     print(f"Thought: {thought}")
        >>>
        >>> hooks = ReActHooks(on_thought=log_thought)
        >>> workflow = ReActWorkflow(agent, hooks=hooks)
    """

    def __init__(
        self,
        # Inherited from WorkflowHooks
        on_workflow_start: Callable[..., Awaitable[None] | None] | None = None,
        on_workflow_complete: Callable[..., Awaitable[None] | None] | None = None,
        on_workflow_error: Callable[..., Awaitable[None] | None] | None = None,
        on_step_start: Callable[..., Awaitable[None] | None] | None = None,
        on_step_complete: Callable[..., Awaitable[None] | None] | None = None,
        on_step_error: Callable[..., Awaitable[None] | None] | None = None,
        on_iteration_start: Callable[..., Awaitable[None] | None] | None = None,
        on_iteration_complete: Callable[..., Awaitable[None] | None] | None = None,
        # ReAct-specific hooks
        on_thought: ThoughtHook | None = None,
        on_action: ActionHook | None = None,
        on_observation: ObservationHook | None = None,
        on_compaction: CompactionHook | None = None,
    ) -> None:
        """Initialize ReAct hooks.

        Args:
            on_workflow_start: Called when workflow begins.
            on_workflow_complete: Called when workflow completes successfully.
            on_workflow_error: Called when workflow fails.
            on_step_start: Called before each step executes.
            on_step_complete: Called after each step completes.
            on_step_error: Called when a step fails.
            on_iteration_start: Called at the start of each iteration.
            on_iteration_complete: Called at the end of each iteration.
            on_thought: Called when a thought/reasoning is generated.
            on_action: Called when a tool is about to execute.
            on_observation: Called when a tool result is received.
            on_compaction: Called when context is compacted.
        """
        super().__init__(
            on_workflow_start=on_workflow_start,
            on_workflow_complete=on_workflow_complete,
            on_workflow_error=on_workflow_error,
            on_step_start=on_step_start,
            on_step_complete=on_step_complete,
            on_step_error=on_step_error,
            on_iteration_start=on_iteration_start,
            on_iteration_complete=on_iteration_complete,
        )
        self.on_thought = on_thought
        self.on_action = on_action
        self.on_observation = on_observation
        self.on_compaction = on_compaction

    async def trigger_thought(self, state: ReActState, thought: str) -> None:
        """Trigger the on_thought hook.

        Args:
            state: Current ReAct state.
            thought: The generated thought/reasoning.
        """
        await self._trigger("on_thought", state, thought)

    async def trigger_action(
        self,
        state: ReActState,
        tool_name: str,
        tool_args: dict[str, Any],
    ) -> None:
        """Trigger the on_action hook.

        Args:
            state: Current ReAct state.
            tool_name: Name of the tool being called.
            tool_args: Arguments passed to the tool.
        """
        await self._trigger("on_action", state, tool_name, tool_args)

    async def trigger_observation(
        self,
        state: ReActState,
        observation: str,
        is_error: bool = False,
    ) -> None:
        """Trigger the on_observation hook.

        Args:
            state: Current ReAct state.
            observation: The tool result or error message.
            is_error: Whether this observation is an error.
        """
        await self._trigger("on_observation", state, observation, is_error)

    async def trigger_compaction(self, result: CompactionResult) -> None:
        """Trigger the on_compaction hook.

        Args:
            result: The compaction result with details.
        """
        await self._trigger("on_compaction", result)
