"""ReAct workflow state management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from pydantic_agent.workflows.react.config import ReActConfig


@dataclass
class ScratchpadEntry:
    """Single entry in the ReAct scratchpad.

    Attributes:
        entry_type: Type of entry (thought, action, or observation).
        content: The content of this entry.
        timestamp: When this entry was created.
        token_count: Estimated token count for this entry.
        metadata: Additional entry-specific metadata.
    """

    entry_type: Literal["thought", "action", "observation"]
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReActState:
    """Internal state for ReAct workflow execution.

    This is stored in WorkflowState.context and tracks the full
    reasoning trace, termination status, and token usage.

    Attributes:
        task: The original user task/prompt.
        scratchpad: List of all Thought/Action/Observation entries.
        current_thought: The most recent thought generated.
        current_action: The most recent action taken.
        current_observation: The most recent observation received.
        is_terminated: Whether the workflow has terminated.
        termination_reason: Why the workflow terminated.
        final_answer: The final answer if workflow completed successfully.
        iteration_token_counts: Token count for each iteration.
        total_tokens_used: Total tokens used across all iterations.
        compaction_count: Number of times context was compacted.
        consecutive_thought_count: Consecutive thoughts without action (for forcing action).
    """

    task: str
    scratchpad: list[ScratchpadEntry] = field(default_factory=list)

    # Current iteration state
    current_thought: str | None = None
    current_action: str | None = None
    current_observation: str | None = None

    # Termination tracking
    is_terminated: bool = False
    termination_reason: str | None = None
    final_answer: str | None = None

    # Token tracking
    iteration_token_counts: list[int] = field(default_factory=list)
    total_tokens_used: int = 0
    compaction_count: int = 0

    # Loop control
    consecutive_thought_count: int = 0

    def add_thought(self, thought: str, token_count: int = 0) -> None:
        """Add a thought to the scratchpad.

        Args:
            thought: The reasoning/thought content.
            token_count: Estimated token count.
        """
        self.scratchpad.append(
            ScratchpadEntry(
                entry_type="thought",
                content=thought,
                token_count=token_count,
            )
        )
        self.current_thought = thought
        self.consecutive_thought_count += 1

    def add_action(
        self,
        action: str,
        token_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an action to the scratchpad.

        Args:
            action: The action description (tool name and args).
            token_count: Estimated token count.
            metadata: Additional metadata (tool_name, tool_args, etc.).
        """
        self.scratchpad.append(
            ScratchpadEntry(
                entry_type="action",
                content=action,
                token_count=token_count,
                metadata=metadata or {},
            )
        )
        self.current_action = action
        self.consecutive_thought_count = 0  # Reset on action

    def add_observation(
        self,
        observation: str,
        token_count: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add an observation to the scratchpad.

        Args:
            observation: The tool result/observation content.
            token_count: Estimated token count.
            metadata: Additional metadata (tool_name, is_error, etc.).
        """
        self.scratchpad.append(
            ScratchpadEntry(
                entry_type="observation",
                content=observation,
                token_count=token_count,
                metadata=metadata or {},
            )
        )
        self.current_observation = observation

    def get_scratchpad_text(self, config: ReActConfig) -> str:
        """Format the scratchpad for prompt inclusion.

        Args:
            config: ReActConfig containing prefix settings.

        Returns:
            Formatted scratchpad text with prefixes.
        """
        if not self.scratchpad:
            return ""

        lines = []
        for entry in self.scratchpad:
            prefix = {
                "thought": config.reasoning_prefix,
                "action": config.action_prefix,
                "observation": config.observation_prefix,
            }[entry.entry_type]
            lines.append(f"{prefix}{entry.content}")

        return "\n".join(lines)

    def get_thoughts(self) -> list[str]:
        """Get all thoughts from the scratchpad."""
        return [e.content for e in self.scratchpad if e.entry_type == "thought"]

    def get_actions(self) -> list[str]:
        """Get all actions from the scratchpad."""
        return [e.content for e in self.scratchpad if e.entry_type == "action"]

    def get_observations(self) -> list[str]:
        """Get all observations from the scratchpad."""
        return [e.content for e in self.scratchpad if e.entry_type == "observation"]
