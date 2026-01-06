"""Cost estimation for token usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_agent.tokens.tracker import TokenUsage


# Default cost rates per 1000 tokens (USD)
DEFAULT_COST_RATES = {
    # OpenAI models
    "gpt-4": 0.03,
    "gpt-4-turbo": 0.01,
    "gpt-3.5-turbo": 0.002,
    # Anthropic models
    "claude-3-opus": 0.015,
    "claude-3-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    # Local models (typically free)
    "llama": 0.0,
    "mistral": 0.0,
    "ollama": 0.0,
    # Default fallback
    "default": 0.001,
}


@dataclass
class CostBreakdown:
    """Cost breakdown by category.

    Attributes:
        prompt_cost: Cost for prompt tokens.
        completion_cost: Cost for completion tokens.
        total_cost: Total cost.
        model: Model used for calculation.
    """

    prompt_cost: float
    completion_cost: float
    total_cost: float
    model: str | None = None


class CostEstimator:
    """Estimate costs based on token usage.

    Provides cost estimation for various models with configurable rates.
    """

    def __init__(
        self,
        custom_rates: dict[str, float] | None = None,
    ) -> None:
        """Initialize the cost estimator.

        Args:
            custom_rates: Custom cost rates per 1000 tokens.
                          Overrides defaults for specified models.
        """
        self._rates = DEFAULT_COST_RATES.copy()
        if custom_rates:
            self._rates.update(custom_rates)

    def get_rate(self, model: str) -> float:
        """Get the cost rate for a model.

        Args:
            model: Model name or identifier.

        Returns:
            Cost per 1000 tokens.
        """
        # Check exact match
        if model in self._rates:
            return self._rates[model]

        # Check prefix match
        model_lower = model.lower()
        for key, rate in self._rates.items():
            if key.lower() in model_lower:
                return rate

        # Return default
        return self._rates.get("default", 0.0)

    def estimate(
        self,
        usage: "TokenUsage",
        model: str | None = None,
    ) -> CostBreakdown:
        """Estimate cost for token usage.

        Args:
            usage: Token usage to estimate cost for.
            model: Model to use for rate lookup.

        Returns:
            CostBreakdown with detailed costs.
        """
        rate = self.get_rate(model or "default")

        prompt_cost = (usage.prompt_tokens / 1000) * rate
        completion_cost = (usage.completion_tokens / 1000) * rate
        total_cost = prompt_cost + completion_cost

        return CostBreakdown(
            prompt_cost=prompt_cost,
            completion_cost=completion_cost,
            total_cost=total_cost,
            model=model,
        )

    def estimate_tokens(
        self,
        token_count: int,
        model: str | None = None,
    ) -> float:
        """Estimate cost for a token count.

        Args:
            token_count: Number of tokens.
            model: Model to use for rate lookup.

        Returns:
            Estimated cost in USD.
        """
        rate = self.get_rate(model or "default")
        return (token_count / 1000) * rate

    def set_rate(self, model: str, rate: float) -> None:
        """Set a custom rate for a model.

        Args:
            model: Model name.
            rate: Cost per 1000 tokens.
        """
        self._rates[model] = rate

    def get_all_rates(self) -> dict[str, float]:
        """Get all configured rates.

        Returns:
            Dictionary of model names to rates.
        """
        return self._rates.copy()
