"""Subagent markdown config loader.

Loads subagent definitions from ``.mamba/agents/{name}.md`` and
``~/.mamba/agents/{name}.md`` files. Each file contains YAML frontmatter
with subagent configuration fields and an optional markdown body that
becomes the subagent's system prompt.

Example file format::

    ---
    name: researcher
    description: Research subagent for gathering information
    tools: [read_file, grep_search]
    model: gpt-4
    skills: [web-search]
    ---

    You are a research assistant. Your job is to gather information...
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from mamba_agents.subagents.config import SubagentConfig
from mamba_agents.subagents.errors import SubagentConfigError

# Match YAML frontmatter delimited by ---
# The frontmatter content can be empty (just newlines) or contain YAML
_FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)^---\s*\n?(.*)$", re.DOTALL | re.MULTILINE)

# Hyphenated YAML keys that map to Python underscore equivalents
_KEY_MAPPING: dict[str, str] = {
    "disallowed-tools": "disallowed_tools",
    "max-turns": "max_turns",
    "system-prompt": "system_prompt",
}


def _parse_frontmatter(source: str, path: Path) -> tuple[dict[str, Any], str | None]:
    """Parse YAML frontmatter and body from a markdown source.

    Args:
        source: Raw markdown file content.
        path: File path for error messages.

    Returns:
        Tuple of (frontmatter dict, body string or None).

    Raises:
        SubagentConfigError: If frontmatter is missing or YAML is invalid.
    """
    match = _FRONTMATTER_PATTERN.match(source)

    if not match:
        raise SubagentConfigError(
            name=path.stem,
            detail=f"No YAML frontmatter found in {path}. File must start with '---' delimiters.",
        )

    frontmatter_yaml, body = match.groups()

    try:
        frontmatter = yaml.safe_load(frontmatter_yaml) or {}
    except yaml.YAMLError as e:
        raise SubagentConfigError(
            name=path.stem,
            detail=f"Invalid YAML in {path}: {e}",
        ) from e

    if not isinstance(frontmatter, dict):
        raise SubagentConfigError(
            name=path.stem,
            detail=f"Frontmatter must be a YAML mapping, got {type(frontmatter).__name__}",
        )

    # Normalize body: strip whitespace, treat empty as None
    body_text = body.strip() if body else None
    if body_text == "":
        body_text = None

    return frontmatter, body_text


def _normalize_keys(data: dict[str, Any]) -> dict[str, Any]:
    """Map hyphenated YAML keys to Python underscore equivalents.

    Args:
        data: Raw frontmatter dictionary.

    Returns:
        Dictionary with normalized keys.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        normalized = _KEY_MAPPING.get(key, key.replace("-", "_"))
        result[normalized] = value
    return result


def load_subagent_config(path: Path) -> SubagentConfig:
    """Load a subagent configuration from a markdown file.

    Parses a ``.md`` file containing YAML frontmatter and an optional
    markdown body. The frontmatter fields map to ``SubagentConfig`` attributes,
    and the markdown body becomes the ``system_prompt``.

    Args:
        path: Path to the ``.md`` file.

    Returns:
        Parsed ``SubagentConfig`` instance.

    Raises:
        SubagentConfigError: If the file cannot be read, has no frontmatter,
            contains invalid YAML, or is missing required fields.
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as e:
        raise SubagentConfigError(
            name=path.stem,
            detail=f"Cannot read file {path}: {e}",
        ) from e

    frontmatter, body = _parse_frontmatter(source, path)
    data = _normalize_keys(frontmatter)

    # Markdown body becomes system_prompt if not set in frontmatter
    if body is not None and "system_prompt" not in data:
        data["system_prompt"] = body

    try:
        return SubagentConfig(**data)
    except ValidationError as e:
        # Extract meaningful error details from pydantic
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        raise SubagentConfigError(
            name=data.get("name", path.stem),
            detail=f"Validation failed: {'; '.join(errors)}",
        ) from e


def discover_subagents(
    project_dir: Path | None = None,
    user_dir: Path | None = None,
) -> list[SubagentConfig]:
    """Discover subagent configs from project and user directories.

    Scans ``.mamba/agents/`` in the project directory and
    ``~/.mamba/agents/`` in the user home directory for ``.md`` files.
    Each file is parsed into a ``SubagentConfig``.

    Args:
        project_dir: Project-level agents directory.
            Defaults to ``.mamba/agents/`` relative to cwd.
        user_dir: User-level agents directory.
            Defaults to ``~/.mamba/agents/``.

    Returns:
        List of discovered ``SubagentConfig`` instances. Returns an
        empty list if no directories exist or no files are found.

    Raises:
        SubagentConfigError: If a discovered file has invalid content.
    """
    if project_dir is None:
        project_dir = Path(".mamba/agents")
    if user_dir is None:
        user_dir = Path("~/.mamba/agents").expanduser()

    configs: list[SubagentConfig] = []

    for directory in [project_dir, user_dir]:
        resolved = directory.expanduser()
        if not resolved.is_dir():
            continue

        for md_file in sorted(resolved.glob("*.md")):
            if md_file.is_file():
                config = load_subagent_config(md_file)
                configs.append(config)

    return configs
