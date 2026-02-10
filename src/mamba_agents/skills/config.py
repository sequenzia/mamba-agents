"""Skill data models, enums, and configuration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, PrivateAttr, model_validator


class SkillScope(str, Enum):
    """Skill discovery scope.

    Determines where a skill was discovered and its default trust level.

    Attributes:
        PROJECT: Project-level skill from ``.mamba/skills/``.
        USER: User-level skill from ``~/.mamba/skills/``.
        CUSTOM: Skill from an explicitly configured custom path.
    """

    PROJECT = "project"
    USER = "user"
    CUSTOM = "custom"


class TrustLevel(str, Enum):
    """Skill trust level.

    Controls what capabilities a skill is permitted to use.

    Attributes:
        TRUSTED: Full access to tools and model invocation.
        UNTRUSTED: Restricted access; hooks and certain tools are blocked.
    """

    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"


@dataclass
class SkillInfo:
    """Metadata about a discovered skill (loaded eagerly).

    Contains all frontmatter fields from the Agent Skills specification
    plus mamba-agents extensions. Required fields must be provided at
    construction time; all optional fields default to ``None`` or their
    specified defaults.

    Attributes:
        name: Validated skill identifier.
        description: Human-readable description of what the skill does.
        path: Directory containing the SKILL.md file.
        scope: Discovery scope (project, user, or custom).
        license: SPDX license identifier for the skill.
        compatibility: Compatibility string (e.g., tool or version constraints).
        metadata: Arbitrary key-value metadata from frontmatter.
        allowed_tools: List of tool names this skill is permitted to use.
        model: Model override for skill execution.
        execution_mode: Execution mode (``"fork"`` or ``None``).
        agent: Subagent config name when execution_mode is ``"fork"``.
        disable_model_invocation: Whether to disable LLM calls for this skill.
        user_invocable: Whether users can invoke this skill directly.
        argument_hint: Hint text for skill argument input.
        hooks: Reserved for future lifecycle hooks (not implemented in v1).
        trust_level: Resolved trust level for this skill.
    """

    name: str
    description: str
    path: Path
    scope: SkillScope
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] | None = None
    allowed_tools: list[str] | None = None
    model: str | None = None
    execution_mode: str | None = None
    agent: str | None = None
    disable_model_invocation: bool = False
    user_invocable: bool = True
    argument_hint: str | None = None
    hooks: dict[str, Any] | None = None
    trust_level: TrustLevel = TrustLevel.TRUSTED


class Skill(BaseModel):
    """Full skill with loaded content.

    Wraps a ``SkillInfo`` with lazily-loaded body content and runtime state.
    The ``_tools`` private attribute holds registered tool callables and is
    excluded from serialization.

    Attributes:
        info: Skill metadata (always loaded).
        body: SKILL.md markdown body (lazy loaded, ``None`` until loaded).
        is_active: Whether the skill is currently activated.
    """

    model_config = {"arbitrary_types_allowed": True}

    info: SkillInfo
    body: str | None = None
    is_active: bool = False
    _tools: list[Callable[..., Any]] = PrivateAttr(default_factory=list)


class SkillConfig(BaseModel):
    """Configuration for the skill subsystem.

    Attributes:
        skills_dirs: Directories to scan for project-level skills.
        user_skills_dir: User-level skills directory (``~`` is expanded).
        custom_paths: Additional search paths for skill discovery.
        auto_discover: Whether to auto-discover skills on startup.
        namespace_tools: Whether to prefix skill tools with the skill name.
        trusted_paths: Paths to treat as trusted (in addition to project/user).
    """

    skills_dirs: list[Path] = Field(
        default_factory=lambda: [Path(".mamba/skills")],
        description="Directories to scan for skills",
    )
    user_skills_dir: Path = Field(
        default=Path("~/.mamba/skills"),
        description="User-level skills directory",
    )
    custom_paths: list[Path] = Field(
        default_factory=list,
        description="Additional search paths",
    )
    auto_discover: bool = Field(
        default=True,
        description="Auto-discover skills on startup",
    )
    namespace_tools: bool = Field(
        default=True,
        description="Prefix skill tools with skill name",
    )
    trusted_paths: list[Path] = Field(
        default_factory=list,
        description="Paths to treat as trusted (in addition to project/user)",
    )

    @model_validator(mode="after")
    def _expand_user_dir(self) -> SkillConfig:
        """Expand ``~`` in user_skills_dir to the home directory."""
        self.user_skills_dir = self.user_skills_dir.expanduser()
        return self


@dataclass
class ValidationResult:
    """Result from validating a skill against the schema.

    Attributes:
        valid: Whether the skill passed validation.
        errors: List of validation error messages.
        warnings: List of validation warnings.
        skill_path: Path to the validated skill, if available.
        trust_level: Resolved trust level, if determined.
    """

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skill_path: Path | None = None
    trust_level: TrustLevel | None = None
