"""Core Agent class wrapping pydantic-ai."""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import AsyncIterator, Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import ModelRetry
from pydantic_ai.models import Model
from pydantic_ai.toolsets import AbstractToolset

from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.message_utils import dicts_to_model_messages, model_messages_to_dicts
from mamba_agents.agent.messages import MessageQuery
from mamba_agents.agent.result import AgentResult
from mamba_agents.config.settings import AgentSettings
from mamba_agents.context import ContextManager, ContextState
from mamba_agents.context.compaction import CompactionResult
from mamba_agents.prompts.config import TemplateConfig
from mamba_agents.tokens import CostEstimator, TokenCounter, UsageTracker
from mamba_agents.tokens.cost import CostBreakdown
from mamba_agents.tokens.tracker import TokenUsage, UsageRecord

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.result import StreamedRunResult
    from pydantic_ai.tools import ToolDefinition
    from pydantic_ai.usage import UsageLimits

    from mamba_agents.prompts import PromptManager
    from mamba_agents.skills import Skill, SkillInfo, SkillManager
    from mamba_agents.subagents import (
        DelegationHandle,
        SubagentConfig,
        SubagentManager,
        SubagentResult,
    )


DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


class Agent[DepsT, OutputT]:
    """AI Agent with tool-calling capabilities.

    This is a thin wrapper around pydantic-ai's Agent class that adds:
    - Configuration via AgentSettings
    - Context management and compaction
    - Token usage tracking
    - Prompt template support
    - Enhanced observability

    Example:
        >>> from mamba_agents import Agent
        >>>
        >>> # Option 1: String prompt (backward compatible)
        >>> agent = Agent(
        ...     "openai:gpt-4",
        ...     system_prompt="You are a helpful assistant.",
        ... )
        >>>
        >>> # Option 2: Template config
        >>> from mamba_agents.prompts import TemplateConfig
        >>> agent = Agent(
        ...     "openai:gpt-4",
        ...     system_prompt=TemplateConfig(
        ...         name="system/assistant",
        ...         variables={"name": "Code Helper"}
        ...     )
        ... )
        >>>
        >>> result = await agent.run("Hello, world!")
        >>> print(result.output)
    """

    def __init__(
        self,
        model: str | Model | None = None,
        *,
        tools: Sequence[Callable[..., Any] | ToolDefinition] | None = None,
        toolsets: Sequence[AbstractToolset[DepsT]] | None = None,
        system_prompt: str | TemplateConfig = "",
        deps_type: type[DepsT] | None = None,
        output_type: type[OutputT] | None = None,
        config: AgentConfig | None = None,
        settings: AgentSettings | None = None,
        prompt_manager: PromptManager | None = None,
        skills: list[Skill | str | Path] | None = None,
        skill_dirs: list[str | Path] | None = None,
        subagents: list[SubagentConfig] | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            model: Model to use (string identifier or Model instance).
                If not provided, uses settings.model_backend configuration.
            tools: Optional list of tools to register.
            toolsets: Optional list of toolsets (e.g., MCP servers) to use.
                MCP servers should be passed here, not via tools parameter.
            system_prompt: System prompt for the agent. Can be a string or TemplateConfig.
            deps_type: Type of dependencies for tool calls.
            output_type: Expected output type.
            config: Agent execution configuration.
            settings: Full agent settings (for model backend, etc.).
            prompt_manager: Optional PromptManager for template resolution.
            skills: Optional list of skills to register. Each item can be a
                ``Skill`` instance, a string path, or a ``Path`` to a skill directory.
            skill_dirs: Optional list of directories to scan for skills.
            subagents: Optional list of subagent configurations to register.

        Raises:
            ValueError: If neither model nor settings is provided.
        """
        self._config = config or AgentConfig(system_prompt=system_prompt)
        self._settings = settings or AgentSettings()
        self._prompt_manager = prompt_manager

        # Determine model name and whether to use settings for connection config
        if model is None:
            if settings is None:
                raise ValueError("Either 'model' or 'settings' must be provided")
            model_name: str | None = self._settings.model_backend.model
        elif isinstance(model, str):
            model_name = model
        else:
            # model is already a Model instance
            model_name = None

        # Construct model using settings connection config when applicable
        if model_name is not None and settings is not None:
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            model = OpenAIChatModel(
                model_name,
                provider=OpenAIProvider(
                    base_url=self._settings.model_backend.base_url,
                    api_key=(
                        self._settings.model_backend.api_key.get_secret_value()
                        if self._settings.model_backend.api_key
                        else None
                    ),
                ),
            )

        # Resolve system prompt from template if needed
        self._resolved_system_prompt = self._resolve_system_prompt(self._config.system_prompt)

        # Create the underlying pydantic-ai agent
        agent_kwargs: dict[str, Any] = {
            "system_prompt": self._resolved_system_prompt,
        }

        if tools:
            if self._config.graceful_tool_errors:
                agent_kwargs["tools"] = [self._wrap_tool_with_graceful_errors(t) for t in tools]
            else:
                agent_kwargs["tools"] = list(tools)

        if toolsets:
            agent_kwargs["toolsets"] = list(toolsets)

        if deps_type:
            agent_kwargs["deps_type"] = deps_type

        if output_type:
            agent_kwargs["output_type"] = output_type

        self._agent: PydanticAgent[DepsT, OutputT] = PydanticAgent(model, **agent_kwargs)

        # Store model name for cost estimation
        self._model_name = model_name

        # Initialize token tracking (always on)
        tokenizer_cfg = self._config.tokenizer or self._settings.tokenizer
        self._token_counter = TokenCounter(config=tokenizer_cfg)
        self._usage_tracker = UsageTracker(cost_rates=self._settings.cost_rates)
        self._cost_estimator = CostEstimator(custom_rates=self._settings.cost_rates)

        # Initialize context manager (if enabled)
        if self._config.track_context:
            context_cfg = self._config.context or self._settings.context
            self._context_manager: ContextManager | None = ContextManager(
                config=context_cfg,
                token_counter=self._token_counter,
            )
            if self._resolved_system_prompt:
                self._context_manager.set_system_prompt(self._resolved_system_prompt)
        else:
            self._context_manager = None

        # Initialize skill manager (explicit via init_skills())
        self._skill_manager: SkillManager | None = None

        if skills is not None or skill_dirs is not None:
            self.init_skills(skills=skills, skill_dirs=skill_dirs)

        # Initialize subagent manager (explicit via init_subagents())
        self._subagent_manager: SubagentManager | None = None

        if subagents is not None:
            self.init_subagents(subagents=subagents)

    def _build_kwargs(self, **params: Any) -> dict[str, Any]:
        """Build kwargs dict, filtering out None values.

        Args:
            **params: Key-value pairs to include if not None.

        Returns:
            Dictionary with only non-None values.
        """
        return {k: v for k, v in params.items() if v is not None}

    def _ensure_context_enabled(self) -> ContextManager:
        """Ensure context tracking is enabled.

        Returns:
            The context manager instance.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        if self._context_manager is None:
            raise RuntimeError(
                "Context tracking is disabled. Enable with AgentConfig(track_context=True)"
            )
        return self._context_manager

    def _resolve_system_prompt(self, prompt: str | TemplateConfig) -> str:
        """Resolve a system prompt from string or template config.

        Args:
            prompt: String prompt or TemplateConfig.

        Returns:
            Resolved prompt string.
        """
        if isinstance(prompt, str):
            return prompt

        # Get or create prompt manager
        manager = self._get_prompt_manager()
        return manager.render_config(prompt)

    def _get_prompt_manager(self) -> PromptManager:
        """Get or create the prompt manager.

        Returns:
            PromptManager instance.
        """
        if self._prompt_manager is not None:
            return self._prompt_manager

        # Create from settings
        from mamba_agents.prompts import PromptManager

        self._prompt_manager = PromptManager(config=self._settings.prompts)
        return self._prompt_manager

    def _wrap_tool_with_graceful_errors(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap a tool function to convert exceptions to ModelRetry.

        This allows the LLM to receive error messages and potentially
        retry with different parameters instead of crashing the agent loop.

        Args:
            func: The tool function to wrap.

        Returns:
            Wrapped function that converts exceptions to ModelRetry.
        """
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except ModelRetry:
                    # Pass through ModelRetry unchanged (no double-wrapping)
                    raise
                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {exc}"
                    logger.debug(
                        "Tool %s raised %s, converting to ModelRetry",
                        func.__name__,
                        error_msg,
                    )
                    raise ModelRetry(error_msg) from exc

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except ModelRetry:
                    # Pass through ModelRetry unchanged (no double-wrapping)
                    raise
                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {exc}"
                    logger.debug(
                        "Tool %s raised %s, converting to ModelRetry",
                        func.__name__,
                        error_msg,
                    )
                    raise ModelRetry(error_msg) from exc

            return sync_wrapper

    @classmethod
    def from_settings(
        cls,
        settings: AgentSettings,
        *,
        tools: Sequence[Callable[..., Any] | ToolDefinition] | None = None,
        toolsets: Sequence[AbstractToolset[DepsT]] | None = None,
        system_prompt: str = "",
        deps_type: type[DepsT] | None = None,
        output_type: type[OutputT] | None = None,
    ) -> Agent[DepsT, OutputT]:
        """Create an agent from settings.

        This factory method creates an agent configured according to the
        provided settings, including model backend configuration.

        Args:
            settings: Agent settings to use.
            tools: Optional list of tools to register.
            toolsets: Optional list of toolsets (e.g., MCP servers) to use.
            system_prompt: System prompt for the agent.
            deps_type: Type of dependencies for tool calls.
            output_type: Expected output type.

        Returns:
            Configured Agent instance.
        """
        # Use OpenAI provider with custom base_url from settings
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        model = OpenAIChatModel(
            settings.model_backend.model,
            provider=OpenAIProvider(
                base_url=settings.model_backend.base_url,
                api_key=(
                    settings.model_backend.api_key.get_secret_value()
                    if settings.model_backend.api_key
                    else None
                ),
            ),
        )

        return cls(
            model,
            tools=tools,
            toolsets=toolsets,
            system_prompt=system_prompt,
            deps_type=deps_type,
            output_type=output_type,
            settings=settings,
        )

    def _do_post_run_tracking(self, result: AgentResult[OutputT]) -> bool:
        """Handle post-run tracking. Returns True if compaction needed.

        Args:
            result: The result from the run.

        Returns:
            True if compaction should be triggered, False otherwise.
        """
        self._usage_tracker.record_usage(result.usage(), model=self._model_name)
        if self._context_manager is not None:
            new_messages = model_messages_to_dicts(result.new_messages())
            self._context_manager.add_messages(new_messages)
            return self._config.auto_compact and self._context_manager.should_compact()
        return False

    async def _post_run_hook(self, result: AgentResult[OutputT]) -> None:
        """Handle post-run tracking and context management (async)."""
        if self._do_post_run_tracking(result) and self._context_manager:
            await self._context_manager.compact()

    def _resolve_message_history(
        self, message_history: list[ModelMessage] | None
    ) -> list[ModelMessage] | None:
        """Resolve message history from explicit input or internal context.

        Args:
            message_history: Explicit message history, or None to use internal context.

        Returns:
            Resolved message history, or None if no history available.
        """
        if message_history is not None:
            return message_history
        if self._context_manager is not None:
            internal_messages = self._context_manager.get_messages()
            if internal_messages:
                return dicts_to_model_messages(internal_messages)
        return None

    async def run(
        self,
        prompt: str,
        *,
        deps: DepsT | None = None,
        message_history: list[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> AgentResult[OutputT]:
        """Run the agent with the given prompt.

        Args:
            prompt: User prompt to process.
            deps: Optional dependencies for tool calls.
            message_history: Optional message history for context.
                If None and context tracking is enabled, uses internal context.
            usage_limits: Optional usage limits.

        Returns:
            AgentResult containing the output and metadata.
        """
        kwargs = self._build_kwargs(
            deps=deps,
            usage_limits=usage_limits,
            message_history=self._resolve_message_history(message_history),
        )

        result = await self._agent.run(prompt, **kwargs)
        wrapped_result = AgentResult(result)

        # Post-run tracking
        await self._post_run_hook(wrapped_result)

        return wrapped_result

    def _post_run_hook_sync(self, result: AgentResult[OutputT]) -> None:
        """Handle post-run tracking and context management (sync)."""
        if self._do_post_run_tracking(result) and self._context_manager:
            import asyncio

            asyncio.run(self._context_manager.compact())

    def run_sync(
        self,
        prompt: str,
        *,
        deps: DepsT | None = None,
        message_history: list[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> AgentResult[OutputT]:
        """Run the agent synchronously.

        Args:
            prompt: User prompt to process.
            deps: Optional dependencies for tool calls.
            message_history: Optional message history for context.
                If None and context tracking is enabled, uses internal context.
            usage_limits: Optional usage limits.

        Returns:
            AgentResult containing the output and metadata.
        """
        kwargs = self._build_kwargs(
            deps=deps,
            usage_limits=usage_limits,
            message_history=self._resolve_message_history(message_history),
        )

        result = self._agent.run_sync(prompt, **kwargs)
        wrapped_result = AgentResult(result)

        # Post-run tracking
        self._post_run_hook_sync(wrapped_result)

        return wrapped_result

    async def run_stream(
        self,
        prompt: str,
        *,
        deps: DepsT | None = None,
        message_history: list[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> AsyncIterator[StreamedRunResult[OutputT]]:
        """Run the agent with streaming output.

        Args:
            prompt: User prompt to process.
            deps: Optional dependencies for tool calls.
            message_history: Optional message history for context.
                If None and context tracking is enabled, uses internal context.
            usage_limits: Optional usage limits.

        Yields:
            StreamedRunResult with streaming response events.

        Note:
            Usage and context tracking occurs after the stream is consumed.
        """
        kwargs = self._build_kwargs(
            deps=deps,
            usage_limits=usage_limits,
            message_history=self._resolve_message_history(message_history),
        )

        async with self._agent.run_stream(prompt, **kwargs) as result:
            yield result
            # After stream is consumed and yield returns, track usage and messages
            self._usage_tracker.record_usage(result.usage(), model=self._model_name)
            if self._context_manager is not None:
                new_messages = model_messages_to_dicts(result.all_messages())
                self._context_manager.add_messages(new_messages)
                if self._config.auto_compact and self._context_manager.should_compact():
                    await self._context_manager.compact()

    def _register_tool(
        self,
        func: Callable[..., Any] | None,
        method: Callable[..., Any],
        name: str | None,
        description: str | None,
        retries: int | None,
        graceful_errors: bool | None,
    ) -> Callable[..., Any]:
        """Register a tool using the specified pydantic-ai method.

        Args:
            func: The tool function to register, or None for decorator usage.
            method: The pydantic-ai method to use (tool or tool_plain).
            name: Optional custom name for the tool.
            description: Optional description override.
            retries: Optional retry count override.
            graceful_errors: Whether to convert exceptions to ModelRetry.
                None uses the agent config setting.

        Returns:
            The decorated function or a decorator.
        """
        kwargs = self._build_kwargs(name=name, description=description, retries=retries)

        # Resolve effective graceful_errors setting: per-tool override > agent config
        effective_graceful = (
            graceful_errors if graceful_errors is not None else self._config.graceful_tool_errors
        )

        def apply_wrapper(f: Callable[..., Any]) -> Callable[..., Any]:
            wrapped = self._wrap_tool_with_graceful_errors(f) if effective_graceful else f
            return method(**kwargs)(wrapped)

        if func is not None:
            return apply_wrapper(func)

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            return apply_wrapper(f)

        return decorator

    def tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        retries: int | None = None,
        graceful_errors: bool | None = None,
    ) -> Callable[..., Any]:
        """Register a tool function with the agent.

        Can be used as a decorator with or without arguments.

        Args:
            func: The tool function to register.
            name: Optional custom name for the tool.
            description: Optional description override.
            retries: Optional retry count override.
            graceful_errors: Whether to convert exceptions to ModelRetry.
                None uses the agent config setting (default: True).
                Set False to propagate exceptions directly.

        Returns:
            The decorated function.

        Example:
            >>> @agent.tool
            ... async def read_file(path: str) -> str:
            ...     return Path(path).read_text()
        """
        return self._register_tool(
            func, self._agent.tool, name, description, retries, graceful_errors
        )

    def tool_plain(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        retries: int | None = None,
        graceful_errors: bool | None = None,
    ) -> Callable[..., Any]:
        """Register a plain tool function (no RunContext).

        Similar to tool() but for functions that don't need RunContext.

        Args:
            func: The tool function to register.
            name: Optional custom name for the tool.
            description: Optional description override.
            retries: Optional retry count override.
            graceful_errors: Whether to convert exceptions to ModelRetry.
                None uses the agent config setting (default: True).
                Set False to propagate exceptions directly.

        Returns:
            The decorated function.
        """
        return self._register_tool(
            func, self._agent.tool_plain, name, description, retries, graceful_errors
        )

    def override(
        self,
        *,
        model: Model | None = None,
        deps: DepsT | None = None,
    ) -> Any:
        """Create a context manager to override agent settings.

        Useful for testing with mock models.

        Args:
            model: Model to use instead of configured model.
            deps: Dependencies to use.

        Returns:
            Context manager for the override.
        """
        return self._agent.override(**self._build_kwargs(model=model, deps=deps))

    @property
    def config(self) -> AgentConfig:
        """Get the agent configuration."""
        return self._config

    @property
    def settings(self) -> AgentSettings:
        """Get the agent settings."""
        return self._settings

    @property
    def token_counter(self) -> TokenCounter:
        """Get the token counter for advanced token counting operations."""
        return self._token_counter

    @property
    def usage_tracker(self) -> UsageTracker:
        """Get the usage tracker for detailed usage analysis."""
        return self._usage_tracker

    @property
    def cost_estimator(self) -> CostEstimator:
        """Get the cost estimator for cost calculations."""
        return self._cost_estimator

    @property
    def context_manager(self) -> ContextManager | None:
        """Get the context manager for advanced context operations.

        Returns None if track_context is disabled.
        """
        return self._context_manager

    @property
    def messages(self) -> MessageQuery:
        """Get a MessageQuery interface for the current message history.

        Returns a new ``MessageQuery`` instance on each access, reflecting
        the current state of the conversation. The query uses the Agent's
        configured ``TokenCounter`` for token-aware analytics.

        When context tracking is disabled (``track_context=False``), returns
        a ``MessageQuery`` with an empty message list.

        Returns:
            A ``MessageQuery`` instance over the current messages.
        """
        if self._context_manager is not None:
            current_messages = self._context_manager.get_messages()
        else:
            current_messages = []
        return MessageQuery(current_messages, token_counter=self._token_counter)

    @property
    def model_name(self) -> str | None:
        """Get the model name used by this agent."""
        return self._model_name

    @property
    def prompt_manager(self) -> PromptManager | None:
        """Get the prompt manager.

        Returns None if no prompt manager was provided or created.
        """
        return self._prompt_manager

    # === System Prompt Facade Methods ===

    def get_system_prompt(self) -> str:
        """Get the current resolved system prompt.

        Returns:
            The resolved system prompt string.
        """
        return self._resolved_system_prompt

    def set_system_prompt(
        self,
        prompt: str | TemplateConfig,
        **variables: Any,
    ) -> None:
        """Set a new system prompt at runtime.

        This updates the system prompt and refreshes the context manager.

        Args:
            prompt: New system prompt. Can be a string or TemplateConfig.
            **variables: Additional variables to merge with TemplateConfig variables.

        Note:
            This does not update the underlying pydantic-ai agent's system prompt.
            The new prompt will be used for context tracking and can be retrieved
            via get_system_prompt().
        """
        # Handle additional variables for TemplateConfig
        if isinstance(prompt, TemplateConfig) and variables:
            prompt = TemplateConfig(
                name=prompt.name,
                version=prompt.version,
                variables={**prompt.variables, **variables},
            )

        self._resolved_system_prompt = self._resolve_system_prompt(prompt)

        # Update context manager if enabled
        if self._context_manager is not None:
            self._context_manager.set_system_prompt(self._resolved_system_prompt)

    # === Token Counting Facade Methods ===

    def get_token_count(self, text: str | None = None) -> int:
        """Get token count for text or current context.

        Args:
            text: Optional text to count. If None, returns current context token count.

        Returns:
            Token count.

        Raises:
            RuntimeError: If text is None and context tracking is disabled.
        """
        if text is not None:
            return self._token_counter.count(text)

        return self._ensure_context_enabled().get_token_count()

    # === Usage Tracking Facade Methods ===

    def get_usage(self) -> TokenUsage:
        """Get aggregate token usage statistics.

        Returns:
            TokenUsage with total prompt/completion/total tokens and request count.
        """
        return self._usage_tracker.get_total_usage()

    def get_usage_history(self) -> list[UsageRecord]:
        """Get detailed per-request usage history.

        Returns:
            List of UsageRecord objects for each run.
        """
        return self._usage_tracker.get_usage_history()

    # === Cost Estimation Facade Methods ===

    def get_cost(self, model: str | None = None) -> float:
        """Get estimated cost for all usage.

        Args:
            model: Model name for rate lookup. Defaults to agent's model.

        Returns:
            Estimated cost in USD.
        """
        usage = self._usage_tracker.get_total_usage()
        model_for_cost = model or self._model_name or "default"
        return self._cost_estimator.estimate(usage, model_for_cost).total_cost

    def get_cost_breakdown(self, model: str | None = None) -> CostBreakdown:
        """Get detailed cost breakdown.

        Args:
            model: Model name for rate lookup. Defaults to agent's model.

        Returns:
            CostBreakdown with prompt_cost, completion_cost, total_cost.
        """
        usage = self._usage_tracker.get_total_usage()
        model_for_cost = model or self._model_name or "default"
        return self._cost_estimator.estimate(usage, model_for_cost)

    # === Context Management Facade Methods ===

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages in the context.

        Returns:
            List of message dictionaries.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        return self._ensure_context_enabled().get_messages()

    def should_compact(self) -> bool:
        """Check if context compaction threshold is reached.

        Returns:
            True if compaction should be triggered.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        return self._ensure_context_enabled().should_compact()

    async def compact(self) -> CompactionResult:
        """Manually trigger context compaction.

        Returns:
            CompactionResult with details of what was done.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        return await self._ensure_context_enabled().compact()

    def get_context_state(self) -> ContextState:
        """Get the current context state.

        Returns:
            ContextState with token_count, message_count, etc.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        return self._ensure_context_enabled().get_context_state()

    # === Skill Management Facade Methods ===

    def init_skills(
        self,
        skills: list[Skill | str | Path] | None = None,
        skill_dirs: list[str | Path] | None = None,
    ) -> None:
        """Initialize the SkillManager and register provided skills.

        Creates the ``SkillManager`` if it has not been created yet, then
        registers the given skills and discovers skills from directories.
        If the SkillManager is already initialized, this method is a no-op
        (idempotent).

        Args:
            skills: Optional list of skills to register. Each item can be a
                ``Skill`` instance, a string path, or a ``Path`` to a skill
                directory.
            skill_dirs: Optional list of directories to scan for skills.

        Raises:
            RuntimeError: If this agent is a subagent (subagents cannot
                initialize skill managers).
        """
        if self._config._is_subagent:
            raise RuntimeError(
                "Subagents cannot initialize a SkillManager. "
                "Only the parent agent may call init_skills()."
            )

        if self._skill_manager is not None:
            return

        from mamba_agents.skills import SkillManager as _SkillManager
        from mamba_agents.skills.config import Skill as _Skill

        skill_cfg = self._settings.skills if self._settings.skills is not None else None
        self._skill_manager = _SkillManager(config=skill_cfg)

        # Register individual skills
        if skills is not None:
            for skill in skills:
                if isinstance(skill, str):
                    self._skill_manager.register(Path(skill))
                elif isinstance(skill, (Path, _Skill)):
                    self._skill_manager.register(skill)
                else:
                    self._skill_manager.register(skill)

        # Discover skills from directories
        if skill_dirs is not None:
            from mamba_agents.skills.config import SkillScope, TrustLevel
            from mamba_agents.skills.discovery import scan_directory

            for dir_path in skill_dirs:
                resolved = Path(dir_path) if isinstance(dir_path, str) else dir_path
                found = scan_directory(resolved, SkillScope.CUSTOM, TrustLevel.TRUSTED)
                for info in found:
                    if not self._skill_manager.registry.has(info.name):
                        self._skill_manager.registry.register(info)

        # Register the invoke_skill pydantic-ai tool when skills exist
        if len(self._skill_manager) > 0:
            self._register_invoke_skill_tool()

    def _register_invoke_skill_tool(self) -> None:
        """Register the ``invoke_skill`` pydantic-ai tool on the underlying agent.

        Creates an async tool that allows the model to dynamically invoke
        registered skills during ``agent.run()``. The tool description lists
        all currently available skills (those not disabled for model invocation).

        Skills registered after ``init_skills()`` are still callable via the
        tool -- the tool queries the live registry at invocation time.

        If a tool named ``invoke_skill`` already exists, it is removed first
        to avoid pydantic-ai ``UserError`` on duplicate registration.
        """
        from mamba_agents.skills.invocation import InvocationSource

        # Build dynamic description listing available skills
        skill_lines: list[str] = []
        for info in self._skill_manager.list():
            if not info.disable_model_invocation:
                skill_lines.append(f"- {info.name}: {info.description}")

        if skill_lines:
            available = "\n    ".join(skill_lines)
            description = (
                f"Invoke a registered skill by name.\n\n    Available skills:\n    {available}"
            )
        else:
            description = "Invoke a registered skill by name."

        # Remove existing invoke_skill tool to avoid duplicate registration error
        toolset = self._agent._function_toolset.tools
        toolset.pop("invoke_skill", None)

        # Capture self reference for closure
        agent_self = self

        async def invoke_skill(name: str, arguments: str = "") -> str:
            """Invoke a registered skill by name."""
            try:
                # Check if skill manager is still available
                if agent_self._skill_manager is None:
                    return "Error: No skills available"

                # Look up the skill
                skill = agent_self._skill_manager.get(name)
                if skill is None:
                    available_names = [s.name for s in agent_self._skill_manager.list()]
                    return (
                        f"Error: Skill '{name}' not found. "
                        f"Available skills: {', '.join(available_names) or 'none'}"
                    )

                # Check model invocation permission
                if skill.info.disable_model_invocation:
                    return f"Error: Skill '{name}' has model invocation disabled"

                # Check for fork execution mode
                if skill.info.execution_mode == "fork":
                    from mamba_agents.skills.integration import activate_with_fork

                    if agent_self._subagent_manager is None:
                        return (
                            f"Error: Skill '{name}' requires fork execution "
                            "but no SubagentManager is initialized"
                        )

                    result = await activate_with_fork(
                        skill,
                        arguments,
                        agent_self.subagent_manager,
                        get_skill_fn=agent_self._skill_manager.get,
                    )
                    return result

                # Standard activation with MODEL invocation source
                from mamba_agents.skills.invocation import activate

                return activate(skill, arguments, source=InvocationSource.MODEL)

            except Exception as exc:
                return f"Error: {type(exc).__name__}: {exc}"

        # Register as a plain tool (no RunContext needed)
        self._agent.tool_plain(
            invoke_skill,
            name="invoke_skill",
            description=description,
        )

    @property
    def has_skill_manager(self) -> bool:
        """Check whether the SkillManager has been initialized.

        Returns:
            True if ``init_skills()`` has been called, False otherwise.
        """
        return self._skill_manager is not None

    @property
    def skill_manager(self) -> SkillManager:
        """Get the SkillManager instance.

        Returns:
            The SkillManager instance.

        Raises:
            AttributeError: If the SkillManager has not been initialized.
                Call ``agent.init_skills()`` first.
        """
        if self._skill_manager is None:
            raise AttributeError(
                "SkillManager has not been initialized. "
                "Call agent.init_skills() first, or pass skills/skill_dirs "
                "to the Agent constructor."
            )
        return self._skill_manager

    def register_skill(self, skill: Skill | str | Path) -> None:
        """Register a skill with the agent.

        Delegates to the underlying ``SkillManager.register()`` method,
        then refreshes the ``invoke_skill`` pydantic-ai tool description
        to reflect the updated set of available skills.

        Args:
            skill: A ``Skill`` instance, ``SkillInfo``, string path, or ``Path``
                to a directory containing SKILL.md.
        """
        from mamba_agents.skills.config import Skill as _Skill

        if isinstance(skill, str):
            self.skill_manager.register(Path(skill))
        elif isinstance(skill, (Path, _Skill)):
            self.skill_manager.register(skill)
        else:
            # SkillInfo or other compatible type
            self.skill_manager.register(skill)

        # Refresh the invoke_skill tool description to include the new skill
        self._register_invoke_skill_tool()

    def deregister_skill(self, name: str) -> None:
        """Remove a skill from the agent by name.

        Delegates to the underlying ``SkillManager.deregister()`` method,
        then refreshes the ``invoke_skill`` pydantic-ai tool description
        to reflect the updated set of available skills. If no skills
        remain after removal, the ``invoke_skill`` tool is removed
        entirely.

        Args:
            name: The skill name to remove.

        Raises:
            SkillNotFoundError: If the skill is not registered.
        """
        self.skill_manager.deregister(name)

        # Refresh or remove the invoke_skill tool
        if len(self._skill_manager) > 0:
            self._register_invoke_skill_tool()
        else:
            # No skills left — remove the tool entirely
            toolset = self._agent._function_toolset.tools
            toolset.pop("invoke_skill", None)

    def get_skill(self, name: str) -> Skill | None:
        """Get a skill by name.

        Delegates to the underlying ``SkillManager.get()`` method.

        Args:
            name: The skill name to retrieve.

        Returns:
            The ``Skill`` if found, ``None`` otherwise.
        """
        return self.skill_manager.get(name)

    def list_skills(self) -> list[SkillInfo]:
        """List all registered skill metadata.

        Delegates to the underlying ``SkillManager.list()`` method.

        Returns:
            A list of ``SkillInfo`` for all registered skills.
        """
        return self.skill_manager.list()

    async def invoke_skill(self, name: str, *args: str) -> str:
        """Activate and invoke a skill by name (async).

        Looks up the skill in the manager, activates it with the provided
        arguments joined as a single argument string, and returns the
        processed skill content.

        For skills with ``execution_mode: "fork"``, the Agent mediates
        between the SkillManager and SubagentManager via the integration
        module, passing both managers as explicit arguments. Fork-mode
        delegation uses ``await`` internally for reliable operation in
        async contexts (FastAPI, ASGI servers).

        For non-fork skills, this method is a thin async wrapper around
        the synchronous ``SkillManager.activate()`` call.

        Args:
            name: Name of the skill to invoke.
            *args: Positional arguments to pass to the skill. Arguments are
                joined with spaces into a single argument string.

        Returns:
            Processed skill content with arguments substituted.

        Raises:
            SkillNotFoundError: If the skill is not registered.
            SkillInvocationError: If the invocation source lacks permission,
                or if a fork-mode skill is invoked without a SubagentManager.
        """
        arguments = " ".join(args) if args else ""

        # Check for fork execution mode and mediate via integration module
        skill = self.skill_manager.get(name)
        if skill is not None and skill.info.execution_mode == "fork":
            from mamba_agents.skills.integration import activate_with_fork

            if self._subagent_manager is None:
                from mamba_agents.skills.errors import SkillInvocationError

                raise SkillInvocationError(
                    name=name,
                    source="code",
                    reason=(
                        "Skill has execution_mode='fork' which requires a SubagentManager. "
                        "Call agent.init_subagents() or pass subagents to the Agent "
                        "constructor to enable fork-mode skills."
                    ),
                )

            return await activate_with_fork(
                skill,
                arguments,
                self.subagent_manager,
                get_skill_fn=self.skill_manager.get,
            )

        return self.skill_manager.activate(name, arguments)

    def invoke_skill_sync(self, name: str, *args: str) -> str:
        """Activate and invoke a skill by name (sync wrapper).

        Synchronous convenience wrapper around the async ``invoke_skill()``
        method. For non-fork skills, delegates directly to the synchronous
        ``SkillManager.activate()`` without creating an event loop. For
        fork-mode skills, uses the pydantic-ai ``run_sync`` pattern.

        Args:
            name: Name of the skill to invoke.
            *args: Positional arguments to pass to the skill. Arguments are
                joined with spaces into a single argument string.

        Returns:
            Processed skill content with arguments substituted.

        Raises:
            SkillNotFoundError: If the skill is not registered.
            SkillInvocationError: If the invocation source lacks permission,
                or if a fork-mode skill is invoked without a SubagentManager.
        """
        import asyncio

        arguments = " ".join(args) if args else ""

        # Non-fork skills: call SkillManager.activate() directly (sync, no event loop)
        skill = self.skill_manager.get(name)
        if skill is None or skill.info.execution_mode != "fork":
            return self.skill_manager.activate(name, arguments)

        # Fork-mode: must go through async activate_with_fork
        return asyncio.run(self.invoke_skill(name, *args))

    # === Subagent Management Facade Methods ===

    def init_subagents(
        self,
        subagents: list[SubagentConfig] | None = None,
    ) -> None:
        """Initialize the SubagentManager and register provided configs.

        Creates the ``SubagentManager`` if it has not been created yet, then
        registers the given subagent configurations. If the SubagentManager
        is already initialized, this method is a no-op (idempotent).

        Args:
            subagents: Optional list of subagent configurations to register.

        Raises:
            RuntimeError: If this agent is a subagent (subagents cannot
                initialize subagent managers).
        """
        if self._config._is_subagent:
            raise RuntimeError(
                "Subagents cannot initialize a SubagentManager. "
                "Only the parent agent may call init_subagents()."
            )

        if self._subagent_manager is not None:
            return

        from mamba_agents.subagents import SubagentManager as _SubagentManager

        # Pass the skill registry (not the SkillManager) if available.
        # SubagentManager uses the registry for skill pre-loading only.
        skill_registry = self._skill_manager.registry if self._skill_manager is not None else None

        self._subagent_manager = _SubagentManager(
            parent_agent=self,
            configs=subagents,
            skill_registry=skill_registry,
        )

    @property
    def has_subagent_manager(self) -> bool:
        """Check whether the SubagentManager has been initialized.

        Returns:
            True if ``init_subagents()`` has been called, False otherwise.
        """
        return self._subagent_manager is not None

    @property
    def subagent_manager(self) -> SubagentManager:
        """Get the SubagentManager instance.

        Returns:
            The SubagentManager instance.

        Raises:
            AttributeError: If the SubagentManager has not been initialized.
                Call ``agent.init_subagents()`` first.
        """
        if self._subagent_manager is None:
            raise AttributeError(
                "SubagentManager has not been initialized. "
                "Call agent.init_subagents() first, or pass subagents "
                "to the Agent constructor."
            )
        return self._subagent_manager

    async def delegate(
        self,
        config_name: str,
        task: str,
        **kwargs: Any,
    ) -> SubagentResult:
        """Delegate a task to a registered subagent (async).

        Spawns a subagent from the named config, runs the task, and
        returns the result. Token usage is automatically aggregated
        to this agent's ``UsageTracker``.

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
        return await self.subagent_manager.delegate(config_name, task, **kwargs)

    def delegate_sync(
        self,
        config_name: str,
        task: str,
        **kwargs: Any,
    ) -> SubagentResult:
        """Delegate a task to a registered subagent (sync wrapper).

        Synchronous convenience wrapper around the async ``delegate()``
        method.

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
        return self.subagent_manager.delegate_sync(config_name, task, **kwargs)

    async def delegate_async(
        self,
        config_name: str,
        task: str,
        **kwargs: Any,
    ) -> DelegationHandle:
        """Delegate a task to a registered subagent asynchronously.

        Returns a ``DelegationHandle`` immediately while the subagent
        runs in the background.

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
        return await self.subagent_manager.delegate_async(config_name, task, **kwargs)

    def register_subagent(self, config: SubagentConfig) -> None:
        """Register a subagent configuration.

        Delegates to the underlying ``SubagentManager.register()`` method.

        Args:
            config: The subagent configuration to register.

        Raises:
            SubagentConfigError: If the config fails validation.
        """
        self.subagent_manager.register(config)

    def list_subagents(self) -> list[SubagentConfig]:
        """List all registered subagent configurations.

        Delegates to the underlying ``SubagentManager.list()`` method.

        Returns:
            List of all registered ``SubagentConfig`` instances.
        """
        return self.subagent_manager.list()

    # === Reset Operations ===

    def clear_context(self) -> None:
        """Clear all context (messages and compaction history).

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        self._ensure_context_enabled().clear()

    def reset_tracking(self) -> None:
        """Reset usage tracking data (keeps context)."""
        self._usage_tracker.reset()

    def reset_all(self) -> None:
        """Reset both context and usage tracking."""
        self.reset_tracking()
        if self._context_manager is not None:
            self._context_manager.clear()
