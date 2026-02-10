"""Top-level SkillManager facade for the skills subsystem.

Composes loader, discovery, registry, validator, and invocation components
behind a single unified API. Follows the MCPClientManager pattern for
lifecycle management.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from mamba_agents.skills.config import (
    Skill,
    SkillConfig,
    SkillInfo,
    ValidationResult,
)
from mamba_agents.skills.discovery import discover_skills
from mamba_agents.skills.errors import SkillInvocationError, SkillNotFoundError
from mamba_agents.skills.invocation import activate, deactivate
from mamba_agents.skills.registry import SkillRegistry
from mamba_agents.skills.validator import validate

logger = logging.getLogger(__name__)


class SkillManager:
    """Facade for the skill subsystem.

    Composes all skill components (loader, discovery, registry, validator,
    invocation) behind a single API. Provides the primary interface for
    discovering, registering, activating, and managing skills.

    Follows the ``MCPClientManager`` pattern: create an instance with
    configuration, then call methods to interact with the subsystem.

    Example::

        manager = SkillManager()
        skills = manager.discover()
        content = manager.activate("my-skill", arguments="file.txt")
        tools = manager.get_tools("my-skill")

    Args:
        config: Skill subsystem configuration. Uses defaults if ``None``.
    """

    def __init__(
        self,
        config: SkillConfig | None = None,
    ) -> None:
        """Initialize the SkillManager with configuration.

        Creates the internal registry and stores the config for
        subsequent discovery and validation operations.

        Args:
            config: Skill subsystem configuration. Uses defaults if ``None``.
        """
        self._config = config or SkillConfig()
        self._registry = SkillRegistry()

    @property
    def config(self) -> SkillConfig:
        """Get the skill configuration."""
        return self._config

    @property
    def registry(self) -> SkillRegistry:
        """Get the internal skill registry (for advanced use)."""
        return self._registry

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover(self) -> list[SkillInfo]:
        """Scan configured directories and register discovered skills.

        Scans all directories from the configuration (project, user, custom)
        for SKILL.md files. Discovered skills are registered in the internal
        registry. If a skill with the same name already exists in the
        registry, it is skipped to avoid duplicates on repeated calls.

        Individual discovery errors are logged and skipped without aborting
        the entire scan.

        Returns:
            List of newly discovered ``SkillInfo`` instances.
        """
        try:
            discovered = discover_skills(self._config)
        except Exception:
            logger.exception("Discovery failed")
            return []

        newly_registered: list[SkillInfo] = []
        for info in discovered:
            if self._registry.has(info.name):
                logger.debug(
                    "Skill '%s' already registered, skipping duplicate",
                    info.name,
                )
                continue

            try:
                self._registry.register(info)
                newly_registered.append(info)
            except Exception:
                logger.exception(
                    "Failed to register discovered skill '%s'",
                    info.name,
                )

        return newly_registered

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, skill: Skill | SkillInfo | Path) -> None:
        """Register a skill from an instance, info, or path.

        Delegates directly to the internal registry.

        Args:
            skill: A ``Skill`` instance, ``SkillInfo`` metadata, or ``Path``
                to a directory containing SKILL.md.

        Raises:
            SkillConflictError: If a skill with the same name is already
                registered.
            SkillNotFoundError: If the path does not exist or has no SKILL.md.
            SkillValidationError: If the skill fails validation.
        """
        self._registry.register(skill)

    def deregister(self, name: str) -> None:
        """Remove a skill from the registry by name.

        Deactivates the skill first if it is currently active, then
        removes it from the registry.

        Args:
            name: The skill name to remove.

        Raises:
            SkillNotFoundError: If the skill is not registered.
        """
        skill = self._registry.get(name)
        if skill is not None and skill.is_active:
            deactivate(skill)

        self._registry.deregister(name)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, name: str) -> Skill | None:
        """Get a skill by name.

        Delegates to the registry, which performs lazy body loading if
        needed.

        Args:
            name: The skill name to retrieve.

        Returns:
            The ``Skill`` if found, ``None`` otherwise.
        """
        return self._registry.get(name)

    def list(self) -> list[SkillInfo]:
        """List all registered skill metadata.

        Returns:
            A list of ``SkillInfo`` for all registered skills.
        """
        return self._registry.list()

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def activate(self, name: str, arguments: str = "") -> str:
        """Activate a skill by name.

        Looks up the skill in the registry, then delegates to the
        invocation module for permission checks, lazy loading, argument
        substitution, and activation state management.

        Skills with ``execution_mode: "fork"`` require a ``SubagentManager``
        for delegation. Use ``integration.activate_with_fork()`` directly,
        or invoke through the ``Agent`` facade which mediates between both
        managers.

        If the skill is already active, it is re-activated (refreshed)
        with the new arguments.

        Args:
            name: Name of the skill to activate.
            arguments: Raw argument string to pass to the skill.

        Returns:
            Processed skill content with arguments substituted.

        Raises:
            SkillNotFoundError: If the skill is not registered.
            SkillInvocationError: If the skill has fork execution mode
                (requires SubagentManager via integration module), or
                the invocation source lacks permission.
        """
        skill = self._registry.get(name)
        if skill is None:
            raise SkillNotFoundError(name=name, path="<registry>")

        # Fork-mode skills cannot be activated through SkillManager alone.
        # Use integration.activate_with_fork() with an explicit SubagentManager.
        if skill.info.execution_mode == "fork":
            raise SkillInvocationError(
                name=name,
                source="code",
                reason=(
                    "Skill has execution_mode='fork' which requires a SubagentManager. "
                    "Use integration.activate_with_fork() or invoke through the Agent "
                    "facade which mediates between SkillManager and SubagentManager."
                ),
            )

        return activate(skill, arguments)

    def deactivate(self, name: str) -> None:
        """Deactivate a skill by name.

        If the skill is not active or not found, this is a no-op.

        Args:
            name: Name of the skill to deactivate.
        """
        skill = self._registry.get(name)
        if skill is None:
            return

        if not skill.is_active:
            return

        deactivate(skill)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, path: Path) -> ValidationResult:
        """Validate a SKILL.md file at the given path.

        Delegates to the validator module for schema validation,
        frontmatter checks, and name-directory matching.

        Args:
            path: Path to a SKILL.md file or its parent directory.

        Returns:
            ``ValidationResult`` with valid flag, errors, and warnings.
        """
        return validate(path)

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def get_tools(self, name: str) -> list[Callable[..., Any]]:
        """Get tools registered by a specific active skill.

        Returns the tool callables stored on the skill's internal
        ``_tools`` list. Returns an empty list if the skill is not
        found or not active.

        Args:
            name: Name of the skill.

        Returns:
            List of tool callables for the skill.
        """
        skill = self._registry.get(name)
        if skill is None or not skill.is_active:
            return []

        return list(skill._tools)

    def get_all_tools(self) -> list[Callable[..., Any]]:
        """Get all tools from all active skills with namespace prefixes.

        Collects tools from every active skill. When ``namespace_tools``
        is enabled in the config, tool functions are wrapped with a
        prefixed name (``{skill_name}:{tool.__name__}``).

        Returns:
            List of all tool callables from all active skills.
        """
        all_tools: list[Callable[..., Any]] = []

        for info in self._registry.list():
            skill = self._registry.get(info.name)
            if skill is None or not skill.is_active:
                continue

            if self._config.namespace_tools:
                for tool in skill._tools:
                    # Create a namespaced wrapper that preserves the callable
                    prefixed_name = f"{info.name}:{getattr(tool, '__name__', str(tool))}"
                    namespaced = _namespace_tool(tool, prefixed_name)
                    all_tools.append(namespaced)
            else:
                all_tools.extend(skill._tools)

        return all_tools

    # ------------------------------------------------------------------
    # References (Tier 3 — on-demand loading)
    # ------------------------------------------------------------------

    def get_references(self, skill_name: str) -> list[Path]:
        """List available reference files for a skill.

        Scans the ``references/`` subdirectory within the skill's path
        for supplemental files (markdown, text, JSON, etc.). References
        are not loaded at discovery or activation, only on explicit request.

        Args:
            skill_name: Name of the skill to list references for.

        Returns:
            List of paths to reference files. Empty if the skill has no
            references directory or the skill is not found.
        """
        skill = self._registry.get(skill_name)
        if skill is None:
            return []

        refs_dir = skill.info.path / "references"
        if not refs_dir.exists() or not refs_dir.is_dir():
            return []

        return sorted(p for p in refs_dir.iterdir() if p.is_file())

    def load_reference(self, skill_name: str, ref_name: str) -> str:
        """Load and return the content of a reference file.

        Reads a specific file from the skill's ``references/`` directory
        and returns its content as a string.

        Args:
            skill_name: Name of the skill.
            ref_name: Name of the reference file (e.g., ``"api-docs.md"``).

        Returns:
            Content of the reference file as a string.

        Raises:
            SkillNotFoundError: If the skill is not registered.
            FileNotFoundError: If the reference file does not exist.
        """
        skill = self._registry.get(skill_name)
        if skill is None:
            raise SkillNotFoundError(name=skill_name, path="<registry>")

        ref_path = skill.info.path / "references" / ref_name
        if not ref_path.exists():
            raise FileNotFoundError(
                f"Reference '{ref_name}' not found for skill '{skill_name}' at {ref_path}"
            )

        return ref_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # Dunder methods
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return a string representation of the manager."""
        count = len(self._registry)
        active = sum(
            1
            for info in self._registry.list()
            if (s := self._registry.get(info.name)) is not None and s.is_active
        )
        return f"SkillManager(skills={count}, active={active})"

    def __len__(self) -> int:
        """Return the number of registered skills."""
        return len(self._registry)


def _namespace_tool(
    tool: Callable[..., Any],
    prefixed_name: str,
) -> Callable[..., Any]:
    """Wrap a tool callable with a namespaced name.

    Creates a thin wrapper that delegates to the original tool but has
    a different ``__name__`` attribute for identification.

    Args:
        tool: Original tool callable.
        prefixed_name: Namespaced name (e.g., ``"my-skill:read_file"``).

    Returns:
        Wrapper callable with the prefixed name.
    """
    from functools import wraps

    @wraps(tool)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return tool(*args, **kwargs)

    wrapper.__name__ = prefixed_name
    wrapper.__qualname__ = prefixed_name
    return wrapper
