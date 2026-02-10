"""Skill testing harness for isolated skill testing.

Provides ``SkillTestHarness`` for testing skills without a full Agent
instance, and a ``skill_harness`` pytest fixture for convenient test setup.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mamba_agents.skills.config import Skill, ValidationResult
from mamba_agents.skills.errors import SkillNotFoundError
from mamba_agents.skills.invocation import substitute_arguments
from mamba_agents.skills.loader import load_full
from mamba_agents.skills.validator import validate, validate_frontmatter


class SkillTestHarness:
    """Test harness for validating and invoking skills in isolation.

    Allows skill authors to load, validate, and invoke skills without
    setting up a full ``Agent`` instance or requiring a real LLM model.
    Accepts either a path to a skill directory or a pre-built ``Skill``
    instance.

    Example::

        # From a directory path
        harness = SkillTestHarness(skill_path=Path("my-skill"))
        skill = harness.load()
        result = harness.validate()
        content = harness.invoke("file.txt")

        # From a Skill instance
        harness = SkillTestHarness(skill=my_skill)
        content = harness.invoke("arg1 arg2")

    Args:
        skill_path: Path to a directory containing a SKILL.md file.
        skill: A pre-built ``Skill`` instance to use directly.

    Raises:
        ValueError: If neither ``skill_path`` nor ``skill`` is provided.
    """

    def __init__(
        self,
        skill_path: Path | None = None,
        skill: Skill | None = None,
    ) -> None:
        """Initialize the test harness.

        Args:
            skill_path: Path to a directory containing a SKILL.md file.
            skill: A pre-built ``Skill`` instance to use directly.

        Raises:
            ValueError: If neither ``skill_path`` nor ``skill`` is provided.
        """
        if skill_path is None and skill is None:
            raise ValueError("Either 'skill_path' or 'skill' must be provided")

        self._skill_path = skill_path
        self._skill = skill

    @property
    def skill(self) -> Skill | None:
        """Return the loaded skill, or ``None`` if not yet loaded."""
        return self._skill

    @property
    def skill_path(self) -> Path | None:
        """Return the configured skill path."""
        return self._skill_path

    def load(self) -> Skill:
        """Load and validate the skill.

        If a ``Skill`` instance was provided at construction, returns it
        directly. Otherwise, loads the skill from the configured path.

        Returns:
            The loaded ``Skill`` instance.

        Raises:
            SkillNotFoundError: If the skill path does not exist or has
                no SKILL.md file.
            SkillParseError: If the SKILL.md frontmatter is malformed.
            SkillValidationError: If required fields are missing or invalid.
        """
        if self._skill is not None:
            return self._skill

        if self._skill_path is None:
            raise ValueError("No skill_path configured and no skill provided")

        path = Path(self._skill_path)

        # Resolve to SKILL.md file
        skill_file = path / "SKILL.md" if path.is_dir() else path

        if not skill_file.exists():
            name = path.name if path.is_dir() else path.parent.name
            raise SkillNotFoundError(name=name, path=skill_file)

        self._skill = load_full(skill_file)
        return self._skill

    def validate(self) -> ValidationResult:
        """Validate frontmatter and body, returning a structured result.

        If a ``Skill`` instance is available (either provided at
        construction or loaded via ``load()``), validates its frontmatter
        data directly. Otherwise, validates from the configured path.

        Returns:
            ``ValidationResult`` with valid flag, errors, and warnings.
        """
        if self._skill is not None:
            # Validate the in-memory skill's frontmatter fields
            data = _skill_to_frontmatter_dict(self._skill)
            result = validate_frontmatter(data)

            # Add path info if available
            if self._skill.info.path is not None:
                result.skill_path = self._skill.info.path

            return result

        if self._skill_path is not None:
            path = Path(self._skill_path)
            return validate(path)

        return ValidationResult(
            valid=False,
            errors=["No skill path or skill instance available for validation"],
        )

    def invoke(self, arguments: str = "") -> str:
        """Simulate invocation with test arguments.

        Loads the skill if not already loaded, then performs argument
        substitution on the skill body. Does not require a real LLM
        model -- only processes the skill content template.

        Args:
            arguments: Raw argument string to substitute into the skill body.

        Returns:
            Processed skill content with arguments substituted.

        Raises:
            SkillNotFoundError: If the skill cannot be loaded.
        """
        skill = self.load()
        body = skill.body or ""
        return substitute_arguments(body, arguments)

    def get_registered_tools(self) -> list[str]:
        """Get tool names that would be registered by this skill.

        Returns the names from the ``allowed_tools`` field of the skill's
        metadata. Loads the skill if not already loaded.

        Returns:
            List of tool name strings. Empty if no tools are configured.
        """
        skill = self.load()
        return list(skill.info.allowed_tools or [])


def _skill_to_frontmatter_dict(skill: Skill) -> dict[str, object]:
    """Convert a Skill's info fields back to a frontmatter-style dict.

    Used for validating in-memory Skill instances through the same
    validation pipeline as file-based skills.

    Args:
        skill: The Skill whose info to convert.

    Returns:
        Dictionary with YAML-style keys matching the frontmatter schema.
    """
    info = skill.info
    data: dict[str, object] = {}

    if info.name is not None:
        data["name"] = info.name
    if info.description is not None:
        data["description"] = info.description
    if info.license is not None:
        data["license"] = info.license
    if info.compatibility is not None:
        data["compatibility"] = info.compatibility
    if info.metadata is not None:
        data["metadata"] = info.metadata
    if info.allowed_tools is not None:
        data["allowed-tools"] = info.allowed_tools
    if info.model is not None:
        data["model"] = info.model
    if info.execution_mode is not None:
        data["context"] = info.execution_mode
    if info.disable_model_invocation:
        data["disable-model-invocation"] = info.disable_model_invocation
    if not info.user_invocable:
        data["user-invocable"] = info.user_invocable
    if info.hooks is not None:
        data["hooks"] = info.hooks
    if info.argument_hint is not None:
        data["argument-hint"] = info.argument_hint

    return data


@pytest.fixture
def skill_harness():
    """Pytest fixture providing a factory for ``SkillTestHarness`` instances.

    Usage::

        def test_my_skill(skill_harness):
            harness = skill_harness(path=Path("my-skill"))
            skill = harness.load()
            assert skill.info.name == "my-skill"

        def test_from_instance(skill_harness):
            harness = skill_harness(skill=my_skill)
            result = harness.validate()
            assert result.valid
    """

    def _harness(
        path: Path | None = None,
        skill: Skill | None = None,
    ) -> SkillTestHarness:
        return SkillTestHarness(skill_path=path, skill=skill)

    return _harness
