"""In-memory skill registry with async-safe registration and lookup."""

from __future__ import annotations

import asyncio
from pathlib import Path

from mamba_agents.skills.config import Skill, SkillInfo, SkillScope
from mamba_agents.skills.errors import (
    SkillConflictError,
    SkillNotFoundError,
    SkillValidationError,
)


def _load_skill_from_path(path: Path) -> Skill:
    """Load a skill from a directory path containing SKILL.md.

    This is a minimal internal loader used by the registry for Path-based
    registration. It reads the SKILL.md file, parses YAML frontmatter, and
    constructs a ``Skill`` instance. When the full ``skills/loader.py`` module
    is available, this function should delegate to it.

    Args:
        path: Directory containing a SKILL.md file, or direct path to a
            SKILL.md file.

    Returns:
        A fully loaded ``Skill`` with info and body.

    Raises:
        SkillNotFoundError: If the path does not exist or has no SKILL.md.
        SkillValidationError: If the frontmatter is missing or invalid.
    """
    # Allow both directory and direct SKILL.md paths
    if path.is_file() and path.name == "SKILL.md":
        skill_file = path
        skill_dir = path.parent
    else:
        skill_dir = path
        skill_file = path / "SKILL.md"

    if not skill_file.exists():
        raise SkillNotFoundError(
            name=skill_dir.name,
            path=skill_file,
        )

    content = skill_file.read_text(encoding="utf-8")

    # Parse YAML frontmatter between --- markers
    if not content.startswith("---"):
        raise SkillValidationError(
            name=skill_dir.name,
            errors=["SKILL.md must start with YAML frontmatter (--- markers)"],
            path=skill_file,
        )

    # Find closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        raise SkillValidationError(
            name=skill_dir.name,
            errors=["SKILL.md frontmatter missing closing --- marker"],
            path=skill_file,
        )

    frontmatter_str = content[3:end_idx].strip()
    body = content[end_idx + 3 :].strip() or None

    # Parse YAML (use yaml if available, otherwise simple key-value parsing)
    try:
        import yaml

        frontmatter = yaml.safe_load(frontmatter_str)
    except ImportError:
        # Fallback: simple key-value parsing for basic frontmatter
        frontmatter = {}
        for line in frontmatter_str.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, _, value = line.partition(":")
                frontmatter[key.strip()] = value.strip()
    except Exception as exc:
        raise SkillValidationError(
            name=skill_dir.name,
            errors=[f"Failed to parse YAML frontmatter: {exc}"],
            path=skill_file,
        ) from exc

    if not isinstance(frontmatter, dict):
        raise SkillValidationError(
            name=skill_dir.name,
            errors=["YAML frontmatter must be a mapping"],
            path=skill_file,
        )

    # Validate required fields
    errors: list[str] = []
    if "name" not in frontmatter:
        errors.append("Missing required field: name")
    if "description" not in frontmatter:
        errors.append("Missing required field: description")
    if errors:
        raise SkillValidationError(
            name=frontmatter.get("name", skill_dir.name),
            errors=errors,
            path=skill_file,
        )

    name = frontmatter["name"]
    description = frontmatter["description"]

    info = SkillInfo(
        name=name,
        description=description,
        path=skill_dir,
        scope=SkillScope.CUSTOM,
        license=frontmatter.get("license"),
        compatibility=frontmatter.get("compatibility"),
        metadata=frontmatter.get("metadata"),
        allowed_tools=frontmatter.get("allowed-tools"),
        model=frontmatter.get("model"),
        execution_mode=frontmatter.get("execution-mode"),
        agent=frontmatter.get("agent"),
        disable_model_invocation=frontmatter.get("disable-model-invocation", False),
        user_invocable=frontmatter.get("user-invocable", True),
        argument_hint=frontmatter.get("argument-hint"),
    )

    return Skill(info=info, body=body)


