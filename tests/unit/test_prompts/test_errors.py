"""Tests for prompt error classes."""

from mamba_agents.prompts.errors import (
    PromptError,
    PromptNotFoundError,
    TemplateRenderError,
    TemplateValidationError,
)


class TestPromptError:
    """Tests for base PromptError."""

    def test_is_exception(self) -> None:
        """Test PromptError is an Exception."""
        error = PromptError("Test error")
        assert isinstance(error, Exception)

    def test_message(self) -> None:
        """Test error message."""
        error = PromptError("Custom message")
        assert str(error) == "Custom message"


class TestPromptNotFoundError:
    """Tests for PromptNotFoundError."""

    def test_basic_error(self) -> None:
        """Test error with just name."""
        error = PromptNotFoundError("system/assistant")

        assert error.name == "system/assistant"
        assert error.version is None
        assert "system/assistant" in str(error)

    def test_error_with_version(self) -> None:
        """Test error with name and version."""
        error = PromptNotFoundError("system/assistant", version="v2")

        assert error.name == "system/assistant"
        assert error.version == "v2"
        assert "system/assistant" in str(error)
        assert "v2" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from PromptError."""
        error = PromptNotFoundError("test")
        assert isinstance(error, PromptError)


class TestTemplateRenderError:
    """Tests for TemplateRenderError."""

    def test_basic_error(self) -> None:
        """Test error with name and cause."""
        cause = ValueError("Missing variable")
        error = TemplateRenderError("test/prompt", cause)

        assert error.name == "test/prompt"
        assert error.cause is cause
        assert "test/prompt" in str(error)
        assert "Missing variable" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from PromptError."""
        error = TemplateRenderError("test", ValueError("test"))
        assert isinstance(error, PromptError)


class TestTemplateValidationError:
    """Tests for TemplateValidationError."""

    def test_basic_error(self) -> None:
        """Test error with name and message."""
        error = TemplateValidationError("test/prompt", "Invalid syntax on line 5")

        assert error.name == "test/prompt"
        assert "test/prompt" in str(error)
        assert "Invalid syntax" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from PromptError."""
        error = TemplateValidationError("test", "error")
        assert isinstance(error, PromptError)
