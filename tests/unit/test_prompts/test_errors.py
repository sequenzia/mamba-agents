"""Tests for prompt error classes."""

from mamba_agents.prompts.errors import (
    MarkdownParseError,
    PromptError,
    PromptNotFoundError,
    TemplateConflictError,
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


class TestMarkdownParseError:
    """Tests for MarkdownParseError."""

    def test_basic_error(self) -> None:
        """Test error with name and message."""
        error = MarkdownParseError("test/prompt", "Invalid YAML frontmatter")

        assert error.name == "test/prompt"
        assert "test/prompt" in str(error)
        assert "Invalid YAML frontmatter" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from PromptError."""
        error = MarkdownParseError("test", "error")
        assert isinstance(error, PromptError)


class TestTemplateConflictError:
    """Tests for TemplateConflictError."""

    def test_basic_error(self) -> None:
        """Test error with name, version, and extensions."""
        error = TemplateConflictError("test/prompt", "v1", [".jinja2", ".md"])

        assert error.name == "test/prompt"
        assert error.version == "v1"
        assert error.extensions == [".jinja2", ".md"]
        assert "test/prompt" in str(error)
        assert "v1" in str(error)
        assert ".jinja2" in str(error)
        assert ".md" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from PromptError."""
        error = TemplateConflictError("test", "v1", [".a", ".b"])
        assert isinstance(error, PromptError)

    def test_multiple_extensions_in_message(self) -> None:
        """Test error message includes all conflicting extensions."""
        error = TemplateConflictError("test", "v1", [".jinja2", ".md", ".txt"])
        message = str(error)

        assert ".jinja2, .md, .txt" in message or all(
            ext in message for ext in [".jinja2", ".md", ".txt"]
        )