class SkillRegistry:
    """In-memory registry for managing skill registration and lookup.

    Stores registered skills and provides methods for registration,
    deregistration, retrieval, and listing. Uses ``asyncio.Lock`` for
    async-safe concurrent access.

    The registry supports three registration sources:
    - ``Skill`` instances (full skill with info and optional body)
    - ``SkillInfo`` instances (metadata only, body loaded lazily on ``get()``)
    - ``Path`` objects (delegates to loader to parse SKILL.md)

    Example::

        registry = SkillRegistry()
        registry.register(skill_instance)
        registry.register(skill_info)
        registry.register(Path("/path/to/skill"))

        skill = registry.get("my-skill")
        all_skills = registry.list()
    """

    def __init__(self) -> None:
        """Initialize an empty skill registry."""
        self._skills: dict[str, Skill] = {}
        self._lock = asyncio.Lock()

    def register(self, skill: Skill | SkillInfo | Path) -> None:
        """Register a skill from an instance, info, or path.

        When a ``Path`` is provided, the registry delegates to the loader
        to parse the SKILL.md file. When a ``SkillInfo`` is provided, a
        ``Skill`` wrapper is created with no body (loaded lazily on ``get()``).

        Args:
            skill: A ``Skill`` instance, ``SkillInfo`` metadata, or ``Path``
                to a directory containing SKILL.md.

        Raises:
            SkillConflictError: If a skill with the same name is already
                registered.
            SkillNotFoundError: If the path does not exist or has no SKILL.md.
            SkillValidationError: If the skill fails validation during
                path-based registration.
        """
        if isinstance(skill, Path):
            resolved = _load_skill_from_path(skill)
        elif isinstance(skill, SkillInfo):
            resolved = Skill(info=skill)
        else:
            resolved = skill

        name = resolved.info.name

        if name in self._skills:
            existing = self._skills[name]
            raise SkillConflictError(
                name=name,
                paths=[str(existing.info.path), str(resolved.info.path)],
            )

        self._skills[name] = resolved

    async def aregister(self, skill: Skill | SkillInfo | Path) -> None:
        """Async-safe version of ``register()``.

        Acquires the internal lock before mutating the registry.

        Args:
            skill: A ``Skill`` instance, ``SkillInfo`` metadata, or ``Path``
                to a directory containing SKILL.md.

        Raises:
            SkillConflictError: If a skill with the same name is already
                registered.
            SkillNotFoundError: If the path does not exist or has no SKILL.md.
            SkillValidationError: If the skill fails validation during
                path-based registration.
        """
        async with self._lock:
            self.register(skill)

    def deregister(self, name: str) -> None:
        """Remove a skill from the registry by name.

        Args:
            name: The skill name to remove.

        Raises:
            SkillNotFoundError: If the skill is not registered.
        """
        if name not in self._skills:
            raise SkillNotFoundError(name=name, path="<registry>")

        del self._skills[name]

    async def aderegister(self, name: str) -> None:
        """Async-safe version of ``deregister()``.

        Acquires the internal lock before mutating the registry.

        Args:
            name: The skill name to remove.

        Raises:
            SkillNotFoundError: If the skill is not registered.
        """
        async with self._lock:
            self.deregister(name)

    def get(self, name: str) -> Skill | None:
        """Get a skill by name.

        If the skill was registered from a ``SkillInfo`` (metadata only) and
        its body has not been loaded yet, this method attempts to load the
        body lazily from the skill's path.

        Args:
            name: The skill name to retrieve.

        Returns:
            The full ``Skill`` if found, ``None`` otherwise.
        """
        skill = self._skills.get(name)
        if skill is None:
            return None

        # Lazy-load body if not present and path is available
        if skill.body is None and skill.info.path is not None:
            skill_file = skill.info.path / "SKILL.md"
            if skill_file.exists():
                try:
                    loaded = _load_skill_from_path(skill.info.path)
                    skill.body = loaded.body
                except (SkillNotFoundError, SkillValidationError):
                    # Body loading is best-effort; skill remains usable
                    pass

        return skill

    def list(self) -> list[SkillInfo]:
        """List all registered skill metadata.

        Returns:
            A list of ``SkillInfo`` instances for all registered skills.
        """
        return [skill.info for skill in self._skills.values()]

    def has(self, name: str) -> bool:
        """Check if a skill is registered.

        Args:
            name: The skill name to check.

        Returns:
            ``True`` if the skill is registered, ``False`` otherwise.
        """
        return name in self._skills

    def __len__(self) -> int:
        """Return the number of registered skills."""
        return len(self._skills)

    def __repr__(self) -> str:
        """Return a string representation of the registry."""
        names = list(self._skills.keys())
        return f"SkillRegistry(skills={names})"
