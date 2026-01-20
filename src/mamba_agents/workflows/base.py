"""Base classes for workflow execution."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from mamba_agents.workflows.config import WorkflowConfig
    from mamba_agents.workflows.hooks import WorkflowHooks

DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")
StateT = TypeVar("StateT")


@dataclass
class WorkflowStep[OutputT]:
    """A single step in workflow execution.

    Attributes:
        step_number: Sequential step number (1-indexed).
        step_type: Type identifier (e.g., "agent_call", "decision", "reflection").
        description: Human-readable step description.
        input_data: Input provided to this step.
        output_data: Output produced by this step.
        agent_result: AgentResult if step invoked an agent.
        error: Error message if step failed.
        started_at: Step start timestamp.
        completed_at: Step completion timestamp.
        metadata: Additional step-specific metadata.
    """

    step_number: int
    step_type: str
    description: str
    input_data: Any
    output_data: OutputT | None = None
    agent_result: Any = None  # AgentResult[OutputT] - avoid circular import
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate step duration in seconds."""
        if self.completed_at is None:
            return None
        return (self.completed_at - self.started_at).total_seconds()

    @property
    def success(self) -> bool:
        """Check if step completed successfully."""
        return self.error is None and self.completed_at is not None


@dataclass
class WorkflowState[StateT]:
    """Current state of workflow execution.

    Tracks progress, decisions, and execution history.

    Attributes:
        current_step: Current step number (1-indexed).
        total_steps: Total steps executed so far.
        iteration_count: Current iteration count within workflow.
        is_complete: Whether workflow has completed.
        is_failed: Whether workflow failed.
        steps: List of all executed steps.
        context: Workflow-specific state data.
        metadata: Additional workflow metadata.
    """

    current_step: int = 1
    total_steps: int = 0
    iteration_count: int = 0
    is_complete: bool = False
    is_failed: bool = False
    steps: list[WorkflowStep[Any]] = field(default_factory=list)
    context: StateT | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: WorkflowStep[Any]) -> None:
        """Add a completed step to history."""
        self.steps.append(step)
        self.total_steps = len(self.steps)
        self.current_step = self.total_steps + 1

    def get_latest_step(self) -> WorkflowStep[Any] | None:
        """Get the most recent step."""
        return self.steps[-1] if self.steps else None

    def get_step(self, step_number: int) -> WorkflowStep[Any] | None:
        """Get step by number (1-indexed)."""
        idx = step_number - 1
        return self.steps[idx] if 0 <= idx < len(self.steps) else None


@dataclass
class WorkflowResult[OutputT, StateT]:
    """Result of workflow execution.

    Attributes:
        success: Whether workflow completed successfully.
        output: Final workflow output.
        state: Final workflow state.
        error: Error message if workflow failed.
        total_steps: Total steps executed.
        total_iterations: Total iterations across all steps.
        duration_seconds: Total execution time.
        termination_reason: Why the workflow stopped.
    """

    success: bool
    output: OutputT | None = None
    state: WorkflowState[StateT] | None = None
    error: str | None = None
    total_steps: int = 0
    total_iterations: int = 0
    duration_seconds: float = 0.0
    termination_reason: str = "unknown"

    @classmethod
    def ok(
        cls,
        output: OutputT,
        state: WorkflowState[StateT],
        duration: float,
        reason: str = "completed",
    ) -> WorkflowResult[OutputT, StateT]:
        """Create successful result."""
        return cls(
            success=True,
            output=output,
            state=state,
            total_steps=state.total_steps,
            total_iterations=state.iteration_count,
            duration_seconds=duration,
            termination_reason=reason,
        )

    @classmethod
    def fail(
        cls,
        error: str,
        state: WorkflowState[StateT] | None = None,
        duration: float = 0.0,
        reason: str = "error",
    ) -> WorkflowResult[Any, StateT]:
        """Create failed result."""
        return cls(
            success=False,
            error=error,
            state=state,
            total_steps=state.total_steps if state else 0,
            total_iterations=state.iteration_count if state else 0,
            duration_seconds=duration,
            termination_reason=reason,
        )


