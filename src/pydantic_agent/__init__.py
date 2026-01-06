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

from pydantic_agent.agent.core import Agent
from pydantic_agent.agent.config import AgentConfig
from pydantic_agent.agent.result import AgentResult
from pydantic_agent.config.settings import AgentSettings

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentResult",
    "AgentSettings",
]

__version__ = "0.1.0"
