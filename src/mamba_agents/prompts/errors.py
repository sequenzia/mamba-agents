"""Prompt management exceptions."""

from __future__ import annotations


class PromptError(Exception):
    """Base exception for prompt-related errors."""


class PromptNotFoundError(PromptError):
    """Raised when a prompt template cannot be found."""

    def __init__(self, name: str, version: str | None = None) -> None:
        """Initialize the error.

        Args:
            name: Template name that was not found.
            version: Template version that was not found.
        """
        self.name = name
        self.version = version
        version_str = f" (version: {version})" if version else ""
        super().__init__(f"Prompt template not found: {name}{version_str}")


class TemplateRenderError(PromptError):
    """Raised when a template fails to render."""

    def __init__(self, name: str, cause: Exception) -> None:
        """Initialize the error.

        Args:
            name: Template name that failed to render.
            cause: The underlying exception.
        """
        self.name = name
        self.cause = cause
        super().__init__(f"Failed to render template '{name}': {cause}")


class TemplateValidationError(PromptError):
    """Raised when a template has invalid syntax or structure."""

    def __init__(self, name: str, message: str) -> None:
        """Initialize the error.

        Args:
            name: Template name with invalid syntax.
            message: Description of the validation error.
        """
        self.name = name
        super().__init__(f"Invalid template '{name}': {message}")


class MarkdownParseError(PromptError):
    """Raised when a markdown prompt fails to parse.

    This typically occurs when the YAML frontmatter is malformed.
    """

    def __init__(self, name: str, message: str) -> None:
        """Initialize the error.

        Args:
            name: Template name that failed to parse.
            message: Description of the parse error.
        """
        self.name = name
        super().__init__(f"Failed to parse markdown prompt '{name}': {message}")


class TemplateConflictError(PromptError):
    """Raised when multiple template files exist for the same name.

    For example, both 'prompt.md' and 'prompt.jinja2' exist.
    """

    def __init__(self, name: str, version: str, extensions: list[str]) -> None:
        """Initialize the error.

        Args:
            name: Template name with conflicting files.
            version: Template version where conflict was found.
            extensions: List of conflicting file extensions.
        """
        self.name = name
        self.version = version
        self.extensions = extensions
        ext_list = ", ".join(extensions)
        super().__init__(
            f"Multiple template files found for '{name}' (version: {version}): {ext_list}"
        )
