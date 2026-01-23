"""Context window management.

Provides automatic tracking and compaction of conversation history
to stay within model context limits.

Compaction Strategies:
    - sliding_window: Remove oldest messages beyond threshold
    - summarize_older: LLM-based summarization of older messages
    - selective_pruning: Remove completed tool call/result pairs
    - importance_scoring: LLM-based scoring, prune lowest importance
    - hybrid: Combine multiple strategies in sequence

Built into Agent (Recommended):
    >>> from mamba_agents import Agent, AgentConfig, CompactionConfig
    >>> config = AgentConfig(
    ...     track_context=True,  # Default
    ...     auto_compact=True,   # Default
    ...     context=CompactionConfig(
    ...         strategy="hybrid",
    ...         trigger_threshold_tokens=50000,
    ...     ),
    ... )
    >>> agent = Agent("gpt-4o", config=config)
    >>> state = agent.get_context_state()
    >>> print(f"Messages: {state.message_count}, Tokens: {state.token_count}")

Standalone Usage:
    >>> from mamba_agents.context import ContextManager, CompactionConfig
    >>> config = CompactionConfig(strategy="sliding_window")
    >>> manager = ContextManager(config=config)
    >>> manager.add_messages([...])
    >>> if manager.should_compact():
    ...     result = await manager.compact()

See Also:
    - examples/advanced/context_compaction.py for runnable example
    - docs/user-guide/context-management.md for detailed guide
"""

from mamba_agents.context.compaction.base import CompactionResult, CompactionStrategy
from mamba_agents.context.compaction.hybrid import HybridStrategy
from mamba_agents.context.compaction.importance import ImportanceScoringStrategy
from mamba_agents.context.compaction.selective import SelectivePruningStrategy
from mamba_agents.context.compaction.sliding_window import SlidingWindowStrategy
from mamba_agents.context.compaction.summarize import SummarizeOlderStrategy
from mamba_agents.context.config import CompactionConfig
from mamba_agents.context.history import MessageHistory
from mamba_agents.context.manager import ContextManager, ContextState

__all__ = [
    "CompactionConfig",
    "CompactionResult",
    "CompactionStrategy",
    "ContextManager",
    "ContextState",
    "HybridStrategy",
    "ImportanceScoringStrategy",
    "MessageHistory",
    "SelectivePruningStrategy",
    "SlidingWindowStrategy",
    "SummarizeOlderStrategy",
]
