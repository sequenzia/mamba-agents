"""Context management configuration."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


CompactionStrategyType = Literal[
    "sliding_window",
    "summarize_older",
    "selective_pruning",
    "importance_scoring",
    "hybrid",
]


class CompactionConfig(BaseModel):
    """Configuration for context window compaction.

    Attributes:
        strategy: Compaction strategy to use.
        trigger_threshold_tokens: Token count that triggers compaction.
        target_tokens: Target token count after compaction.
        preserve_recent_turns: Number of recent turns to always preserve.
        preserve_system_prompt: Always preserve the system prompt.
        summarization_model: Model to use for summarization (or "same").
    """

    strategy: CompactionStrategyType = Field(
        default="sliding_window",
        description="Compaction strategy to use",
    )
    trigger_threshold_tokens: int = Field(
        default=100000,
        gt=0,
        description="Token count that triggers compaction",
    )
    target_tokens: int = Field(
        default=80000,
        gt=0,
        description="Target token count after compaction",
    )
    preserve_recent_turns: int = Field(
        default=10,
        ge=0,
        description="Number of recent turns to always preserve",
    )
    preserve_system_prompt: bool = Field(
        default=True,
        description="Always preserve the system prompt",
    )
    summarization_model: str = Field(
        default="same",
        description="Model for summarization ('same' uses agent's model)",
    )
