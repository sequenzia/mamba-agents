"""Prompt template class."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Template as Jinja2Template


@dataclass
class PromptTemplate:
    """A renderable prompt template.

    Wraps a Jinja2 template with metadata and provides a clean
    interface for rendering with variables.

    Attributes:
        name: Template name (e.g., "system/assistant").
        version: Template version (e.g., "v1").
        source: Raw template source code.

    Example:
        >>> template = PromptTemplate(
        ...     name="system/assistant",
        ...     version="v1",
        ...     source="You are {{ name }}.",
        ... )
        >>> template.render(name="a helpful assistant")
        'You are a helpful assistant.'
    """

    name: str
    version: str
    source: str
    _compiled: Jinja2Template | None = field(default=None, repr=False, compare=False)
    _default_variables: dict[str, Any] = field(default_factory=dict, repr=False)

    def render(self, **variables: Any) -> str:
        """Render the template with the given variables.

        Args:
            **variables: Variables to substitute in the template.

        Returns:
            Rendered template string.

        Raises:
            TemplateRenderError: If rendering fails.
        """
        from jinja2 import Template as Jinja2Template
        from jinja2 import UndefinedError

        from mamba_agents.prompts.errors import TemplateRenderError

        # Merge default variables with provided ones
        merged_vars = {**self._default_variables, **variables}

        try:
            if self._compiled is None:
                self._compiled = Jinja2Template(self.source)
            return self._compiled.render(**merged_vars)
        except UndefinedError as e:
            raise TemplateRenderError(self.name, e) from e
        except Exception as e:
            raise TemplateRenderError(self.name, e) from e

    def with_variables(self, **variables: Any) -> PromptTemplate:
        """Create a new template with default variables set.

        This is useful for partial application of variables.

        Args:
            **variables: Default variables for the new template.

        Returns:
            New PromptTemplate with default variables set.

        Example:
            >>> base = PromptTemplate("sys", "v1", "Hello {{ name }}, you are {{ role }}.")
            >>> greeter = base.with_variables(name="Claude")
            >>> greeter.render(role="helpful")
            'Hello Claude, you are helpful.'
        """
        return PromptTemplate(
            name=self.name,
            version=self.version,
            source=self.source,
            _compiled=self._compiled,
            _default_variables={**self._default_variables, **variables},
        )

    def get_variables(self) -> set[str]:
        """Get the set of variable names used in this template.

        Returns:
            Set of variable names found in the template.
        """
        from jinja2 import Environment, meta

        env = Environment()
        ast = env.parse(self.source)
        return meta.find_undeclared_variables(ast)

    def __str__(self) -> str:
        """Return the rendered template with default variables."""
        return self.render()
