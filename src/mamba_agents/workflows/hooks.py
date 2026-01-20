"""Workflow execution hooks and callbacks."""

from __future__ import annotations

import asyncio
import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from mamba_agents.workflows.base import WorkflowResult, WorkflowState, WorkflowStep

StateT = TypeVar("StateT")
OutputT = TypeVar("OutputT")

# Type aliases for hook functions
WorkflowStartHook = Callable[["WorkflowState[StateT]"], Awaitable[None] | None]
WorkflowCompleteHook = Callable[
    ["WorkflowResult[OutputT, StateT]"],
    Awaitable[None] | None,
]
WorkflowErrorHook = Callable[
    ["WorkflowState[StateT]", Exception],
    Awaitable[None] | None,
]
StepStartHook = Callable[
    ["WorkflowState[StateT]", int, str],
    Awaitable[None] | None,
]
StepCompleteHook = Callable[
    ["WorkflowState[StateT]", "WorkflowStep[Any]"],
    Awaitable[None] | None,
]
StepErrorHook = Callable[
    ["WorkflowState[StateT]", "WorkflowStep[Any]", Exception],
    Awaitable[None] | None,
]
IterationStartHook = Callable[
    ["WorkflowState[StateT]", int],
    Awaitable[None] | None,
]
IterationCompleteHook = Callable[
    ["WorkflowState[StateT]", int],
    Awaitable[None] | None,
]


class WorkflowHooks[StateT, OutputT]:
    """Hook callbacks for workflow execution events.

    All hooks are optional and receive workflow state/context.
    Hooks can be sync or async functions.

    Attributes:
        on_workflow_start: Called when workflow begins.
        on_workflow_complete: Called when workflow completes successfully.
        on_workflow_error: Called when workflow fails.
        on_step_start: Called before each step executes.
        on_step_complete: Called after each step completes.
        on_step_error: Called when a step fails.
        on_iteration_start: Called at the start of each iteration.
        on_iteration_complete: Called at the end of each iteration.
    """

    def __init__(
        self,
        on_workflow_start: WorkflowStartHook[StateT] | None = None,
        on_workflow_complete: WorkflowCompleteHook[OutputT, StateT] | None = None,
        on_workflow_error: WorkflowErrorHook[StateT] | None = None,
        on_step_start: StepStartHook[StateT] | None = None,
        on_step_complete: StepCompleteHook[StateT] | None = None,
        on_step_error: StepErrorHook[StateT] | None = None,
        on_iteration_start: IterationStartHook[StateT] | None = None,
        on_iteration_complete: IterationCompleteHook[StateT] | None = None,
    ) -> None:
        """Initialize workflow hooks.

        Args:
            on_workflow_start: Called when workflow begins.
            on_workflow_complete: Called when workflow completes successfully.
            on_workflow_error: Called when workflow fails.
            on_step_start: Called before each step executes.
            on_step_complete: Called after each step completes.
            on_step_error: Called when a step fails.
            on_iteration_start: Called at the start of each iteration.
            on_iteration_complete: Called at the end of each iteration.
        """
        self.on_workflow_start = on_workflow_start
        self.on_workflow_complete = on_workflow_complete
        self.on_workflow_error = on_workflow_error
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete
        self.on_step_error = on_step_error
        self.on_iteration_start = on_iteration_start
        self.on_iteration_complete = on_iteration_complete

    async def trigger_workflow_start(self, state: WorkflowState[StateT]) -> None:
        """Trigger workflow start hook.

        Args:
            state: Current workflow state.
        """
        if self.on_workflow_start:
            await self._call_hook(self.on_workflow_start, state)

    async def trigger_workflow_complete(
        self,
        result: WorkflowResult[OutputT, StateT],
    ) -> None:
        """Trigger workflow complete hook.

        Args:
            result: Workflow result.
        """
        if self.on_workflow_complete:
            await self._call_hook(self.on_workflow_complete, result)

    async def trigger_workflow_error(
        self,
        state: WorkflowState[StateT],
        error: Exception,
    ) -> None:
        """Trigger workflow error hook.

        Args:
            state: Current workflow state.
            error: The exception that caused the failure.
        """
        if self.on_workflow_error:
            await self._call_hook(self.on_workflow_error, state, error)

    async def trigger_step_start(
        self,
        state: WorkflowState[StateT],
        step_number: int,
        step_type: str,
    ) -> None:
        """Trigger step start hook.

        Args:
            state: Current workflow state.
            step_number: The step number about to execute.
            step_type: Type identifier of the step.
        """
        if self.on_step_start:
            await self._call_hook(self.on_step_start, state, step_number, step_type)

    async def trigger_step_complete(
        self,
        state: WorkflowState[StateT],
        step: WorkflowStep[Any],
    ) -> None:
        """Trigger step complete hook.

        Args:
            state: Current workflow state.
            step: The completed step.
        """
        if self.on_step_complete:
            await self._call_hook(self.on_step_complete, state, step)

    async def trigger_step_error(
        self,
        state: WorkflowState[StateT],
        step: WorkflowStep[Any],
        error: Exception,
    ) -> None:
        """Trigger step error hook.

        Args:
            state: Current workflow state.
            step: The failed step.
            error: The exception that caused the failure.
        """
        if self.on_step_error:
            await self._call_hook(self.on_step_error, state, step, error)

    async def trigger_iteration_start(
        self,
        state: WorkflowState[StateT],
        iteration: int,
    ) -> None:
        """Trigger iteration start hook.

        Args:
            state: Current workflow state.
            iteration: The iteration number starting.
        """
        if self.on_iteration_start:
            await self._call_hook(self.on_iteration_start, state, iteration)

    async def trigger_iteration_complete(
        self,
        state: WorkflowState[StateT],
        iteration: int,
    ) -> None:
        """Trigger iteration complete hook.

        Args:
            state: Current workflow state.
            iteration: The iteration number completed.
        """
        if self.on_iteration_complete:
            await self._call_hook(self.on_iteration_complete, state, iteration)

    @staticmethod
    async def _call_hook(hook: Callable[..., Any], *args: Any) -> None:
        """Call hook function (sync or async).

        Args:
            hook: The hook function to call.
            *args: Arguments to pass to the hook.
        """
        if inspect.iscoroutinefunction(hook):
            await hook(*args)
        else:
            # Run sync function in executor to avoid blocking
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, functools.partial(hook, *args))
