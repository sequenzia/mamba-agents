"""
Mamba Agents - A simple, extensible AI Agent framework built on pydantic-ai.

Quick Start:
    >>> from mamba_agents import Agent
    >>> agent = Agent("gpt-4o")
    >>> result = agent.run_sync("What is 2 + 2?")
    >>> print(result.output)
    4

With Settings:
    >>> from mamba_agents import Agent, AgentSettings
    >>> settings = AgentSettings()  # Loads from env, .env, config files
    >>> agent = Agent("gpt-4o", settings=settings)
    >>> result = agent.run_sync("Hello!")

With Tools:
    >>> from mamba_agents import Agent
    >>> from mamba_agents.tools import read_file, run_bash
    >>> agent = Agent("gpt-4o", tools=[read_file, run_bash])

Key Features:
    - Context tracking with auto-compaction (5 strategies)
    - Token counting and cost estimation
    - MCP server integration (stdio, SSE, Streamable HTTP)
    - Jinja2 prompt templates with versioning
    - ReAct workflow for multi-step reasoning
    - Graceful tool error handling (v0.1.2+)

See Also:
    - examples/ directory for runnable scripts
    - https://sequenzia.github.io/mamba-agents for documentation
"""

# Core agent exports
from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.core import Agent
from mamba_agents.agent.display import (
    DisplayPreset,
    HtmlRenderer,
    MessageRenderer,
    PlainTextRenderer,
    RichRenderer,
    print_stats,
    print_timeline,
    print_tools,
)
from mamba_agents.agent.messages import MessageQuery, MessageStats, ToolCallInfo, Turn
from mamba_agents.agent.result import AgentResult
from mamba_agents.config.settings import AgentSettings

# Context management
from mamba_agents.context import ContextState
from mamba_agents.context.compaction import CompactionResult
from mamba_agents.context.config import CompactionConfig

# MCP integration
from mamba_agents.mcp import MCPAuthConfig, MCPClientManager, MCPServerConfig

# Prompt management
from mamba_agents.prompts import PromptConfig, PromptManager, PromptTemplate, TemplateConfig

# Skills subsystem
from mamba_agents.skills import (
    Skill,
    SkillConfig,
    SkillConflictError,
    SkillError,
    SkillInfo,
    SkillLoadError,
    SkillManager,
    SkillNotFoundError,
    SkillParseError,
    SkillScope,
    SkillValidationError,
    TrustLevel,
    ValidationResult,
)

# Subagents subsystem
from mamba_agents.subagents import (
    DelegationHandle,
    SubagentConfig,
    SubagentConfigError,
    SubagentDelegationError,
    SubagentError,
    SubagentManager,
    SubagentNestingError,
    SubagentNotFoundError,
    SubagentResult,
    SubagentTimeoutError,
)

# Token tracking
from mamba_agents.tokens.cost import CostBreakdown
from mamba_agents.tokens.tracker import TokenUsage, UsageRecord

# Workflow orchestration
from mamba_agents.workflows import (
    Workflow,
    WorkflowConfig,
    WorkflowHooks,
    WorkflowResult,
    WorkflowState,
    WorkflowStep,
)

__all__ = [
    "Agent",
    "AgentConfig",
    "AgentResult",
    "AgentSettings",
    "CompactionConfig",
    "CompactionResult",
    "ContextState",
    "CostBreakdown",
    "DelegationHandle",
    "DisplayPreset",
    "HtmlRenderer",
    "MCPAuthConfig",
    "MCPClientManager",
    "MCPServerConfig",
    "MessageQuery",
    "MessageRenderer",
    "MessageStats",
    "PlainTextRenderer",
    "PromptConfig",
    "PromptManager",
    "PromptTemplate",
    "RichRenderer",
    "Skill",
    "SkillConfig",
    "SkillConflictError",
    "SkillError",
    "SkillInfo",
    "SkillLoadError",
    "SkillManager",
    "SkillNotFoundError",
    "SkillParseError",
    "SkillScope",
    "SkillValidationError",
    "SubagentConfig",
    "SubagentConfigError",
    "SubagentDelegationError",
    "SubagentError",
    "SubagentManager",
    "SubagentNestingError",
    "SubagentNotFoundError",
    "SubagentResult",
    "SubagentTimeoutError",
    "TemplateConfig",
    "TokenUsage",
    "ToolCallInfo",
    "TrustLevel",
    "Turn",
    "UsageRecord",
    "ValidationResult",
    "Workflow",
    "WorkflowConfig",
    "WorkflowHooks",
    "WorkflowResult",
    "WorkflowState",
    "WorkflowStep",
    "__version__",
    "print_stats",
    "print_timeline",
    "print_tools",
]

# Version is dynamically set by hatch-vcs during build
try:
    from mamba_agents._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"
