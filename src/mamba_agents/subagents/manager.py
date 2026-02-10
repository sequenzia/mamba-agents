"""Top-level SubagentManager facade for the subagents subsystem.

Composes spawner, delegation, loader, and config management behind a
single unified API. Follows the ``MCPClientManager`` pattern for lifecycle
management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mamba_agents.subagents.config import DelegationHandle, SubagentConfig, SubagentResult
from mamba_agents.subagents.delegation import delegate, delegate_async, delegate_sync
from mamba_agents.subagents.errors import SubagentConfigError, SubagentNotFoundError
from mamba_agents.subagents.loader import discover_subagents
from mamba_agents.subagents.spawner import spawn
from mamba_agents.tokens.tracker import TokenUsage

if TYPE_CHECKING:
    from mamba_agents.agent.core import Agent
    from mamba_agents.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


class SubagentManager:
    """Facade for the subagent subsystem.

    Composes all subagent components (spawner, delegation, loader)
    behind a single API. Provides the primary interface for registering,
    delegating to, and tracking subagents.

    Follows the ``MCPClientManager`` pattern: create an instance with
    a parent agent and optional configs, then call methods to interact
    with the subsystem.

    Example::

        manager = SubagentManager(parent_agent)
        manager.register(SubagentConfig(name="helper", description="Helps"))
        result = manager.delegate_sync("helper", "Summarize this document")

    Args:
        parent_agent: The parent agent that owns this manager.
        configs: Optional list of initial subagent configurations to register.
        skill_registry: Optional SkillRegistry for skill pre-loading in subagents.
    """

    def __init__(
        self,
        parent_agent: Agent[Any, Any],
        configs: list[SubagentConfig] | None = None,
        skill_registry: SkillRegistry | None = None,
    ) -> None:
        """Initialize the SubagentManager.

        Registers any provided configs and stores the parent agent
        reference for spawning subagents.

        Args:
            parent_agent: The parent agent that owns this manager.
            configs: Optional list of initial subagent configurations to register.
            skill_registry: Optional SkillRegistry for skill pre-loading in subagents.

        Raises:
            SubagentConfigError: If any provided config fails validation.
        """
        self._parent_agent = parent_agent
        self._skill_registry = skill_registry
        self._configs: dict[str, SubagentConfig] = {}
        self._active_handles: list[DelegationHandle] = []
        self._usage_breakdown: dict[str, TokenUsage] = {}

        # Register initial configs
        if configs:
            for config in configs:
                self.register(config)

    # ------------------------------------------------------------------
    # Config Management
    # ------------------------------------------------------------------

    def register(self, config: SubagentConfig) -> None:
        """Register a subagent configuration.

        Validates the config and stores it for later delegation. If a config
        with the same name already exists, it is overwritten.

        Args:
            config: The subagent configuration to register.

        Raises:
            SubagentConfigError: If the config fails validation (e.g., missing
                required fields).
        """
        # Pydantic validation happens at SubagentConfig construction time.
        # Additional validation: ensure name is not empty/whitespace.
        if not config.name or not config.name.strip():
            raise SubagentConfigError(
                name="<empty>",
                detail="Subagent config name must not be empty",
            )

        self._configs[config.name] = config
        logger.debug("Registered subagent config '%s'", config.name)

    def deregister(self, name: str) -> None:
        """Remove a subagent configuration by name.

        Args:
            name: The config name to remove.

        Raises:
            SubagentNotFoundError: If no config with that name exists.
        """
        if name not in self._configs:
            raise SubagentNotFoundError(
                config_name=name,
                available=list(self._configs.keys()),
            )

        del self._configs[name]
        logger.debug("Deregistered subagent config '%s'", name)

    def list(self) -> list[SubagentConfig]:
        """List all registered subagent configurations.

        Returns:
            List of all registered ``SubagentConfig`` instances.
        """
        return list(self._configs.values())

    def get(self, name: str) -> SubagentConfig | None:
        """Get a subagent configuration by name.

        Args:
            name: The config name to retrieve.

        Returns:
            The ``SubagentConfig`` if found, ``None`` otherwise.
        """
        return self._configs.get(name)

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    async def delegate(
        self,
        config_name: str,
        task: str,
        **kwargs: Any,
    ) -> SubagentResult:
        """Delegate a task to a registered subagent (async).

        Spawns a subagent from the named config, runs the task, and
        returns the result. Token usage is automatically aggregated
        to the parent agent's ``UsageTracker``.

        Args:
            config_name: Name of the registered subagent config.
            task: The task description to delegate.
            **kwargs: Additional keyword arguments passed to the delegation
                function (e.g., ``context``, ``context_messages``).

        Returns:
            SubagentResult with output, usage, duration, and success status.

        Raises:
            SubagentNotFoundError: If no config with that name is registered.
        """
        config = self._resolve_config(config_name)
        subagent = self._spawn(config)

        result = await delegate(
            subagent,
            task,
            subagent_name=config.name,
            **kwargs,
        )

        self._aggregate_usage(config.name, result)
        return result

    def delegate_sync(
        self,
        config_name: str,
        task: str,
        **kwargs: Any,
    ) -> SubagentResult:
        """Delegate a task to a registered subagent (sync wrapper).

        Synchronous convenience wrapper around the async ``delegate()``
        method. Uses ``delegate_sync`` from the delegation module.

        Args:
            config_name: Name of the registered subagent config.
            task: The task description to delegate.
            **kwargs: Additional keyword arguments passed to the delegation
                function (e.g., ``context``, ``context_messages``).

        Returns:
            SubagentResult with output, usage, duration, and success status.

        Raises:
            SubagentNotFoundError: If no config with that name is registered.
        """
        config = self._resolve_config(config_name)
        subagent = self._spawn(config)

        result = delegate_sync(
            subagent,
            task,
            subagent_name=config.name,
            **kwargs,
        )

        self._aggregate_usage(config.name, result)
        return result

    async def delegate_async(
        self,
        config_name: str,
        task: str,
        **kwargs: Any,
    ) -> DelegationHandle:
        """Delegate a task to a registered subagent asynchronously.

        Returns a ``DelegationHandle`` immediately while the subagent
        runs in the background. Token usage is aggregated when the
        handle's result is awaited via the returned wrapped handle.

        Args:
            config_name: Name of the registered subagent config.
            task: The task description to delegate.
            **kwargs: Additional keyword arguments passed to the delegation
                function (e.g., ``context``, ``context_messages``).

        Returns:
            DelegationHandle for tracking and awaiting the result.

        Raises:
            SubagentNotFoundError: If no config with that name is registered.
        """
        config = self._resolve_config(config_name)
        subagent = self._spawn(config)

        handle = await delegate_async(
            subagent,
            task,
            subagent_name=config.name,
            **kwargs,
        )

        # Wrap the handle to aggregate usage on completion
        wrapped_handle = _UsageTrackingHandle(
            handle=handle,
            manager=self,
            config_name=config.name,
        )

        self._active_handles.append(wrapped_handle)
        return wrapped_handle

    async def spawn_dynamic(
        self,
        config: SubagentConfig,
        task: str,
        **kwargs: Any,
    ) -> SubagentResult:
        """Spawn a one-off subagent from a runtime config and run a task.

        Creates an ad-hoc subagent without registering the config. This
        allows dynamic subagent creation at runtime. The config name may
        conflict with a registered name -- the registered config is not
        affected.

        Args:
            config: A ``SubagentConfig`` to use for this delegation.
            task: The task description to delegate.
            **kwargs: Additional keyword arguments passed to the delegation
                function (e.g., ``context``, ``context_messages``).

        Returns:
            SubagentResult with output, usage, duration, and success status.
        """
        subagent = self._spawn(config)

        result = await delegate(
            subagent,
            task,
            subagent_name=config.name,
            **kwargs,
        )

        self._aggregate_usage(config.name, result)
        return result

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def get_active_delegations(self) -> list[DelegationHandle]:
        """Get all active (incomplete) async delegation handles.

        Prunes completed handles from the internal tracking list and
        returns only those still in progress.

        Returns:
            List of active ``DelegationHandle`` instances.
        """
        # Prune completed handles
        self._active_handles = [h for h in self._active_handles if not h.is_complete]
        return list(self._active_handles)

    def get_usage_breakdown(self) -> dict[str, TokenUsage]:
        """Get per-subagent token usage breakdown.

        Returns a dictionary mapping subagent names to their aggregate
        token usage from all delegations through this manager.

        Returns:
            Dictionary mapping subagent names to ``TokenUsage``.
        """
        return dict(self._usage_breakdown)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> list[SubagentConfig]:
        """Discover and register subagent configs from standard directories.

        Scans ``.mamba/agents/`` in the project directory and
        ``~/.mamba/agents/`` in the user home directory for markdown
        config files. Discovered configs are merged with programmatically
        registered configs. Existing configs with the same name are not
        overwritten.

        Returns:
            List of newly discovered ``SubagentConfig`` instances.
        """
        try:
            discovered = discover_subagents()
        except Exception:
            logger.exception("Subagent discovery failed")
            return []

        newly_registered: list[SubagentConfig] = []
        for config in discovered:
            if config.name in self._configs:
                logger.debug(
                    "Subagent config '%s' already registered, skipping duplicate",
                    config.name,
                )
                continue

            try:
                self._configs[config.name] = config
                newly_registered.append(config)
            except Exception:
                logger.exception(
                    "Failed to register discovered subagent config '%s'",
                    config.name,
                )

        return newly_registered

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_config(self, config_name: str) -> SubagentConfig:
        """Resolve a config by name, raising if not found.

        Args:
            config_name: Name of the registered config.

        Returns:
            The resolved ``SubagentConfig``.

        Raises:
            SubagentNotFoundError: If no config with that name exists.
        """
        config = self._configs.get(config_name)
        if config is None:
            raise SubagentNotFoundError(
                config_name=config_name,
                available=list(self._configs.keys()),
            )
        return config

    def _spawn(self, config: SubagentConfig) -> Agent[Any, Any]:
        """Spawn a subagent from a config.

        Args:
            config: The subagent configuration.

        Returns:
            A configured ``Agent`` instance.
        """
        return spawn(config, self._parent_agent, skill_registry=self._skill_registry)

    def _aggregate_usage(self, config_name: str, result: SubagentResult) -> None:
        """Aggregate subagent token usage to parent tracker and internal breakdown.

        Args:
            config_name: Name of the subagent config.
            result: The delegation result with usage data.
        """
        usage = result.usage

        # Aggregate to parent's UsageTracker with source tag
        if usage.total_tokens > 0 or usage.request_count > 0:
            self._parent_agent.usage_tracker.record_raw(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                model=self._parent_agent.model_name,
                tool_name=None,
            )

            # Also record with source for per-subagent tracking on parent
            # Use record_usage-style aggregation to _subagent_totals
            if config_name not in self._parent_agent.usage_tracker._subagent_totals:
                self._parent_agent.usage_tracker._subagent_totals[config_name] = TokenUsage()
            sub = self._parent_agent.usage_tracker._subagent_totals[config_name]
            sub.prompt_tokens += usage.prompt_tokens
            sub.completion_tokens += usage.completion_tokens
            sub.total_tokens += usage.total_tokens
            sub.request_count += usage.request_count

        # Update internal per-subagent breakdown
        if config_name not in self._usage_breakdown:
            self._usage_breakdown[config_name] = TokenUsage()

        breakdown = self._usage_breakdown[config_name]
        breakdown.prompt_tokens += usage.prompt_tokens
        breakdown.completion_tokens += usage.completion_tokens
        breakdown.total_tokens += usage.total_tokens
        breakdown.request_count += usage.request_count

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return a string representation of the manager."""
        count = len(self._configs)
        active = len(self.get_active_delegations())
        return f"SubagentManager(configs={count}, active_delegations={active})"

    def __len__(self) -> int:
        """Return the number of registered configs."""
        return len(self._configs)


