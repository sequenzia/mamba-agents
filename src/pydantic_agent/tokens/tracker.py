"""Token usage tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai.usage import Usage


@dataclass
class UsageRecord:
    """A single usage record.

    Attributes:
        timestamp: When the usage was recorded.
        prompt_tokens: Tokens in the prompt.
        completion_tokens: Tokens in the completion.
        total_tokens: Total tokens used.
        model: Model used for this request.
        tool_name: Optional tool name if tool call.
    """

    timestamp: datetime
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str | None = None
    tool_name: str | None = None


@dataclass
class TokenUsage:
    """Aggregate token usage statistics.

    Attributes:
        prompt_tokens: Total prompt tokens.
        completion_tokens: Total completion tokens.
        total_tokens: Total tokens.
        request_count: Number of requests.
        cached_tokens: Tokens served from cache.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0
    cached_tokens: int = 0


class UsageTracker:
    """Track token usage across requests.

    Provides per-request tracking, session aggregates, and cost estimation.
    """

    def __init__(
        self,
        cost_rates: dict[str, float] | None = None,
    ) -> None:
        """Initialize the usage tracker.

        Args:
            cost_rates: Optional cost per 1000 tokens for different models.
        """
        self._records: list[UsageRecord] = []
        self._totals = TokenUsage()
        self._cost_rates = cost_rates or {}

    def record_usage(
        self,
        usage: "Usage",
        model: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        """Record usage from a pydantic-ai result.

        Args:
            usage: Usage object from pydantic-ai.
            model: Optional model name.
            tool_name: Optional tool name for tool calls.
        """
        # Extract token counts from pydantic-ai Usage
        prompt_tokens = usage.request_tokens or 0
        completion_tokens = usage.response_tokens or 0
        total_tokens = usage.total_tokens or (prompt_tokens + completion_tokens)

        record = UsageRecord(
            timestamp=datetime.now(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            tool_name=tool_name,
        )

        self._records.append(record)

        # Update totals
        self._totals.prompt_tokens += prompt_tokens
        self._totals.completion_tokens += completion_tokens
        self._totals.total_tokens += total_tokens
        self._totals.request_count += 1

    def record_raw(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str | None = None,
        tool_name: str | None = None,
    ) -> None:
        """Record raw token counts.

        Args:
            prompt_tokens: Number of prompt tokens.
            completion_tokens: Number of completion tokens.
            model: Optional model name.
            tool_name: Optional tool name.
        """
        total = prompt_tokens + completion_tokens

        record = UsageRecord(
            timestamp=datetime.now(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            model=model,
            tool_name=tool_name,
        )

        self._records.append(record)

        self._totals.prompt_tokens += prompt_tokens
        self._totals.completion_tokens += completion_tokens
        self._totals.total_tokens += total
        self._totals.request_count += 1

    def get_total_usage(self) -> TokenUsage:
        """Get total usage statistics.

        Returns:
            TokenUsage with aggregate statistics.
        """
        return self._totals

    def get_usage_history(self) -> list[UsageRecord]:
        """Get usage history.

        Returns:
            List of all usage records.
        """
        return self._records.copy()

    def get_cost_estimate(self, model: str | None = None) -> float:
        """Estimate cost based on usage.

        Args:
            model: Model to use for cost calculation.
                   If None, uses default rate.

        Returns:
            Estimated cost in USD.
        """
        # Get rate per 1000 tokens
        rate = 0.0
        if model and model in self._cost_rates:
            rate = self._cost_rates[model]
        elif "default" in self._cost_rates:
            rate = self._cost_rates["default"]

        # Calculate cost
        return (self._totals.total_tokens / 1000) * rate

    def get_breakdown_by_tool(self) -> dict[str, TokenUsage]:
        """Get token usage broken down by tool.

        Returns:
            Dictionary mapping tool names to usage.
        """
        breakdown: dict[str, TokenUsage] = {}

        for record in self._records:
            key = record.tool_name or "_agent"

            if key not in breakdown:
                breakdown[key] = TokenUsage()

            breakdown[key].prompt_tokens += record.prompt_tokens
            breakdown[key].completion_tokens += record.completion_tokens
            breakdown[key].total_tokens += record.total_tokens
            breakdown[key].request_count += 1

        return breakdown

    def reset(self) -> None:
        """Reset all tracking data."""
        self._records.clear()
        self._totals = TokenUsage()
