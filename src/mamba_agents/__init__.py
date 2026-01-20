"""
Mamba Agents - A simple, extensible AI Agent framework built on pydantic-ai.

This framework provides:
- Simple tool-calling agent loop
- Built-in tools for filesystem, glob, grep, and bash operations
- MCP server integration
- Token management with tiktoken
- Context window management with compaction strategies
- Prompt template management with Jinja2
- Comprehensive observability and error handling

Essential imports:
    from mamba_agents import Agent, AgentConfig, AgentSettings

For submodule-specific imports (alternative to main exports):
    from mamba_agents.tokens import TokenUsage, UsageRecord, CostBreakdown
    from mamba_agents.prompts import PromptManager, PromptTemplate, PromptConfig, TemplateConfig
    from mamba_agents.mcp import MCPClientManager, MCPServerConfig, MCPAuthConfig
    from mamba_agents.workflows import Workflow, WorkflowConfig, WorkflowHooks, ...
"""

# Core agent exports
from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.core import Agent
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
    "MCPAuthConfig",
    "MCPClientManager",
    "MCPServerConfig",
    "PromptConfig",
    "PromptManager",
    "PromptTemplate",
    "TemplateConfig",
    "TokenUsage",
    "UsageRecord",
    "Workflow",
    "WorkflowConfig",
    "WorkflowHooks",
    "WorkflowResult",
    "WorkflowState",
    "WorkflowStep",
    "__version__",
]

# Version is dynamically set by hatch-vcs during build
try:
    from mamba_agents._version import __version__
except ImportError:
    __version__ = "0.0.0.dev0"
