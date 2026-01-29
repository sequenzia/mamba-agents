"""Core Agent class wrapping pydantic-ai."""

from __future__ import annotations

import functools
import inspect
import logging
from collections.abc import AsyncIterator, Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import ModelRetry
from pydantic_ai.models import Model
from pydantic_ai.toolsets import AbstractToolset

from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.message_utils import dicts_to_model_messages, model_messages_to_dicts
from mamba_agents.agent.result import AgentResult
from mamba_agents.config.settings import AgentSettings
from mamba_agents.context import ContextManager, ContextState
from mamba_agents.context.compaction import CompactionResult
from mamba_agents.prompts.config import TemplateConfig
from mamba_agents.tokens import CostEstimator, TokenCounter, UsageTracker
from mamba_agents.tokens.cost import CostBreakdown
from mamba_agents.tokens.tracker import TokenUsage, UsageRecord

logger = logging.getLogger(__name__)

from pydantic_ai import (
    AgentRunResultEvent,
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ToolCallPartDelta,
)

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.result import StreamedRunResult
    from pydantic_ai.tools import ToolDefinition
    from pydantic_ai.usage import UsageLimits

    from mamba_agents.prompts import PromptManager


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

    async def run_stream_events(
        self,
        prompt: str,
        *,
        deps: DepsT | None = None,
        message_history: list[ModelMessage] | None = None,
        usage_limits: UsageLimits | None = None,
    ) -> AsyncIterator[AgentStreamEvent | AgentRunResultEvent]:
        """Run the agent and stream all events including tool calls.

        This method provides fine-grained control over the agent's execution,
        yielding events in real-time as they occur:

        - PartStartEvent: Start of a text or tool call part
        - PartDeltaEvent: Incremental text or tool argument deltas
        - FunctionToolCallEvent: When a tool is about to be called
        - FunctionToolResultEvent: When a tool returns its result
        - FinalResultEvent: When the model starts producing final output
        - AgentRunResultEvent: Final result with complete output

        Args:
            prompt: User prompt to process.
            deps: Optional dependencies for tool calls.
            message_history: Optional message history for context.
                If None and context tracking is enabled, uses internal context.
            usage_limits: Optional usage limits.

        Yields:
            AgentStreamEvent or AgentRunResultEvent objects.

        Example:
            async for event in agent.run_stream_events("What's the weather?"):
                if isinstance(event, FunctionToolCallEvent):
                    print(f"Calling tool: {event.part.tool_name}")
                elif isinstance(event, FunctionToolResultEvent):
                    print(f"Tool result: {event.result.content}")
                elif isinstance(event, AgentRunResultEvent):
                    print(f"Final: {event.result.output}")
        """
        kwargs = self._build_kwargs(
            deps=deps,
            usage_limits=usage_limits,
            message_history=self._resolve_message_history(message_history),
        )

        final_result: AgentRunResultEvent | None = None
        async for event in self._agent.run_stream_events(prompt, **kwargs):
            yield event
            # Capture final result for post-processing
            if isinstance(event, AgentRunResultEvent):
                final_result = event

        # After stream completes, track usage and messages
        if final_result is not None:
            self._usage_tracker.record_usage(
                final_result.result.usage(), model=self._model_name
            )
            if self._context_manager is not None:
                new_messages = model_messages_to_dicts(final_result.result.all_messages())
                self._context_manager.add_messages(new_messages)
                if self._config.auto_compact and self._context_manager.should_compact():
                    await self._context_manager.compact()
        else:
            logger.warning(
                "run_stream_events completed without AgentRunResultEvent, "
                "usage tracking skipped"
            )

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
