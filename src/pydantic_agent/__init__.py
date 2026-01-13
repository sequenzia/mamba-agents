"""
Pydantic Agent - A simple, extensible AI Agent framework built on pydantic-ai.

This framework provides:
- Simple tool-calling agent loop
- Built-in tools for filesystem, glob, grep, and bash operations
- MCP server integration
- Token management with tiktoken
- Context window management with compaction strategies
- Comprehensive observability and error handling
"""

from pydantic_agent.agent.config import AgentConfig
from pydantic_agent.agent.core import Agent
from pydantic_agent.agent.result import AgentResult
from pydantic_agent.config.settings import AgentSettings
from pydantic_agent.context import ContextState
from pydantic_agent.context.compaction import CompactionResult
from pydantic_agent.context.config import CompactionConfig
from pydantic_agent.tokens.cost import CostBreakdown
from pydantic_agent.tokens.tracker import TokenUsage, UsageRecord

__all__ = [
    # Core
    "Agent",
    "AgentConfig",
    "AgentResult",
    "AgentSettings",
    # Context management
    "CompactionConfig",
    "CompactionResult",
    "ContextState",
    # Token tracking
    "CostBreakdown",
    "TokenUsage",
    "UsageRecord",
]

__version__ = "0.1.0"
