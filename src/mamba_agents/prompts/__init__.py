"""Prompt management module.

This module provides comprehensive prompt management capabilities:
- File-based prompt storage with Jinja2 templating
- Directory-based versioning (prompts/v1/, prompts/v2/)
- Template inheritance with Jinja2 extends/blocks
- Runtime template registration for testing

Example:
    Basic usage with file-based templates:

    >>> from mamba_agents.prompts import PromptManager, TemplateConfig
    >>>
    >>> manager = PromptManager()
    >>> prompt = manager.render("system/assistant", name="Code Helper")

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
    PromptError,
    PromptNotFoundError,
    TemplateRenderError,
    TemplateValidationError,
)
from mamba_agents.prompts.manager import PromptManager
from mamba_agents.prompts.template import PromptTemplate

__all__ = [
    "PromptConfig",
    "PromptError",
    "PromptManager",
    "PromptNotFoundError",
    "PromptTemplate",
    "TemplateConfig",
    "TemplateRenderError",
    "TemplateValidationError",
]
