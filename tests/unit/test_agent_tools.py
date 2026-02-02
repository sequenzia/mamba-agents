"""Tests for Agent tool registration and graceful error handling."""

from __future__ import annotations

import pytest
from pydantic_ai import ModelRetry
from pydantic_ai.models.test import TestModel

from mamba_agents import Agent, AgentConfig


class TestAgentConfigGracefulToolErrors:
    """Tests for AgentConfig graceful_tool_errors field."""

    def test_default_config_has_graceful_tool_errors_enabled(self) -> None:
        """Test default config has graceful_tool_errors=True."""
        config = AgentConfig()
        assert config.graceful_tool_errors is True

    def test_graceful_tool_errors_can_be_disabled(self) -> None:
        """Test graceful_tool_errors can be explicitly disabled."""
        config = AgentConfig(graceful_tool_errors=False)
        assert config.graceful_tool_errors is False


class TestGracefulToolErrorsWrapper:
    """Tests for the graceful error wrapper functionality."""

    def test_sync_tool_exception_converts_to_model_retry(self) -> None:
        """Test that sync tool exceptions are converted to ModelRetry."""
        agent = Agent[None, str](TestModel())

        @agent.tool_plain
        def failing_tool(path: str) -> str:
            raise FileNotFoundError(f"File not found: {path}")

        # Directly invoke the tool to test the wrapper
        # The tool is wrapped, so it should raise ModelRetry
        with pytest.raises(ModelRetry) as exc_info:
            failing_tool("/nonexistent/path")

        assert "FileNotFoundError: File not found: /nonexistent/path" in str(exc_info.value)
        # Check exception chain is preserved
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    @pytest.mark.asyncio
    async def test_async_tool_exception_converts_to_model_retry(self) -> None:
        """Test that async tool exceptions are converted to ModelRetry."""
        agent = Agent[None, str](TestModel())

        @agent.tool_plain
        async def async_failing_tool(path: str) -> str:
            raise ValueError(f"Invalid path: {path}")

        with pytest.raises(ModelRetry) as exc_info:
            await async_failing_tool("/bad/path")

        assert "ValueError: Invalid path: /bad/path" in str(exc_info.value)
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_model_retry_passthrough_no_double_wrapping(self) -> None:
        """Test that ModelRetry is passed through unchanged (no double-wrapping)."""
        agent = Agent[None, str](TestModel())

        @agent.tool_plain
        def retry_tool(data: str) -> str:
            raise ModelRetry("Please try with different parameters")

        with pytest.raises(ModelRetry) as exc_info:
            retry_tool("test")

        # Should be the original message, not wrapped
        assert str(exc_info.value) == "Please try with different parameters"
        # Should not have a __cause__ since it's passed through directly
        assert exc_info.value.__cause__ is None

    @pytest.mark.asyncio
    async def test_async_model_retry_passthrough(self) -> None:
        """Test that async ModelRetry is passed through unchanged."""
        agent = Agent[None, str](TestModel())

        @agent.tool_plain
        async def async_retry_tool(data: str) -> str:
            raise ModelRetry("Async retry message")

        with pytest.raises(ModelRetry) as exc_info:
            await async_retry_tool("test")

        assert str(exc_info.value) == "Async retry message"
        assert exc_info.value.__cause__ is None

    def test_successful_tool_returns_normally(self) -> None:
        """Test that successful tools return their values normally."""
        agent = Agent[None, str](TestModel())

        @agent.tool_plain
        def success_tool(name: str) -> str:
            return f"Hello, {name}!"

        result = success_tool("World")
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_async_successful_tool_returns_normally(self) -> None:
        """Test that async successful tools return normally."""
        agent = Agent[None, str](TestModel())

        @agent.tool_plain
        async def async_success_tool(name: str) -> str:
            return f"Async Hello, {name}!"

        result = await async_success_tool("World")
        assert result == "Async Hello, World!"

    def test_function_metadata_preserved(self) -> None:
        """Test that function metadata is preserved after wrapping."""
        agent = Agent[None, str](TestModel())

        @agent.tool_plain
        def documented_tool(x: int) -> int:
            """A well-documented tool that doubles its input."""
            return x * 2

        # functools.wraps should preserve these
        assert documented_tool.__name__ == "documented_tool"
        assert documented_tool.__doc__ == "A well-documented tool that doubles its input."


