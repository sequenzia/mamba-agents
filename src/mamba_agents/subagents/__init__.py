"""Subagents subsystem for task delegation.

Provides configuration, spawning, and delegation of subagents for isolated
task execution within a parent agent context. The ``SubagentManager`` facade
composes all subsystem components behind a single unified API.

Quick Start:
    >>> from mamba_agents.subagents import SubagentManager, SubagentConfig
    >>> config = SubagentConfig(name="researcher", description="Research tasks")
    >>> manager = SubagentManager(parent_agent=agent)
    >>> manager.register(config)
    >>> result = manager.delegate_sync("researcher", "Summarize this article")

Classes:
    SubagentManager: Top-level facade for the subagents subsystem.
    SubagentConfig: Configuration for a subagent definition.
    SubagentResult: Result from a completed subagent delegation.
    DelegationHandle: Handle for tracking async subagent delegation.

Exceptions:
    SubagentError: Base exception for all subagent-related errors.
    SubagentConfigError: Subagent configuration is invalid.
    SubagentNotFoundError: Referenced subagent config was not found.
    SubagentNestingError: Subagent attempted to spawn a sub-subagent.
    SubagentDelegationError: Error during task delegation.
    SubagentTimeoutError: Subagent exceeded maximum allowed turns.
"""

from __future__ import annotations

from mamba_agents.subagents.config import (
    DelegationHandle,
    SubagentConfig,
    SubagentResult,
)
from mamba_agents.subagents.errors import (
    SubagentConfigError,
    SubagentDelegationError,
    SubagentError,
    SubagentNestingError,
    SubagentNotFoundError,
    SubagentTimeoutError,
)
from mamba_agents.subagents.manager import SubagentManager

__all__ = [
    "DelegationHandle",
    "SubagentConfig",
    "SubagentConfigError",
    "SubagentDelegationError",
    "SubagentError",
    "SubagentManager",
    "SubagentNestingError",
    "SubagentNotFoundError",
    "SubagentResult",
    "SubagentTimeoutError",
]
