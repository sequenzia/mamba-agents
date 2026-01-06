"""Agent configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for agent execution.

    Attributes:
        max_iterations: Maximum tool-calling iterations before stopping.
        system_prompt: System prompt for the agent.
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