class TestAgentLevelDisable:
    """Tests for disabling graceful errors at the agent level."""

    def test_agent_level_disable_propagates_exceptions(self) -> None:
        """Test that exceptions propagate when agent has graceful errors disabled."""
        config = AgentConfig(graceful_tool_errors=False)
        agent = Agent[None, str](TestModel(), config=config)

        @agent.tool_plain
        def strict_tool(data: str) -> str:
            raise RuntimeError("Strict failure")

        # Should raise RuntimeError directly, not ModelRetry
        with pytest.raises(RuntimeError) as exc_info:
            strict_tool("test")

        assert "Strict failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_agent_level_disable_async(self) -> None:
        """Test that async exceptions propagate when agent has graceful errors disabled."""
        config = AgentConfig(graceful_tool_errors=False)
        agent = Agent[None, str](TestModel(), config=config)

        @agent.tool_plain
        async def async_strict_tool(data: str) -> str:
            raise KeyError("missing_key")

        with pytest.raises(KeyError):
            await async_strict_tool("test")


class TestPerToolOverride:
    """Tests for per-tool graceful_errors override."""

    def test_per_tool_opt_out(self) -> None:
        """Test per-tool opt-out with graceful_errors=False."""
        # Agent has graceful errors enabled by default
        agent = Agent[None, str](TestModel())

        @agent.tool_plain(graceful_errors=False)
        def critical_tool(data: str) -> str:
            raise ValueError("Critical failure")

        # Should raise ValueError directly, not ModelRetry
        with pytest.raises(ValueError) as exc_info:
            critical_tool("test")

        assert "Critical failure" in str(exc_info.value)

    def test_per_tool_opt_in_when_agent_disabled(self) -> None:
        """Test per-tool opt-in when agent has graceful errors disabled."""
        config = AgentConfig(graceful_tool_errors=False)
        agent = Agent[None, str](TestModel(), config=config)

        @agent.tool_plain(graceful_errors=True)
        def graceful_tool(data: str) -> str:
            raise OSError("IO failed")

        # Should raise ModelRetry because per-tool overrides agent config
        with pytest.raises(ModelRetry) as exc_info:
            graceful_tool("test")

        assert "OSError: IO failed" in str(exc_info.value)

    def test_per_tool_none_uses_agent_default(self) -> None:
        """Test per-tool graceful_errors=None uses agent default."""
        # Default agent has graceful_tool_errors=True
        agent = Agent[None, str](TestModel())

        @agent.tool_plain(graceful_errors=None)  # Explicit None
        def default_tool(data: str) -> str:
            raise TypeError("Type error")

        with pytest.raises(ModelRetry) as exc_info:
            default_tool("test")

        assert "TypeError: Type error" in str(exc_info.value)


class TestToolDecorator:
    """Tests for the tool() decorator (with RunContext support)."""

    def test_tool_decorator_graceful_errors(self) -> None:
        """Test tool() decorator also supports graceful errors."""
        agent = Agent[None, str](TestModel())

        @agent.tool
        def context_tool(ctx, data: str) -> str:
            raise PermissionError("Access denied")

        with pytest.raises(ModelRetry) as exc_info:
            context_tool(None, "test")

        assert "PermissionError: Access denied" in str(exc_info.value)

    def test_tool_decorator_opt_out(self) -> None:
        """Test tool() decorator can opt out of graceful errors."""
        agent = Agent[None, str](TestModel())

        @agent.tool(graceful_errors=False)
        def strict_context_tool(ctx, data: str) -> str:
            raise PermissionError("Strict access denied")

        with pytest.raises(PermissionError):
            strict_context_tool(None, "test")


