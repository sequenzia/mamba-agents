"""Core agent module.

The Agent class wraps pydantic-ai with enterprise features:
- Automatic context tracking across conversations
- Token counting and cost estimation
- Auto-compaction when context threshold reached
- Graceful tool error handling (v0.1.2+)

Basic Usage:
    >>> from mamba_agents import Agent
    >>> agent = Agent("gpt-4o")
    >>> result = agent.run_sync("Hello!")
    >>> print(result.output)

Multi-turn Conversations:
    >>> agent.run_sync("My name is Alice")
    >>> result = agent.run_sync("What's my name?")
    >>> print(result.output)  # Alice

With Tools:
    >>> from mamba_agents.tools import read_file, run_bash
    >>> agent = Agent("gpt-4o", tools=[read_file, run_bash])

Custom Configuration:
    >>> from mamba_agents import Agent, AgentConfig
    >>> config = AgentConfig(
    ...     system_prompt="You are a Python expert.",
    ...     max_iterations=15,
    ...     graceful_tool_errors=True,  # Default
    ... )
    >>> agent = Agent("gpt-4o", config=config)

Classes:
    Agent: Main agent class wrapping pydantic-ai
    AgentConfig: Configuration options
    AgentResult: Wrapper around pydantic-ai RunResult

Utilities:
    dicts_to_model_messages: Convert dicts to pydantic-ai messages
    model_messages_to_dicts: Convert pydantic-ai messages to dicts

See Also:
    - examples/basic/ for runnable examples
    - docs/user-guide/agent-basics.md for detailed guide
"""

from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.core import Agent
from mamba_agents.agent.message_utils import dicts_to_model_messages, model_messages_to_dicts
from mamba_agents.agent.messages import MessageQuery, MessageStats, ToolCallInfo, Turn
from mamba_agents.agent.result import AgentResult

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentResult",
    "MessageQuery",
    "MessageStats",
    "ToolCallInfo",
    "Turn",
    "dicts_to_model_messages",
    "model_messages_to_dicts",
]
