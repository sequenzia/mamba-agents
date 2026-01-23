"""Token management and tracking.

Provides token counting, usage tracking, and cost estimation
using tiktoken for accurate counts.

Built into Agent (Recommended):
    >>> from mamba_agents import Agent
    >>> agent = Agent("gpt-4o")
    >>> agent.run_sync("Hello!")
    >>> print(f"Tokens: {agent.get_usage().total_tokens}")
    >>> print(f"Cost: ${agent.get_cost():.4f}")
    >>> breakdown = agent.get_cost_breakdown()
    >>> print(f"Prompt: ${breakdown.prompt_cost:.4f}")

Standalone Usage:
    >>> from mamba_agents.tokens import TokenCounter, UsageTracker, CostEstimator
    >>> counter = TokenCounter(encoding="cl100k_base")
    >>> count = counter.count("Hello, world!")
    >>> tracker = UsageTracker()
    >>> tracker.record_usage(input_tokens=100, output_tokens=50, model="gpt-4o")
    >>> cost = CostEstimator().estimate(input_tokens=1000, output_tokens=500)

See Also:
    - examples/advanced/token_tracking.py for runnable example
    - docs/user-guide/token-tracking.md for detailed guide
"""

from mamba_agents.tokens.config import TokenizerConfig
from mamba_agents.tokens.cost import CostEstimator
from mamba_agents.tokens.counter import TokenCounter
from mamba_agents.tokens.tracker import UsageTracker

__all__ = ["CostEstimator", "TokenCounter", "TokenizerConfig", "UsageTracker"]