class _UsageTrackingHandle(DelegationHandle):
    """A DelegationHandle wrapper that aggregates usage on completion.

    Wraps an underlying ``DelegationHandle`` to automatically aggregate
    token usage to the parent manager when the result is awaited.
    """

    def __init__(
        self,
        handle: DelegationHandle,
        manager: SubagentManager,
        config_name: str,
    ) -> None:
        """Initialize the usage tracking handle.

        Args:
            handle: The underlying delegation handle.
            manager: The manager for usage aggregation.
            config_name: The config name for tracking.
        """
        # Initialize DelegationHandle fields from the wrapped handle
        super().__init__(
            subagent_name=handle.subagent_name,
            task=handle.task,
            _task=handle._task,
        )
        self._manager = manager
        self._config_name = config_name
        self._usage_aggregated = False

    async def result(self) -> SubagentResult:
        """Await the delegation result and aggregate usage.

        Returns:
            The SubagentResult from the completed subagent.

        Raises:
            asyncio.CancelledError: If the task was cancelled.
            RuntimeError: If no task is associated with this handle.
        """
        sub_result = await super().result()

        # Aggregate usage only once
        if not self._usage_aggregated:
            self._manager._aggregate_usage(self._config_name, sub_result)
            self._usage_aggregated = True

        return sub_result
