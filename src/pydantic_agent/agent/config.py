"""Agent configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field

from pydantic_agent.context.config import CompactionConfig
from pydantic_agent.tokens.config import TokenizerConfig


class AgentConfig(BaseModel):
    """Configuration for agent execution.

    Attributes:
        max_iterations: Maximum tool-calling iterations before stopping.
        system_prompt: System prompt for the agent.
        context: Context compaction configuration. None uses settings default.
        tokenizer: Tokenizer configuration. None uses settings default.
        track_context: Whether to track messages internally across runs.
        auto_compact: Whether to automatically compact when threshold is reached.
    """

    max_iterations: int = Field(
        default=10,
        gt=0,
        description="Maximum tool-calling iterations",
    )
    system_prompt: str = Field(
        default="",
        description="System prompt for the agent",
    )
    context: CompactionConfig | None = Field(
        default=None,
        description="Context compaction config. None uses settings default.",
    )
    tokenizer: TokenizerConfig | None = Field(
        default=None,
        description="Tokenizer config. None uses settings default.",
    )
    track_context: bool = Field(
        default=True,
        description="Track messages internally across runs",
    )
    auto_compact: bool = Field(
        default=True,
        description="Auto-compact when threshold reached",
    )