class TestConstructorToolsGracefulErrors:
    """Tests for graceful error wrapping of constructor-provided tools."""

    def test_constructor_tools_wrapped_by_default(self) -> None:
        """Test that constructor tools get graceful error wrapping by default."""

        def failing_tool(path: str) -> str:
            """A tool that raises an error."""
            raise FileNotFoundError(f"File not found: {path}")

        # Wrap the tool the same way the constructor does
        agent = Agent[None, str](TestModel())
        wrapped = agent._wrap_tool_with_graceful_errors(failing_tool)

        with pytest.raises(ModelRetry) as exc_info:
            wrapped(path="/nonexistent")

        assert "FileNotFoundError: File not found: /nonexistent" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_constructor_tools_applied_when_enabled(self) -> None:
        """Test that constructor creates agent with wrapped tools by default."""
        from pydantic_ai.exceptions import UnexpectedModelBehavior

        def failing_tool(path: str) -> str:
            """A tool that raises an error."""
            raise FileNotFoundError(f"File not found: {path}")

        # Agent with default config (graceful_tool_errors=True)
        # should wrap tools before passing to pydantic-ai
        agent = Agent[None, str](TestModel(), tools=[failing_tool])

        # When wrapped, the FileNotFoundError becomes ModelRetry,
        # which pydantic-ai catches and retries until max retries exceeded.
        # This proves the wrapping happened — without it, FileNotFoundError
        # would propagate directly.
        with pytest.raises(UnexpectedModelBehavior, match="exceeded max retries"):
            agent.run_sync("call failing_tool")

    def test_constructor_tools_not_wrapped_when_disabled(self) -> None:
        """Test that constructor tools are NOT wrapped when graceful errors disabled."""

        def failing_tool(path: str) -> str:
            """A tool that raises an error."""
            raise FileNotFoundError(f"File not found: {path}")

        config = AgentConfig(graceful_tool_errors=False)
        agent = Agent[None, str](TestModel(), tools=[failing_tool], config=config)

        # The raw exception should propagate through pydantic-ai
        with pytest.raises(FileNotFoundError):
            agent.run_sync("call failing_tool")

    def test_constructor_tools_succeed_normally(self) -> None:
        """Test that constructor tools return values normally when no error."""

        def greeting_tool(name: str) -> str:
            """A tool that greets."""
            return f"Hello, {name}!"

        agent = Agent[None, str](TestModel(), tools=[greeting_tool])

        # Wrapped tools should still return values normally
        wrapped = agent._wrap_tool_with_graceful_errors(greeting_tool)
        result = wrapped(name="World")
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_constructor_async_tools_wrapped(self) -> None:
        """Test that async constructor tools get graceful error wrapping."""

        async def async_failing_tool(url: str) -> str:
            """An async tool that raises an error."""
            raise ConnectionError(f"Cannot connect to {url}")

        agent = Agent[None, str](TestModel())
        wrapped = agent._wrap_tool_with_graceful_errors(async_failing_tool)

        with pytest.raises(ModelRetry) as exc_info:
            await wrapped(url="http://bad-host")

        assert "ConnectionError: Cannot connect to http://bad-host" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ConnectionError)

    def test_constructor_tools_preserve_metadata(self) -> None:
        """Test that wrapped constructor tools preserve function metadata."""

        def documented_tool(x: int) -> int:
            """Doubles the input value."""
            return x * 2

        agent = Agent[None, str](TestModel())
        wrapped = agent._wrap_tool_with_graceful_errors(documented_tool)
        assert wrapped.__name__ == "documented_tool"
        assert wrapped.__doc__ == "Doubles the input value."


class TestExceptionChain:
    """Tests for exception chain preservation."""

    def test_exception_cause_is_preserved(self) -> None:
        """Test that the original exception is preserved in __cause__."""
        agent = Agent[None, str](TestModel())

        original_exception = ValueError("Original error")

        @agent.tool_plain
        def chain_tool(data: str) -> str:
            raise original_exception

        with pytest.raises(ModelRetry) as exc_info:
            chain_tool("test")

        # The __cause__ should be the exact same exception object
        assert exc_info.value.__cause__ is original_exception

    @pytest.mark.asyncio
    async def test_async_exception_cause_preserved(self) -> None:
        """Test that async exception cause is preserved."""
        agent = Agent[None, str](TestModel())

        original_exception = RuntimeError("Async original")

        @agent.tool_plain
        async def async_chain_tool(data: str) -> str:
            raise original_exception

        with pytest.raises(ModelRetry) as exc_info:
            await async_chain_tool("test")

        assert exc_info.value.__cause__ is original_exception
