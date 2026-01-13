"""Core Agent class wrapping pydantic-ai."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models import Model

from pydantic_agent.agent.config import AgentConfig
from pydantic_agent.agent.message_utils import dicts_to_model_messages, model_messages_to_dicts
from pydantic_agent.agent.result import AgentResult
from pydantic_agent.config.settings import AgentSettings
from pydantic_agent.context import ContextManager, ContextState
from pydantic_agent.context.compaction import CompactionResult
from pydantic_agent.tokens import CostEstimator, TokenCounter, UsageTracker
from pydantic_agent.tokens.cost import CostBreakdown
from pydantic_agent.tokens.tracker import TokenUsage, UsageRecord

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.result import StreamedRunResult
    from pydantic_ai.tools import ToolDefinition
    from pydantic_ai.usage import UsageLimits


DepsT = TypeVar("DepsT")
OutputT = TypeVar("OutputT")


class Agent(Generic[DepsT, OutputT]):
    """AI Agent with tool-calling capabilities.

    This is a thin wrapper around pydantic-ai's Agent class that adds:
    - Configuration via AgentSettings
    - Context management and compaction
    - Token usage tracking
    - Enhanced observability

    Example:
        >>> from pydantic_agent import Agent
        >>>
        >>> agent = Agent(
        ...     "openai:gpt-4",
        ...     system_prompt="You are a helpful assistant.",
        ... )
        >>> result = await agent.run("Hello, world!")
        >>> print(result.output)
    """

    def __init__(
        self,
        model: str | Model | None = None,
        *,
        tools: Sequence[Callable[..., Any] | ToolDefinition] | None = None,
        system_prompt: str = "",
        deps_type: type[DepsT] | None = None,
        output_type: type[OutputT] | None = None,
        config: AgentConfig | None = None,
        settings: AgentSettings | None = None,
    ) -> None:
        """Initialize the agent.

        Args:
            model: Model to use (string identifier or Model instance).
                If not provided, uses settings.model_backend configuration.
            tools: Optional list of tools to register.
            system_prompt: System prompt for the agent.
            deps_type: Type of dependencies for tool calls.
            output_type: Expected output type.
            config: Agent execution configuration.
            settings: Full agent settings (for model backend, etc.).

        Raises:
            ValueError: If neither model nor settings is provided.
        """
        self._config = config or AgentConfig(system_prompt=system_prompt)
        self._settings = settings or AgentSettings()

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

        # Create the underlying pydantic-ai agent
        agent_kwargs: dict[str, Any] = {
            "system_prompt": self._config.system_prompt,
        }

        if tools:
            agent_kwargs["tools"] = list(tools)

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
            if self._config.system_prompt:
                self._context_manager.set_system_prompt(self._config.system_prompt)
        else:
            self._context_manager = None

    @classmethod
    def from_settings(
        cls,
        settings: AgentSettings,
        *,
        tools: Sequence[Callable[..., Any] | ToolDefinition] | None = None,
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
            system_prompt=system_prompt,
            deps_type=deps_type,
            output_type=output_type,
            settings=settings,
        )

    async def _post_run_hook(self, result: AgentResult[OutputT]) -> None:
        """Handle post-run tracking and context management.

        Args:
            result: The result from the run.
        """
        # 1. Always record usage
        self._usage_tracker.record_usage(result.usage(), model=self._model_name)

        # 2. Track messages in context manager if enabled
        if self._context_manager is not None:
            new_messages = model_messages_to_dicts(result.new_messages())
            self._context_manager.add_messages(new_messages)

            # 3. Auto-compact if enabled and threshold reached
            if self._config.auto_compact and self._context_manager.should_compact():
                await self._context_manager.compact()

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
        kwargs: dict[str, Any] = {}
        if deps is not None:
            kwargs["deps"] = deps
        if usage_limits is not None:
            kwargs["usage_limits"] = usage_limits

        # Determine message history to use
        if message_history is not None:
            # Explicit history provided - use it
            kwargs["message_history"] = message_history
        elif self._context_manager is not None:
            # Use internal context (convert to pydantic-ai format)
            internal_messages = self._context_manager.get_messages()
            if internal_messages:
                kwargs["message_history"] = dicts_to_model_messages(internal_messages)

        result = await self._agent.run(prompt, **kwargs)
        wrapped_result = AgentResult(result)

        # Post-run tracking
        await self._post_run_hook(wrapped_result)

        return wrapped_result

    def _post_run_hook_sync(self, result: AgentResult[OutputT]) -> None:
        """Handle post-run tracking and context management (synchronous version).

        Args:
            result: The result from the run.
        """
        # 1. Always record usage
        self._usage_tracker.record_usage(result.usage(), model=self._model_name)

        # 2. Track messages in context manager if enabled
        if self._context_manager is not None:
            new_messages = model_messages_to_dicts(result.new_messages())
            self._context_manager.add_messages(new_messages)

            # 3. Auto-compact if enabled and threshold reached
            # Note: For sync version, we use asyncio.run for compaction
            if self._config.auto_compact and self._context_manager.should_compact():
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
        kwargs: dict[str, Any] = {}
        if deps is not None:
            kwargs["deps"] = deps
        if usage_limits is not None:
            kwargs["usage_limits"] = usage_limits

        # Determine message history to use
        if message_history is not None:
            # Explicit history provided - use it
            kwargs["message_history"] = message_history
        elif self._context_manager is not None:
            # Use internal context (convert to pydantic-ai format)
            internal_messages = self._context_manager.get_messages()
            if internal_messages:
                kwargs["message_history"] = dicts_to_model_messages(internal_messages)

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
        kwargs: dict[str, Any] = {}
        if deps is not None:
            kwargs["deps"] = deps
        if usage_limits is not None:
            kwargs["usage_limits"] = usage_limits

        # Determine message history to use
        if message_history is not None:
            # Explicit history provided - use it
            kwargs["message_history"] = message_history
        elif self._context_manager is not None:
            # Use internal context (convert to pydantic-ai format)
            internal_messages = self._context_manager.get_messages()
            if internal_messages:
                kwargs["message_history"] = dicts_to_model_messages(internal_messages)

        async with self._agent.run_stream(prompt, **kwargs) as result:
            yield result
            # After stream is consumed and yield returns, track usage and messages
            self._usage_tracker.record_usage(result.usage(), model=self._model_name)
            if self._context_manager is not None:
                new_messages = model_messages_to_dicts(result.all_messages())
                self._context_manager.add_messages(new_messages)
                if self._config.auto_compact and self._context_manager.should_compact():
                    await self._context_manager.compact()

    def tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        retries: int | None = None,
    ) -> Callable[..., Any]:
        """Register a tool function with the agent.

        Can be used as a decorator with or without arguments.

        Args:
            func: The tool function to register.
            name: Optional custom name for the tool.
            description: Optional description override.
            retries: Optional retry count override.

        Returns:
            The decorated function.

        Example:
            >>> @agent.tool
            ... async def read_file(path: str) -> str:
            ...     return Path(path).read_text()
        """
        kwargs: dict[str, Any] = {}
        if name:
            kwargs["name"] = name
        if description:
            kwargs["description"] = description
        if retries is not None:
            kwargs["retries"] = retries

        if func is not None:
            return self._agent.tool(**kwargs)(func)

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            return self._agent.tool(**kwargs)(f)

        return decorator

    def tool_plain(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        retries: int | None = None,
    ) -> Callable[..., Any]:
        """Register a plain tool function (no RunContext).

        Similar to tool() but for functions that don't need RunContext.

        Args:
            func: The tool function to register.
            name: Optional custom name for the tool.
            description: Optional description override.
            retries: Optional retry count override.

        Returns:
            The decorated function.
        """
        kwargs: dict[str, Any] = {}
        if name:
            kwargs["name"] = name
        if description:
            kwargs["description"] = description
        if retries is not None:
            kwargs["retries"] = retries

        if func is not None:
            return self._agent.tool_plain(**kwargs)(func)

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            return self._agent.tool_plain(**kwargs)(f)

        return decorator

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
        kwargs: dict[str, Any] = {}
        if model is not None:
            kwargs["model"] = model
        if deps is not None:
            kwargs["deps"] = deps
        return self._agent.override(**kwargs)

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

        if self._context_manager is None:
            raise RuntimeError(
                "Context tracking is disabled. Enable with AgentConfig(track_context=True)"
            )
        return self._context_manager.get_token_count()

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
        if self._context_manager is None:
            raise RuntimeError(
                "Context tracking is disabled. Enable with AgentConfig(track_context=True)"
            )
        return self._context_manager.get_messages()

    def should_compact(self) -> bool:
        """Check if context compaction threshold is reached.

        Returns:
            True if compaction should be triggered.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        if self._context_manager is None:
            raise RuntimeError(
                "Context tracking is disabled. Enable with AgentConfig(track_context=True)"
            )
        return self._context_manager.should_compact()

    async def compact(self) -> CompactionResult:
        """Manually trigger context compaction.

        Returns:
            CompactionResult with details of what was done.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        if self._context_manager is None:
            raise RuntimeError(
                "Context tracking is disabled. Enable with AgentConfig(track_context=True)"
            )
        return await self._context_manager.compact()

    def get_context_state(self) -> ContextState:
        """Get the current context state.

        Returns:
            ContextState with token_count, message_count, etc.

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        if self._context_manager is None:
            raise RuntimeError(
                "Context tracking is disabled. Enable with AgentConfig(track_context=True)"
            )
        return self._context_manager.get_context_state()

    # === Reset Operations ===

    def clear_context(self) -> None:
        """Clear all context (messages and compaction history).

        Raises:
            RuntimeError: If context tracking is disabled.
        """
        if self._context_manager is None:
            raise RuntimeError(
                "Context tracking is disabled. Enable with AgentConfig(track_context=True)"
            )
        self._context_manager.clear()

    def reset_tracking(self) -> None:
        """Reset usage tracking data (keeps context)."""
        self._usage_tracker.reset()

    def reset_all(self) -> None:
        """Reset both context and usage tracking."""
        self.reset_tracking()
        if self._context_manager is not None:
            self._context_manager.clear()
