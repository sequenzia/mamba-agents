"""Skill validation and trust level enforcement.

Validates SKILL.md frontmatter against the Agent Skills specification
plus mamba-agents extensions, and enforces trust level restrictions on
untrusted skills.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mamba_agents.skills.config import (
    SkillInfo,
    SkillScope,
    TrustLevel,
    ValidationResult,
)

# Name format: lowercase alphanumeric + hyphens, max 64 chars
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_NAME_MAX_LENGTH = 64

# Known frontmatter fields from the Agent Skills spec + mamba extensions.
# Unknown fields produce warnings, not errors.
_KNOWN_FIELDS: set[str] = {
    # Agent Skills spec fields
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
    # mamba extensions
    "model",
    "context",
    "execution-mode",
    "agent",
    "disable-model-invocation",
    "user-invocable",
    "hooks",
    "argument-hint",
}

# Fields that map to Python attribute names (hyphenated -> underscored)
_FIELD_ALIASES: dict[str, str] = {
    "allowed-tools": "allowed_tools",
    "disable-model-invocation": "disable_model_invocation",
    "user-invocable": "user_invocable",
    "execution-mode": "execution_mode",
    "argument-hint": "argument_hint",
}

# Type expectations for optional fields (field_name -> expected_type_description)
_FIELD_TYPES: dict[str, tuple[type | tuple[type, ...], str]] = {
    "name": (str, "string"),
    "description": (str, "string"),
    "license": (str, "string"),
    "compatibility": (str, "string"),
    "metadata": (dict, "mapping (key-value pairs)"),
    "allowed-tools": (list, "list of strings"),
    "model": (str, "string"),
    "context": (str, "string"),
    "execution-mode": (str, "string"),
    "agent": (str, "string"),
    "disable-model-invocation": (bool, "boolean"),
    "user-invocable": (bool, "boolean"),
    "hooks": (dict, "mapping (key-value pairs)"),
    "argument-hint": (str, "string"),
}


def validate_frontmatter(data: dict[str, Any]) -> ValidationResult:
    """Validate parsed frontmatter data against the skill schema.

    Checks required fields, field types, name format, and reports
    unknown fields as warnings. Does not raise exceptions; all
    issues are returned as structured errors and warnings.

    Args:
        data: Parsed YAML frontmatter as a dictionary.

    Returns:
        ValidationResult with valid flag, errors, and warnings.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check required fields
    if "name" not in data:
        errors.append("Missing required field: 'name'")
    if "description" not in data:
        errors.append("Missing required field: 'description'")

    # Validate field types for all present fields
    for field_name, (expected_type, type_desc) in _FIELD_TYPES.items():
        if field_name in data:
            value = data[field_name]
            if not isinstance(value, expected_type):
                errors.append(
                    f"Field '{field_name}' must be {type_desc}, "
                    f"got {type(value).__name__}"
                )

    # Validate name format if present and is a string
    if "name" in data and isinstance(data["name"], str):
        name = data["name"]
        if len(name) > _NAME_MAX_LENGTH:
            errors.append(
                f"Field 'name' exceeds maximum length of {_NAME_MAX_LENGTH} characters "
                f"(got {len(name)})"
            )
        elif len(name) == 0:
            errors.append("Field 'name' must not be empty")
        elif not _NAME_PATTERN.match(name):
            errors.append(
                f"Field 'name' must be lowercase alphanumeric with hyphens "
                f"(pattern: {_NAME_PATTERN.pattern}), got '{name}'"
            )

    # Validate allowed-tools items are strings
    if "allowed-tools" in data and isinstance(data["allowed-tools"], list):
        for i, item in enumerate(data["allowed-tools"]):
            if not isinstance(item, str):
                errors.append(
                    f"Field 'allowed-tools' item at index {i} must be a string, "
                    f"got {type(item).__name__}"
                )

    # Check for unknown fields
    for key in data:
        if key not in _KNOWN_FIELDS:
            warnings.append(f"Unknown frontmatter field: '{key}'")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate(path: Path) -> ValidationResult:
    """Validate a SKILL.md file at the given path.

    Reads the file, parses frontmatter, validates against the schema,
    and checks that the skill name matches the parent directory name.

    Args:
        path: Path to the SKILL.md file or its parent directory.

    Returns:
        ValidationResult with valid flag, errors, warnings, and skill_path.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Resolve to SKILL.md file
    if path.is_dir():
        skill_file = path / "SKILL.md"
        skill_dir = path
    else:
        skill_file = path
        skill_dir = path.parent

    # Check file exists
    if not skill_file.exists():
        return ValidationResult(
            valid=False,
            errors=[f"SKILL.md not found at {skill_file}"],
            skill_path=skill_dir,
        )

    # Read and parse frontmatter
    try:
        content = skill_file.read_text(encoding="utf-8")
    except OSError as exc:
        return ValidationResult(
            valid=False,
            errors=[f"Failed to read {skill_file}: {exc}"],
            skill_path=skill_dir,
        )

    data = _parse_frontmatter(content)
    if data is None:
        return ValidationResult(
            valid=False,
            errors=["SKILL.md does not contain valid YAML frontmatter (missing '---' markers)"],
            skill_path=skill_dir,
        )

    # Validate frontmatter fields
    fm_result = validate_frontmatter(data)
    errors.extend(fm_result.errors)
    warnings.extend(fm_result.warnings)

    # Check name-directory match
    if "name" in data and isinstance(data["name"], str):
        dir_name = skill_dir.name
        if data["name"] != dir_name:
            errors.append(
                f"Skill name '{data['name']}' does not match parent directory name '{dir_name}'"
            )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        skill_path=skill_dir,
    )


def resolve_trust_level(
    scope: SkillScope,
    path: Path,
    trusted_paths: list[Path] | None = None,
) -> TrustLevel:
    """Resolve the trust level for a skill based on its scope and path.

    Project and user skills default to trusted. Custom path skills default
    to untrusted unless their path appears in ``trusted_paths``.

    Args:
        scope: Discovery scope of the skill.
        path: Filesystem path of the skill directory.
        trusted_paths: Additional paths to treat as trusted.

    Returns:
        Resolved TrustLevel for the skill.
    """
    if scope in (SkillScope.PROJECT, SkillScope.USER):
        return TrustLevel.TRUSTED

    # Custom scope: check if the path is in trusted_paths
    if trusted_paths:
        resolved_path = path.resolve()
        for tp in trusted_paths:
            resolved_tp = tp.resolve()
            # Check if the skill path is under a trusted path
            try:
                resolved_path.relative_to(resolved_tp)
                return TrustLevel.TRUSTED
            except ValueError:
                continue

    return TrustLevel.UNTRUSTED


def check_trust_restrictions(skill: SkillInfo) -> list[str]:
    """Check if an untrusted skill uses restricted capabilities.

    Returns a list of violation messages for capabilities that untrusted
    skills are not permitted to use. Returns an empty list for trusted
    skills or skills with no violations.

    Args:
        skill: Skill metadata to check.

    Returns:
        List of restriction violation messages (empty if no violations).
    """
    if skill.trust_level == TrustLevel.TRUSTED:
        return []

    violations: list[str] = []

    # Untrusted skills cannot use hooks
    if skill.hooks:
        violations.append(
            "Untrusted skill cannot use 'hooks' to register lifecycle hooks"
        )

    # Untrusted skills cannot use context: fork (execution_mode = "fork")
    if skill.execution_mode == "fork":
        violations.append(
            "Untrusted skill cannot use 'context: fork' to spawn subagents"
        )

    # Untrusted skills cannot use allowed_tools to extend tool access
    if skill.allowed_tools:
        violations.append(
            "Untrusted skill cannot use 'allowed-tools' to grant tool access "
            "beyond the agent's existing tools"
        )

    return violations


def _parse_frontmatter(content: str) -> dict[str, Any] | None:
    """Parse YAML frontmatter from markdown content.

    Extracts the YAML block between the first pair of ``---`` markers.

    Args:
        content: Full markdown file content.

    Returns:
        Parsed YAML data as a dictionary, or None if no frontmatter found.
    """
    import yaml

    content = content.strip()
    if not content.startswith("---"):
        return None

    # Find the closing --- marker
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return None

    yaml_str = content[3:end_idx].strip()
    if not yaml_str:
        return {}

    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError:
        return None

    if not isinstance(data, dict):
        return None

    return data
