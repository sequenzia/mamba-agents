"""ReAct workflow configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from pydantic_agent.workflows.config import WorkflowConfig

# MVP: only tool-based termination
# Confidence-based termination deferred to future implementation
TerminationStrategy = Literal["tool"]


class ReActConfig(WorkflowConfig):
    """Configuration for ReAct workflow execution.

    Extends WorkflowConfig with ReAct-specific settings for reasoning
    trace visibility, termination strategy, and context management.

    Attributes:
        expose_reasoning: Whether Thought steps appear in workflow state.
        reasoning_prefix: Prefix for reasoning/thought in prompts.
        action_prefix: Prefix for actions in prompts.
        observation_prefix: Prefix for observations in prompts.
        termination_strategy: How to detect workflow completion ("tool" only for MVP).
        final_answer_tool_name: Name of the tool that signals completion.
        auto_compact_in_workflow: Whether to auto-compact context mid-workflow.
        compact_threshold_ratio: Ratio of context limit to trigger compaction.
        max_consecutive_thoughts: Max thoughts without action before forcing action.
        include_scratchpad: Whether to include full reasoning history in each iteration.
        tool_retry_count: Number of retries for failed tool calls.

    Example:
        >>> config = ReActConfig(
        ...     max_iterations=15,
        ...     expose_reasoning=True,
        ...     termination_strategy="tool",
        ... )
    """

    # Reasoning trace visibility
    expose_reasoning: bool = Field(
        default=True,
        description="Whether Thought steps appear in workflow state",
    )
    reasoning_prefix: str = Field(
        default="Thought: ",
        description="Prefix for reasoning/thought in prompts",
    )
    action_prefix: str = Field(
        default="Action: ",
        description="Prefix for actions in prompts",
    )
    observation_prefix: str = Field(
        default="Observation: ",
        description="Prefix for observations in prompts",
    )

    # Termination strategy
    termination_strategy: TerminationStrategy = Field(
        default="tool",
        description="How to detect workflow completion (tool-based only for MVP)",
    )
    final_answer_tool_name: str = Field(
        default="final_answer",
        description="Name of the tool that signals completion",
    )

    # Context management
    auto_compact_in_workflow: bool = Field(
        default=True,
        description="Whether to auto-compact context mid-workflow",
    )
    compact_threshold_ratio: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Ratio of context limit to trigger compaction (0.1-1.0)",
    )

    # Loop behavior
    max_consecutive_thoughts: int = Field(
        default=3,
        gt=0,
        description="Max thoughts without action before forcing action",
    )
    include_scratchpad: bool = Field(
        default=True,
        description="Whether to include full reasoning history in each iteration",
    )

    # Tool retry
    tool_retry_count: int = Field(
        default=2,
        ge=0,
        description="Number of retries for failed tool calls",
    )