class Workflow[DepsT, OutputT, StateT](ABC):
    """Abstract base class for agentic workflows.

    Workflows orchestrate Agent instances through multi-step execution patterns.
    Subclasses implement specific workflow types (ReAct, Plan-Execute, Reflection).

    Example:
        >>> from mamba_agents import Agent
        >>> from mamba_agents.workflows import Workflow, WorkflowConfig
        >>>
        >>> # Create a custom workflow by extending Workflow
        >>> class MyWorkflow(Workflow[None, str, dict]):
        ...     @property
        ...     def name(self) -> str:
        ...         return "my_workflow"
        ...
        ...     def _create_initial_state(self, prompt: str) -> WorkflowState[dict]:
        ...         return WorkflowState(context={"prompt": prompt})
        ...
        ...     async def _execute(self, prompt, state, deps):
        ...         # Implement workflow logic
        ...         return "result"
    """

    def __init__(
        self,
        config: WorkflowConfig | None = None,
        hooks: WorkflowHooks[StateT, OutputT] | None = None,
    ) -> None:
        """Initialize workflow.

        Args:
            config: Workflow execution configuration.
            hooks: Optional hooks for observability.
        """
        from mamba_agents.workflows.config import WorkflowConfig
        from mamba_agents.workflows.hooks import WorkflowHooks

        self._config = config or WorkflowConfig()
        self._hooks: WorkflowHooks[StateT, OutputT] = hooks or WorkflowHooks()

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the workflow name/type identifier.

        Returns:
            Workflow type identifier.
        """
        ...

    @abstractmethod
    async def _execute(
        self,
        prompt: str,
        state: WorkflowState[StateT],
        deps: DepsT | None = None,
    ) -> OutputT:
        """Execute the workflow logic.

        Subclasses implement the specific execution pattern.

        Args:
            prompt: Initial user prompt/task.
            state: Current workflow state.
            deps: Optional dependencies for agent calls.

        Returns:
            Final workflow output.

        Raises:
            WorkflowError: If execution fails.
        """
        ...

    @abstractmethod
    def _create_initial_state(self, prompt: str) -> WorkflowState[StateT]:
        """Create initial workflow state.

        Args:
            prompt: Initial user prompt.

        Returns:
            Initialized WorkflowState.
        """
        ...

    async def run(
        self,
        prompt: str,
        deps: DepsT | None = None,
    ) -> WorkflowResult[OutputT, StateT]:
        """Run the workflow.

        Args:
            prompt: Initial user prompt/task.
            deps: Optional dependencies for agent calls.

        Returns:
            WorkflowResult with output and execution details.
        """
        start_time = datetime.now(UTC)
        state = self._create_initial_state(prompt)

        try:
            # Trigger workflow start hook
            if self._config.enable_hooks:
                await self._hooks.trigger_workflow_start(state)

            # Execute workflow with timeout
            if self._config.timeout_seconds:
                output = await asyncio.wait_for(
                    self._execute(prompt, state, deps),
                    timeout=self._config.timeout_seconds,
                )
            else:
                output = await self._execute(prompt, state, deps)

            state.is_complete = True
            duration = (datetime.now(UTC) - start_time).total_seconds()

            result: WorkflowResult[OutputT, StateT] = WorkflowResult.ok(
                output=output,
                state=state,
                duration=duration,
                reason="completed",
            )

            # Trigger workflow complete hook
            if self._config.enable_hooks:
                await self._hooks.trigger_workflow_complete(result)

            return result

        except TimeoutError:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            state.is_failed = True
            return WorkflowResult.fail(
                error=f"Workflow exceeded timeout of {self._config.timeout_seconds}s",
                state=state,
                duration=duration,
                reason="timeout",
            )

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            state.is_failed = True

            # Trigger error hook
            if self._config.enable_hooks:
                await self._hooks.trigger_workflow_error(state, e)

            return WorkflowResult.fail(
                error=str(e),
                state=state,
                duration=duration,
                reason="error",
            )

    def run_sync(
        self,
        prompt: str,
        deps: DepsT | None = None,
    ) -> WorkflowResult[OutputT, StateT]:
        """Run the workflow synchronously.

        Args:
            prompt: Initial user prompt/task.
            deps: Optional dependencies for agent calls.

        Returns:
            WorkflowResult with output and execution details.
        """
        return asyncio.run(self.run(prompt, deps))

    @property
    def config(self) -> WorkflowConfig:
        """Get workflow configuration."""
        return self._config

    @property
    def hooks(self) -> WorkflowHooks[StateT, OutputT]:
        """Get workflow hooks."""
        return self._hooks
