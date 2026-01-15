"""Prompt management configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    """Configuration for prompt management.

    Attributes:
        prompts_dir: Directory containing prompt templates.
        default_version: Default version to use when not specified.
        file_extension: File extension for prompt templates.
        enable_caching: Whether to cache loaded templates.
        strict_mode: Whether to raise on missing template variables.
    """

    prompts_dir: Path = Field(
        default=Path("prompts"),
        description="Directory containing prompt templates",
    )
    default_version: str = Field(
        default="v1",
        description="Default version to use when not specified",
    )
    file_extension: str = Field(
        default=".jinja2",
        description="File extension for prompt templates",
    )
    enable_caching: bool = Field(
        default=True,
        description="Whether to cache loaded templates",
    )
    strict_mode: bool = Field(
        default=False,
        description="Whether to raise on missing template variables",
    )


class TemplateConfig(BaseModel):
    """Reference to a prompt template.

    Use this to specify which template to load and what variables
    to pass when rendering.

    Attributes:
        name: Template name (e.g., "system/assistant").
        version: Template version. None uses default.
        variables: Variables to pass when rendering.

    Example:
        >>> config = TemplateConfig(
        ...     name="system/assistant",
        ...     variables={"name": "Code Helper"}
        ... )
    """

    name: str = Field(
        description="Template name (e.g., 'system/assistant')",
    )
    version: str | None = Field(
        default=None,
        description="Template version. None uses default.",
    )
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variables to pass when rendering",
    )
