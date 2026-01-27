"""Prompt template class."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jinja2 import Template as Jinja2Template


class TemplateType(Enum):
    """Type of prompt template.

    Attributes:
        JINJA2: Jinja2 template with {{ var }} syntax.
        MARKDOWN: Markdown template with {var} syntax and YAML frontmatter.
    """

    JINJA2 = "jinja2"
    MARKDOWN = "markdown"


@dataclass
class PromptTemplate:
    """A renderable prompt template.

    Supports both Jinja2 templates ({{ var }} syntax) and markdown templates
    ({var} syntax with YAML frontmatter).

    Attributes:
        name: Template name (e.g., "system/assistant").
        version: Template version (e.g., "v1").
        source: Raw template source code.
        template_type: Type of template (JINJA2 or MARKDOWN).

    Example:
        Jinja2 template:
        >>> template = PromptTemplate(
        ...     name="system/assistant",
        ...     version="v1",
        ...     source="You are {{ name }}.",
        ... )
        >>> template.render(name="a helpful assistant")
        'You are a helpful assistant.'

        Markdown template:
        >>> template = PromptTemplate(
        ...     name="system/assistant",
        ...     version="v1",
        ...     source="You are {name}.",
        ...     template_type=TemplateType.MARKDOWN,
        ... )
        >>> template.render(name="a helpful assistant")
        'You are a helpful assistant.'
    """

    name: str
    version: str
    source: str
    template_type: TemplateType = TemplateType.JINJA2
    _compiled: Jinja2Template | None = field(default=None, repr=False, compare=False)
    _default_variables: dict[str, Any] = field(default_factory=dict, repr=False)
    _strict: bool = field(default=False, repr=False)

    def render(self, **variables: Any) -> str:
        """Render the template with the given variables.

        Args:
            **variables: Variables to substitute in the template.

        Returns:
            Rendered template string.

        Raises:
            TemplateRenderError: If rendering fails.
        """
        # Merge default variables with provided ones
        merged_vars = {**self._default_variables, **variables}

        if self.template_type == TemplateType.MARKDOWN:
            return self._render_markdown(merged_vars)
        return self._render_jinja2(merged_vars)

    def _render_jinja2(self, variables: dict[str, Any]) -> str:
        """Render as a Jinja2 template.

        Args:
            variables: Variables to substitute.

        Returns:
            Rendered template string.

        Raises:
            TemplateRenderError: If rendering fails.
        """
        from jinja2 import Template as Jinja2Template
        from jinja2 import UndefinedError

        from mamba_agents.prompts.errors import TemplateRenderError

        try:
            if self._compiled is None:
                self._compiled = Jinja2Template(self.source)
            return self._compiled.render(**variables)
        except UndefinedError as e:
            raise TemplateRenderError(self.name, e) from e
        except Exception as e:
            raise TemplateRenderError(self.name, e) from e

    def _render_markdown(self, variables: dict[str, Any]) -> str:
        """Render as a markdown template.

        Args:
            variables: Variables to substitute.

        Returns:
            Rendered template string.

        Raises:
            TemplateRenderError: If rendering fails (strict mode).
        """
        from mamba_agents.prompts.markdown import render_markdown_prompt, unescape_braces

        result = render_markdown_prompt(
            content=self.source,
            variables=variables,
            strict=self._strict,
            name=self.name,
        )
        return unescape_braces(result)

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
            template_type=self.template_type,
            _compiled=self._compiled,
            _default_variables={**self._default_variables, **variables},
            _strict=self._strict,
        )

    def get_variables(self) -> set[str]:
        """Get the set of variable names used in this template.

        Returns:
            Set of variable names found in the template.
        """
        if self.template_type == TemplateType.MARKDOWN:
            from mamba_agents.prompts.markdown import get_markdown_variables

            return get_markdown_variables(self.source)

        from jinja2 import Environment, meta

        env = Environment()
        ast = env.parse(self.source)
        return meta.find_undeclared_variables(ast)

    def __str__(self) -> str:
        """Return the rendered template with default variables."""
        return self.render()
