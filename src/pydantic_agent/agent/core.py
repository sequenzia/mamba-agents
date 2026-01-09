"""Core Agent class wrapping pydantic-ai."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai.models import Model

from pydantic_agent.agent.config import AgentConfig
from pydantic_agent.agent.result import AgentResult
from pydantic_agent.config.settings import AgentSettings

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
        tools: Sequence[Callable[..., Any] | "ToolDefinition"] | None = None,
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

        # Construct model from settings if not provided
        if model is None:
            if settings is None:
                raise ValueError("Either 'model' or 'settings' must be provided")

            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.openai import OpenAIProvider

            model = OpenAIChatModel(
                self._settings.model_backend.model,
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

    @classmethod
    def from_settings(
        cls,
        settings: AgentSettings,
        *,
        tools: Sequence[Callable[..., Any] | "ToolDefinition"] | None = None,
        system_prompt: str = "",
        deps_type: type[DepsT] | None = None,
        output_type: type[OutputT] | None = None,
    ) -> "Agent[DepsT, OutputT]":
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

    async def run(
        self,
        prompt: str,
        *,
        deps: DepsT | None = None,
        message_history: list["ModelMessage"] | None = None,
        usage_limits: "UsageLimits | None" = None,
    ) -> AgentResult[OutputT]:
        """Run the agent with the given prompt.

        Args:
            prompt: User prompt to process.
            deps: Optional dependencies for tool calls.
            message_history: Optional message history for context.
            usage_limits: Optional usage limits.

        Returns:
            AgentResult containing the output and metadata.
        """
        kwargs: dict[str, Any] = {}
        if deps is not None:
            kwargs["deps"] = deps
        if message_history is not None:
            kwargs["message_history"] = message_history
        if usage_limits is not None:
            kwargs["usage_limits"] = usage_limits

        result = await self._agent.run(prompt, **kwargs)
        return AgentResult(result)

    def run_sync(
        self,
        prompt: str,
        *,
        deps: DepsT | None = None,
        message_history: list["ModelMessage"] | None = None,
        usage_limits: "UsageLimits | None" = None,
    ) -> AgentResult[OutputT]:
        """Run the agent synchronously.

        Args:
            prompt: User prompt to process.
            deps: Optional dependencies for tool calls.
            message_history: Optional message history for context.
            usage_limits: Optional usage limits.

        Returns:
            AgentResult containing the output and metadata.
        """
        kwargs: dict[str, Any] = {}
        if deps is not None:
            kwargs["deps"] = deps
        if message_history is not None:
            kwargs["message_history"] = message_history
        if usage_limits is not None:
            kwargs["usage_limits"] = usage_limits

        result = self._agent.run_sync(prompt, **kwargs)
        return AgentResult(result)

    async def run_stream(
        self,
        prompt: str,
        *,
        deps: DepsT | None = None,
        message_history: list["ModelMessage"] | None = None,
        usage_limits: "UsageLimits | None" = None,
    ) -> AsyncIterator["StreamedRunResult[OutputT]"]:
        """Run the agent with streaming output.

        Args:
            prompt: User prompt to process.
            deps: Optional dependencies for tool calls.
            message_history: Optional message history for context.
            usage_limits: Optional usage limits.

        Yields:
            StreamedRunResult with streaming response events.
        """
        kwargs: dict[str, Any] = {}
        if deps is not None:
            kwargs["deps"] = deps
        if message_history is not None:
            kwargs["message_history"] = message_history
        if usage_limits is not None:
            kwargs["usage_limits"] = usage_limits

        async with self._agent.run_stream(prompt, **kwargs) as result:
            yield result

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
