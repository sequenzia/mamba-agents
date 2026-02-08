"""Skill discovery from configured directories.

Scans a three-level directory hierarchy (project, user, custom) for SKILL.md
files, loads metadata, assigns scope and trust, and resolves name conflicts
using priority ordering.

Priority (highest to lowest):
1. Project: ``.mamba/skills/`` (relative to working directory)
2. User: ``~/.mamba/skills/`` (user home)
3. Custom: Additional configurable search paths
"""

from __future__ import annotations

import logging
from pathlib import Path

from mamba_agents.skills.config import SkillConfig, SkillInfo, SkillScope, TrustLevel
from mamba_agents.skills.errors import SkillConflictError, SkillError
from mamba_agents.skills.loader import load_metadata

logger = logging.getLogger(__name__)

# Priority order for scopes (lower index = higher priority).
_SCOPE_PRIORITY: dict[SkillScope, int] = {
    SkillScope.PROJECT: 0,
    SkillScope.USER: 1,
    SkillScope.CUSTOM: 2,
}


def scan_directory(
    path: Path,
    scope: SkillScope,
    trust: TrustLevel,
) -> list[SkillInfo]:
    """Scan a single directory for skills.

    Uses ``Path.glob("*/SKILL.md")`` to find skill directories, calls
    ``load_metadata()`` for each found file, and assigns the given scope
    and trust level. Follows symlinks.

    Individual parse failures are logged and skipped without aborting.

    Args:
        path: Directory to scan for ``*/SKILL.md`` files.
        scope: Scope to assign to discovered skills.
        trust: Trust level to assign to discovered skills.

    Returns:
        List of ``SkillInfo`` objects discovered in the directory.
    """
    skills: list[SkillInfo] = []

    if not path.exists():
        logger.debug("Skills directory does not exist, skipping: %s", path)
        return skills

    try:
        if not path.is_dir():
            logger.warning("Skills path is not a directory, skipping: %s", path)
            return skills
    except PermissionError:
        logger.warning("Permission denied accessing directory: %s", path)
        return skills

    # Check for same-scope duplicates within this directory.
    seen_names: dict[str, Path] = {}

    try:
        skill_files = sorted(path.glob("*/SKILL.md"))
    except PermissionError:
        logger.warning("Permission denied scanning directory: %s", path)
        return skills

    for skill_md in skill_files:
        try:
            info = load_metadata(skill_md, scope=scope)
            info.trust_level = trust
            info.scope = scope

            # Check for same-scope duplicate.
            if info.name in seen_names:
                raise SkillConflictError(
                    name=info.name,
                    paths=[seen_names[info.name], info.path],
                )

            seen_names[info.name] = info.path
            skills.append(info)
        except SkillConflictError:
            # Re-raise conflict errors — these are not recoverable.
            raise
        except SkillError as exc:
            logger.error(
                "Failed to load skill from %s: %s",
                skill_md,
                exc,
            )
        except Exception as exc:
            logger.error(
                "Unexpected error loading skill from %s: %s",
                skill_md,
                exc,
            )

    return skills


def discover_skills(config: SkillConfig) -> list[SkillInfo]:
    """Discover skills from all configured directories.

    Scans directories in priority order (project > user > custom) and
    resolves name conflicts: higher-priority scopes win and an info
    message is logged. Same-scope conflicts raise ``SkillConflictError``.

    Custom paths are assigned ``TrustLevel.UNTRUSTED`` unless they appear
    in ``config.trusted_paths``.

    Args:
        config: Skill configuration specifying directories and trust settings.

    Returns:
        List of discovered ``SkillInfo`` objects, de-duplicated by name
        with higher-priority scopes winning.

    Raises:
        SkillConflictError: If duplicate skill names exist within the same scope.
    """
    # Resolve trusted_paths to absolute for comparison.
    trusted_paths = {p.resolve() for p in config.trusted_paths}

    # Collect all skills grouped by scope priority.
    # Each entry is (priority, list[SkillInfo]).
    scoped_skills: list[tuple[int, list[SkillInfo]]] = []

    # 1. Project-level directories (highest priority).
    for skills_dir in config.skills_dirs:
        found = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)
        if found:
            scoped_skills.append((_SCOPE_PRIORITY[SkillScope.PROJECT], found))

    # 2. User-level directory.
    user_dir = config.user_skills_dir
    found = scan_directory(user_dir, SkillScope.USER, TrustLevel.TRUSTED)
    if found:
        scoped_skills.append((_SCOPE_PRIORITY[SkillScope.USER], found))

    # 3. Custom paths (lowest priority, untrusted unless in trusted_paths).
    for custom_path in config.custom_paths:
        resolved = custom_path.resolve()
        trust = TrustLevel.TRUSTED if resolved in trusted_paths else TrustLevel.UNTRUSTED
        found = scan_directory(custom_path, SkillScope.CUSTOM, trust)
        if found:
            scoped_skills.append((_SCOPE_PRIORITY[SkillScope.CUSTOM], found))

    # Sort by priority (lower number = higher priority).
    scoped_skills.sort(key=lambda x: x[0])

    # Resolve name conflicts.
    # Same-scope conflicts raise SkillConflictError.
    # Cross-scope conflicts: higher priority wins.
    result: list[SkillInfo] = []
    seen_names: dict[str, SkillInfo] = {}

    for _priority, skills in scoped_skills:
        for skill in skills:
            if skill.name in seen_names:
                existing = seen_names[skill.name]

                # Same-scope conflict — raise error.
                if existing.scope == skill.scope:
                    raise SkillConflictError(
                        name=skill.name,
                        paths=[existing.path, skill.path],
                    )

                # Cross-scope conflict — higher priority already recorded.
                logger.info(
                    "Skill '%s' from %s scope (path: %s) shadows "
                    "lower-priority %s scope (path: %s)",
                    skill.name,
                    existing.scope.value,
                    existing.path,
                    skill.scope.value,
                    skill.path,
                )
                continue

            seen_names[skill.name] = skill
            result.append(skill)

    return result
