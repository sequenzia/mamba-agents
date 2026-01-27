"""Prompt management module.

This module provides comprehensive prompt management capabilities:
- File-based prompt storage with Jinja2 (.jinja2) or Markdown (.md) templates
- Directory-based versioning (prompts/v1/, prompts/v2/)
- Template inheritance with Jinja2 extends/blocks
- Markdown templates with YAML frontmatter and {var} syntax
- Runtime template registration for testing

Example:
    Basic usage with Jinja2 templates:

    >>> from mamba_agents.prompts import PromptManager, TemplateConfig
    >>>
    >>> manager = PromptManager()
    >>> prompt = manager.render("system/assistant", name="Code Helper")

    Markdown template file (prompts/v1/system/assistant.md):

        ---
        variables:
          assistant_name: Claude
        ---
        You are {assistant_name}, a helpful AI assistant.

    Using with Agent:

    >>> from mamba_agents import Agent
    >>> from mamba_agents.prompts import TemplateConfig
    >>>
    >>> agent = Agent(
    ...     "openai:gpt-4",
    ...     system_prompt=TemplateConfig(
    ...         name="system/assistant",
    ...         variables={"name": "Code Helper"}
    ...     )
    ... )

    Testing with registered templates:

    >>> manager = PromptManager()
    >>> manager.register("test/greeting", "Hello, {{ name }}!")
    >>> manager.render("test/greeting", name="World")
    'Hello, World!'
"""

from mamba_agents.prompts.config import PromptConfig, TemplateConfig
from mamba_agents.prompts.errors import (
    MarkdownParseError,
    PromptError,
    PromptNotFoundError,
    TemplateConflictError,
    TemplateRenderError,
    TemplateValidationError,
)
from mamba_agents.prompts.manager import PromptManager
from mamba_agents.prompts.template import PromptTemplate, TemplateType

__all__ = [
    "MarkdownParseError",
    "PromptConfig",
    "PromptError",
    "PromptManager",
    "PromptNotFoundError",
    "PromptTemplate",
    "TemplateConfig",
    "TemplateConflictError",
    "TemplateRenderError",
    "TemplateType",
    "TemplateValidationError",
]
