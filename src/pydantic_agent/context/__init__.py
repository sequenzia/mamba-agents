"""Context window management."""

from pydantic_agent.context.compaction.base import CompactionResult, CompactionStrategy
from pydantic_agent.context.compaction.hybrid import HybridStrategy
from pydantic_agent.context.compaction.importance import ImportanceScoringStrategy
from pydantic_agent.context.compaction.selective import SelectivePruningStrategy
from pydantic_agent.context.compaction.sliding_window import SlidingWindowStrategy
from pydantic_agent.context.compaction.summarize import SummarizeOlderStrategy
from pydantic_agent.context.config import CompactionConfig
from pydantic_agent.context.history import MessageHistory
from pydantic_agent.context.manager import ContextManager, ContextState

__all__ = [
    "ContextManager",
    "ContextState",
    "MessageHistory",
    "CompactionConfig",
    "CompactionStrategy",
    "CompactionResult",
    "SlidingWindowStrategy",
    "SummarizeOlderStrategy",
    "SelectivePruningStrategy",
    "ImportanceScoringStrategy",
    "HybridStrategy",
]
