"""SKILL.md file loader and parser.

Parses SKILL.md files with YAML frontmatter and markdown body,
supporting the Agent Skills open standard plus mamba-agents extensions.

Progressive disclosure:
- ``load_metadata(path)`` returns ``SkillInfo`` (frontmatter only, Tier 1)
- ``load_full(path)`` returns ``Skill`` (frontmatter + body, Tier 2)
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from mamba_agents.skills.config import Skill, SkillInfo, SkillScope
from mamba_agents.skills.errors import (
    SkillLoadError,
    SkillNotFoundError,
    SkillParseError,
    SkillValidationError,
)

logger = logging.getLogger(__name__)

# Maximum recommended body size in estimated tokens (chars / 4 heuristic).
_LARGE_BODY_TOKEN_THRESHOLD = 5000

# Valid name pattern: lowercase alphanumeric and hyphens, max 64 chars.
_NAME_PATTERN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_NAME_MAX_LENGTH = 64

# Required frontmatter fields.
_REQUIRED_FIELDS = ("name", "description")

# Known frontmatter keys (YAML hyphenated) mapped to Python attribute names.
# Keys not in this map are silently ignored.
_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "description": "description",
    "license": "license",
    "compatibility": "compatibility",
    "metadata": "metadata",
    "allowed-tools": "allowed_tools",
    "model": "model",
    "context": "execution_mode",
    "disable-model-invocation": "disable_model_invocation",
    "user-invocable": "user_invocable",
    "hooks": "hooks",
    "argument-hint": "argument_hint",
    "agent": "agent",
}


def _split_frontmatter(content: str, path: Path) -> tuple[str, str | None]:
    """Split SKILL.md content into frontmatter YAML and markdown body.

    Expects content beginning with ``---`` on the first line and a closing
    ``---`` delimiter. Only the first pair of markers is used, so horizontal
    rules (``---``) in the body are preserved.

    Args:
        content: Raw file content.
        path: File path (for error messages).

    Returns:
        Tuple of (frontmatter_yaml, body_or_none). Body is ``None`` when
        there is no content after the closing ``---``.

    Raises:
        SkillParseError: If the ``---`` delimiters are missing or malformed.
    """
    # Derive skill name from parent directory for error messages.
    skill_name = path.parent.name or path.stem

    stripped = content.lstrip()
    if not stripped.startswith("---"):
        raise SkillParseError(
            name=skill_name,
            path=path,
            detail="Missing opening '---' frontmatter delimiter",
        )

    # Find the closing --- after the opening one.
    # Skip the first line (opening ---) and search for the next ---.
    first_newline = stripped.index("\n") if "\n" in stripped else len(stripped)
    rest = stripped[first_newline + 1 :]
    closing_idx = None

    for i, line in enumerate(rest.split("\n")):
        if line.strip() == "---":
            closing_idx = i
            break

    if closing_idx is None:
        raise SkillParseError(
            name=skill_name,
            path=path,
            detail="Missing closing '---' frontmatter delimiter",
        )

    # Split at the closing ---
    lines = rest.split("\n")
    frontmatter_yaml = "\n".join(lines[:closing_idx])
    body_lines = lines[closing_idx + 1 :]
    body_text = "\n".join(body_lines)

    # Determine if body is empty (only whitespace after closing ---)
    body: str | None = body_text if body_text.strip() else None

    return frontmatter_yaml, body


def _parse_yaml(yaml_str: str, path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter string into a dictionary.

    Args:
        yaml_str: Raw YAML string extracted from frontmatter.
        path: File path (for error messages).

    Returns:
        Parsed dictionary of frontmatter fields.

    Raises:
        SkillParseError: If the YAML is syntactically invalid.
    """
    skill_name = path.parent.name or path.stem

    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as exc:
        # Extract line information if available.
        detail = str(exc)
        if hasattr(exc, "problem_mark") and exc.problem_mark is not None:
            mark = exc.problem_mark
            detail = f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}: {exc.problem}"
        raise SkillParseError(
            name=skill_name,
            path=path,
            detail=detail,
        ) from exc

    if data is None:
        # Empty YAML section
        return {}

    if not isinstance(data, dict):
        raise SkillParseError(
            name=skill_name,
            path=path,
            detail="Frontmatter must be a YAML mapping, got " + type(data).__name__,
        )

    return data


def _validate_frontmatter(
    data: dict[str, Any],
    path: Path,
) -> None:
    """Validate frontmatter fields against the skill schema.

    Checks required fields, name format, and name-directory match.

    Args:
        data: Parsed frontmatter dictionary.
        path: Path to the SKILL.md file.

    Raises:
        SkillValidationError: If any validation check fails.
    """
    errors: list[str] = []

    # Check required fields.
    missing = [f for f in _REQUIRED_FIELDS if f not in data or not data[f]]
    if missing:
        for field in missing:
            errors.append(f"Missing required field: {field}")

    # Get name for further checks (may be absent).
    name = data.get("name")

    if name is not None:
        name_str = str(name)

        # Check length.
        if len(name_str) > _NAME_MAX_LENGTH:
            errors.append(
                f"Name '{name_str}' exceeds maximum length of {_NAME_MAX_LENGTH} characters"
            )

        # Check format.
        if not _NAME_PATTERN.match(name_str):
            errors.append(
                f"Name '{name_str}' is invalid: must contain only lowercase "
                "alphanumeric characters and hyphens, and must not start or end "
                "with a hyphen"
            )

        # Check name matches parent directory.
        parent_dir_name = path.parent.name
        if parent_dir_name and name_str != parent_dir_name:
            errors.append(
                f"Name '{name_str}' does not match parent directory '{parent_dir_name}'"
            )

    # Determine the skill name for the error (use whatever we have).
    error_name = str(name) if name else path.parent.name or "unknown"

    if errors:
        raise SkillValidationError(
            name=error_name,
            errors=errors,
            path=path,
        )


