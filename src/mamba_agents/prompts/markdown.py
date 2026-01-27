"""Markdown prompt parsing and rendering.

This module handles parsing markdown prompts with YAML frontmatter
and rendering them with variable substitution using {var} syntax.

Example markdown prompt:
    ---
    description: Basic assistant system prompt
    variables:
      assistant_name: Claude
      tone: professional
    ---

    You are {assistant_name}, a helpful AI assistant.
    Your tone should be {tone} and clear.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from mamba_agents.prompts.errors import MarkdownParseError, TemplateRenderError

# Match YAML frontmatter delimited by ---
# The frontmatter content can be empty (just newlines) or contain YAML
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)^---\s*\n?(.*)$", re.DOTALL | re.MULTILINE)

# Match {var} but not {{escaped}} - captures the variable name
# Negative lookbehind (?<!\{) ensures no { before
# Negative lookahead (?!\}) ensures no } after
VARIABLE_PATTERN = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")


@dataclass
class MarkdownPromptData:
    """Parsed data from a markdown prompt.

    Attributes:
        content: The markdown content (after frontmatter).
        metadata: Metadata from frontmatter (excluding variables).
        default_variables: Default variable values from frontmatter.
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    default_variables: dict[str, Any] = field(default_factory=dict)


def parse_markdown_prompt(source: str, name: str) -> MarkdownPromptData:
    """Parse a markdown prompt with YAML frontmatter.

    Args:
        source: Raw markdown source with optional frontmatter.
        name: Template name for error messages.

    Returns:
        MarkdownPromptData with parsed content, metadata, and defaults.

    Raises:
        MarkdownParseError: If YAML frontmatter is malformed.

    Example:
        >>> data = parse_markdown_prompt('''---
        ... variables:
        ...   name: World
        ... ---
        ... Hello, {name}!
        ... ''', "test")
        >>> data.content
        'Hello, {name}!'
        >>> data.default_variables
        {'name': 'World'}
    """
    match = FRONTMATTER_PATTERN.match(source)

    # No frontmatter - return content as-is
    if not match:
        return MarkdownPromptData(content=source.strip())

    frontmatter_yaml, content = match.groups()

    try:
        frontmatter = yaml.safe_load(frontmatter_yaml) or {}
    except yaml.YAMLError as e:
        raise MarkdownParseError(name, f"Invalid YAML frontmatter: {e}") from e

    # Ensure frontmatter is a dict
    if not isinstance(frontmatter, dict):
        raise MarkdownParseError(
            name,
            f"Frontmatter must be a YAML mapping, got {type(frontmatter).__name__}",
        )

    # Extract variables (with default empty dict if not present)
    default_variables = frontmatter.pop("variables", {}) or {}

    # Ensure variables is a dict
    if not isinstance(default_variables, dict):
        raise MarkdownParseError(
            name,
            f"'variables' must be a mapping, got {type(default_variables).__name__}",
        )

    return MarkdownPromptData(
        content=content.strip(),
        metadata=frontmatter,
        default_variables=default_variables,
    )


def render_markdown_prompt(
    content: str,
    variables: dict[str, Any],
    strict: bool = False,
    name: str = "unknown",
) -> str:
    """Render a markdown prompt by substituting {var} placeholders.

    Args:
        content: Markdown content with {var} placeholders.
        variables: Variables to substitute.
        strict: If True, raise error on missing variables.
        name: Template name for error messages.

    Returns:
        Rendered content with variables substituted.

    Raises:
        TemplateRenderError: If strict=True and a variable is missing.

    Example:
        >>> render_markdown_prompt("Hello, {name}!", {"name": "World"})
        'Hello, World!'
        >>> render_markdown_prompt("Hello, {name}!", {}, strict=True)
        Traceback (most recent call last):
        ...
        TemplateRenderError: ...
    """
    # Find all variable references
    found_vars = get_markdown_variables(content)

    # Check for missing variables in strict mode
    if strict:
        missing = found_vars - set(variables.keys())
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise TemplateRenderError(
                name,
                ValueError(f"Missing required variables: {missing_list}"),
            )

    def replace_var(match: re.Match[str]) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        # Not in variables - leave unchanged (non-strict mode)
        return match.group(0)

    return VARIABLE_PATTERN.sub(replace_var, content)


def get_markdown_variables(content: str) -> set[str]:
    """Extract variable names from markdown content.

    Args:
        content: Markdown content with {var} placeholders.

    Returns:
        Set of variable names found in the content.

    Example:
        >>> get_markdown_variables("Hello, {name}! You are {role}.")
        {'name', 'role'}
        >>> get_markdown_variables("No variables here")
        set()
    """
    return set(VARIABLE_PATTERN.findall(content))


def unescape_braces(content: str) -> str:
    """Convert escaped braces back to single braces.

    Converts {{ to { and }} to } for output.
    This is called after variable substitution.

    Args:
        content: Content with escaped braces.

    Returns:
        Content with braces unescaped.

    Example:
        >>> unescape_braces("Use {{var}} for literal braces")
        'Use {var} for literal braces'
    """
    return content.replace("{{", "{").replace("}}", "}")
