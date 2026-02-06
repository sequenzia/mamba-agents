"""Skills subsystem for modular agent capabilities.

Provides skill discovery, registration, validation, invocation, and lifecycle
management. The ``SkillManager`` facade composes all subsystem components behind
a single unified API.

Quick Start:
    >>> from mamba_agents.skills import SkillManager
    >>> manager = SkillManager()
    >>> skills = manager.discover()
    >>> content = manager.activate("my-skill", arguments="file.txt")

Classes:
    SkillManager: Top-level facade for the skills subsystem.
    Skill: Full skill with loaded content and runtime state.
    SkillInfo: Metadata about a discovered skill (loaded eagerly).
    SkillConfig: Configuration for the skill subsystem.
    ValidationResult: Result from validating a skill against the schema.

Enums:
    SkillScope: Skill discovery scope (project, user, custom).
    TrustLevel: Skill trust level (trusted, untrusted).

Exceptions:
    SkillError: Base exception for all skill-related errors.
    SkillNotFoundError: Skill path does not exist.
    SkillParseError: SKILL.md frontmatter YAML has syntax errors.
    SkillValidationError: Frontmatter fields fail validation.
    SkillLoadError: Permission denied or disk errors during loading.
    SkillConflictError: Duplicate skill names in the same scope.
"""

from __future__ import annotations

from mamba_agents.skills.config import (
    Skill,
    SkillConfig,
    SkillInfo,
    SkillScope,
    TrustLevel,
    ValidationResult,
)
from mamba_agents.skills.errors import (
    SkillConflictError,
    SkillError,
    SkillLoadError,
    SkillNotFoundError,
    SkillParseError,
    SkillValidationError,
)
from mamba_agents.skills.manager import SkillManager

__all__ = [
    "Skill",
    "SkillConfig",
    "SkillConflictError",
    "SkillError",
    "SkillInfo",
    "SkillLoadError",
    "SkillManager",
    "SkillNotFoundError",
    "SkillParseError",
    "SkillScope",
    "SkillValidationError",
    "TrustLevel",
    "ValidationResult",
]