def _map_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Map YAML hyphenated keys to Python underscore attribute names.

    Unknown keys are silently dropped.

    Args:
        data: Parsed frontmatter dictionary with original YAML keys.

    Returns:
        Dictionary with Python-friendly attribute names.
    """
    mapped: dict[str, Any] = {}
    for yaml_key, value in data.items():
        python_key = _FIELD_MAP.get(yaml_key)
        if python_key is not None:
            mapped[python_key] = value
    return mapped


def _read_file(path: Path) -> str:
    """Read a SKILL.md file, handling not-found and permission errors.

    Args:
        path: Path to the SKILL.md file.

    Returns:
        File content as a string.

    Raises:
        SkillNotFoundError: If the file does not exist.
        SkillLoadError: On permission denied or other IO errors.
    """
    skill_name = path.parent.name or path.stem

    if not path.exists():
        raise SkillNotFoundError(name=skill_name, path=path)

    try:
        return path.read_text(encoding="utf-8")
    except PermissionError as exc:
        raise SkillLoadError(name=skill_name, path=path, cause=exc) from exc
    except OSError as exc:
        raise SkillLoadError(name=skill_name, path=path, cause=exc) from exc


def load_metadata(
    path: str | Path,
    *,
    scope: SkillScope = SkillScope.PROJECT,
) -> SkillInfo:
    """Load skill metadata from a SKILL.md file (Tier 1 — frontmatter only).

    Reads and parses the YAML frontmatter without processing the markdown
    body. Use this for fast discovery scans where only metadata is needed.

    Args:
        path: Path to the SKILL.md file.
        scope: Discovery scope for the skill.

    Returns:
        ``SkillInfo`` populated with all recognised frontmatter fields.

    Raises:
        SkillNotFoundError: If the file does not exist.
        SkillLoadError: On permission denied or other IO errors.
        SkillParseError: If frontmatter delimiters or YAML syntax is invalid.
        SkillValidationError: If required fields are missing or name is invalid.
    """
    file_path = Path(path)
    content = _read_file(file_path)
    frontmatter_yaml, _ = _split_frontmatter(content, file_path)
    data = _parse_yaml(frontmatter_yaml, file_path)
    _validate_frontmatter(data, file_path)
    mapped = _map_fields(data)

    # Build SkillInfo with mapped fields.
    return SkillInfo(
        name=mapped["name"],
        description=mapped["description"],
        path=file_path.parent,
        scope=scope,
        license=mapped.get("license"),
        compatibility=mapped.get("compatibility"),
        metadata=mapped.get("metadata"),
        allowed_tools=mapped.get("allowed_tools"),
        model=mapped.get("model"),
        execution_mode=mapped.get("execution_mode"),
        agent=mapped.get("agent"),
        disable_model_invocation=mapped.get("disable_model_invocation", False),
        user_invocable=mapped.get("user_invocable", True),
        argument_hint=mapped.get("argument_hint"),
        hooks=mapped.get("hooks"),
    )


def load_full(
    path: str | Path,
    *,
    scope: SkillScope = SkillScope.PROJECT,
) -> Skill:
    """Load a complete skill from a SKILL.md file (Tier 2 — frontmatter + body).

    Reads both the YAML frontmatter and the markdown body. Issues a warning
    when the body exceeds the recommended token threshold.

    Args:
        path: Path to the SKILL.md file.
        scope: Discovery scope for the skill.

    Returns:
        ``Skill`` containing metadata (``info``) and the markdown body.

    Raises:
        SkillNotFoundError: If the file does not exist.
        SkillLoadError: On permission denied or other IO errors.
        SkillParseError: If frontmatter delimiters or YAML syntax is invalid.
        SkillValidationError: If required fields are missing or name is invalid.
    """
    file_path = Path(path)
    content = _read_file(file_path)
    frontmatter_yaml, body = _split_frontmatter(content, file_path)
    data = _parse_yaml(frontmatter_yaml, file_path)
    _validate_frontmatter(data, file_path)
    mapped = _map_fields(data)

    # Warn if body is large (estimated tokens = chars / 4).
    if body is not None:
        estimated_tokens = len(body) // 4
        if estimated_tokens > _LARGE_BODY_TOKEN_THRESHOLD:
            logger.warning(
                "Skill '%s' body is approximately %d tokens (recommended: <%d). "
                "Consider splitting into references.",
                mapped["name"],
                estimated_tokens,
                _LARGE_BODY_TOKEN_THRESHOLD,
            )

    info = SkillInfo(
        name=mapped["name"],
        description=mapped["description"],
        path=file_path.parent,
        scope=scope,
        license=mapped.get("license"),
        compatibility=mapped.get("compatibility"),
        metadata=mapped.get("metadata"),
        allowed_tools=mapped.get("allowed_tools"),
        model=mapped.get("model"),
        execution_mode=mapped.get("execution_mode"),
        agent=mapped.get("agent"),
        disable_model_invocation=mapped.get("disable_model_invocation", False),
        user_invocable=mapped.get("user_invocable", True),
        argument_hint=mapped.get("argument_hint"),
        hooks=mapped.get("hooks"),
    )

    return Skill(info=info, body=body)
