"""Tests for skill registry."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from mamba_agents.skills.config import Skill, SkillInfo, SkillScope
from mamba_agents.skills.errors import (
    SkillConflictError,
    SkillNotFoundError,
    SkillValidationError,
)
from mamba_agents.skills.registry import SkillRegistry, _load_skill_from_path


def _make_info(
    name: str = "test-skill",
    description: str = "A test skill",
    path: Path | None = None,
    scope: SkillScope = SkillScope.PROJECT,
) -> SkillInfo:
    """Create a minimal SkillInfo for testing."""
    return SkillInfo(
        name=name,
        description=description,
        path=path or Path("/skills/test-skill"),
        scope=scope,
    )


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    path: Path | None = None,
    body: str | None = None,
) -> Skill:
    """Create a minimal Skill for testing."""
    return Skill(
        info=_make_info(name=name, description=description, path=path),
        body=body,
    )


def _make_skill_dir(tmp_path: Path, name: str, description: str = "A skill") -> Path:
    """Create a skill directory with a valid SKILL.md file."""
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nSkill body here."
    )
    return skill_dir


class TestSkillRegistryInit:
    """Tests for SkillRegistry initialization."""

    def test_empty_registry(self) -> None:
        """Test that a new registry starts empty."""
        registry = SkillRegistry()

        assert len(registry) == 0
        assert registry.list() == []

    def test_repr_empty(self) -> None:
        """Test repr of an empty registry."""
        registry = SkillRegistry()
        assert repr(registry) == "SkillRegistry(skills=[])"

    def test_repr_with_skills(self) -> None:
        """Test repr shows registered skill names."""
        registry = SkillRegistry()
        registry.register(_make_skill(name="alpha"))
        registry.register(_make_skill(name="beta"))

        r = repr(registry)
        assert "alpha" in r
        assert "beta" in r


class TestRegisterSkillInstance:
    """Tests for registering Skill instances."""

    def test_register_skill(self) -> None:
        """Test registering a Skill instance."""
        registry = SkillRegistry()
        skill = _make_skill()

        registry.register(skill)

        assert registry.has("test-skill")
        assert len(registry) == 1

    def test_register_multiple_skills(self) -> None:
        """Test registering multiple skills with different names."""
        registry = SkillRegistry()

        registry.register(_make_skill(name="skill-a"))
        registry.register(_make_skill(name="skill-b"))
        registry.register(_make_skill(name="skill-c"))

        assert len(registry) == 3
        assert registry.has("skill-a")
        assert registry.has("skill-b")
        assert registry.has("skill-c")

    def test_register_skill_with_body(self) -> None:
        """Test registering a Skill with body content."""
        registry = SkillRegistry()
        skill = _make_skill(body="# Instructions\n\nDo something.")

        registry.register(skill)

        result = registry.get("test-skill")
        assert result is not None
        assert result.body == "# Instructions\n\nDo something."


class TestRegisterSkillInfo:
    """Tests for registering SkillInfo instances."""

    def test_register_skill_info(self) -> None:
        """Test registering a SkillInfo wraps it in a Skill."""
        registry = SkillRegistry()
        info = _make_info()

        registry.register(info)

        assert registry.has("test-skill")
        skill = registry.get("test-skill")
        assert skill is not None
        assert skill.info is info
        # Body should be None when registered from info (no SKILL.md on disk)
        # Since path doesn't exist, lazy loading won't succeed

    def test_register_skill_info_body_is_none(self) -> None:
        """Test that SkillInfo registration produces Skill with no body."""
        registry = SkillRegistry()
        info = _make_info()

        registry.register(info)

        skill = registry.get("test-skill")
        assert skill is not None
        # Body remains None because the fake path has no SKILL.md
        assert skill.body is None


class TestRegisterFromPath:
    """Tests for registering skills from Path objects."""

    def test_register_from_directory(self, tmp_path: Path) -> None:
        """Test registering a skill from a directory path."""
        skill_dir = _make_skill_dir(tmp_path, "my-skill", "My test skill")
        registry = SkillRegistry()

        registry.register(skill_dir)

        assert registry.has("my-skill")
        skill = registry.get("my-skill")
        assert skill is not None
        assert skill.info.name == "my-skill"
        assert skill.info.description == "My test skill"
        assert skill.body is not None
        assert "Skill body here" in skill.body

    def test_register_from_skill_md_file(self, tmp_path: Path) -> None:
        """Test registering from a direct SKILL.md file path."""
        skill_dir = _make_skill_dir(tmp_path, "direct-skill")
        skill_file = skill_dir / "SKILL.md"
        registry = SkillRegistry()

        registry.register(skill_file)

        assert registry.has("direct-skill")

    def test_register_path_not_found(self, tmp_path: Path) -> None:
        """Test that registering a non-existent path raises SkillNotFoundError."""
        bad_path = tmp_path / "nonexistent"
        registry = SkillRegistry()

        with pytest.raises(SkillNotFoundError):
            registry.register(bad_path)

    def test_register_path_no_skill_md(self, tmp_path: Path) -> None:
        """Test directory without SKILL.md raises SkillNotFoundError."""
        empty_dir = tmp_path / "empty-skill"
        empty_dir.mkdir()
        registry = SkillRegistry()

        with pytest.raises(SkillNotFoundError):
            registry.register(empty_dir)

    def test_register_path_invalid_frontmatter(self, tmp_path: Path) -> None:
        """Test invalid frontmatter raises SkillValidationError."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("No frontmatter here, just text.")
        registry = SkillRegistry()

        with pytest.raises(SkillValidationError):
            registry.register(skill_dir)

    def test_register_path_missing_required_fields(self, tmp_path: Path) -> None:
        """Test frontmatter missing required fields raises SkillValidationError."""
        skill_dir = tmp_path / "incomplete-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\nlicense: MIT\n---\nBody only.")
        registry = SkillRegistry()

        with pytest.raises(SkillValidationError) as exc_info:
            registry.register(skill_dir)

        assert "name" in str(exc_info.value).lower()
        assert "description" in str(exc_info.value).lower()

    def test_register_path_missing_closing_marker(self, tmp_path: Path) -> None:
        """Test frontmatter missing closing --- raises SkillValidationError."""
        skill_dir = tmp_path / "broken-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("---\nname: broken\ndescription: broken\n")
        registry = SkillRegistry()

        with pytest.raises(SkillValidationError):
            registry.register(skill_dir)


class TestDeregister:
    """Tests for deregistering skills."""

    def test_deregister_skill(self) -> None:
        """Test that deregister removes a registered skill."""
        registry = SkillRegistry()
        registry.register(_make_skill())

        registry.deregister("test-skill")

        assert not registry.has("test-skill")
        assert len(registry) == 0

    def test_deregister_nonexistent(self) -> None:
        """Test that deregistering a non-existent skill raises SkillNotFoundError."""
        registry = SkillRegistry()

        with pytest.raises(SkillNotFoundError):
            registry.deregister("nonexistent")

    def test_deregister_and_re_register(self) -> None:
        """Test deregister then re-register with the same name."""
        registry = SkillRegistry()
        registry.register(_make_skill(name="reusable"))

        registry.deregister("reusable")
        assert not registry.has("reusable")

        registry.register(_make_skill(name="reusable"))
        assert registry.has("reusable")


class TestGet:
    """Tests for getting skills from the registry."""

    def test_get_existing(self) -> None:
        """Test getting a registered skill returns the Skill."""
        registry = SkillRegistry()
        skill = _make_skill()
        registry.register(skill)

        result = registry.get("test-skill")

        assert result is not None
        assert result.info.name == "test-skill"

    def test_get_nonexistent(self) -> None:
        """Test getting a non-existent skill returns None."""
        registry = SkillRegistry()

        result = registry.get("nonexistent")

        assert result is None

    def test_get_with_lazy_body_loading(self, tmp_path: Path) -> None:
        """Test that get() lazily loads body when only SkillInfo was registered."""
        # Create a real SKILL.md on disk
        skill_dir = _make_skill_dir(tmp_path, "lazy-skill", "A lazy skill")

        # Register only the SkillInfo (no body)
        info = SkillInfo(
            name="lazy-skill",
            description="A lazy skill",
            path=skill_dir,
            scope=SkillScope.PROJECT,
        )
        registry = SkillRegistry()
        registry.register(info)

        # Before get, body should be None internally
        assert registry._skills["lazy-skill"].body is None

        # get() should trigger lazy loading
        skill = registry.get("lazy-skill")
        assert skill is not None
        assert skill.body is not None
        assert "Skill body here" in skill.body

    def test_get_lazy_load_failure_returns_skill_without_body(self) -> None:
        """Test that lazy load failure still returns the skill with body=None."""
        registry = SkillRegistry()
        info = _make_info(path=Path("/nonexistent/path"))
        registry.register(info)

        skill = registry.get("test-skill")

        assert skill is not None
        assert skill.body is None  # Failed to load, but skill is still returned


class TestList:
    """Tests for listing skills."""

    def test_list_empty(self) -> None:
        """Test listing when registry is empty."""
        registry = SkillRegistry()

        result = registry.list()

        assert result == []

    def test_list_returns_skill_info(self) -> None:
        """Test that list returns SkillInfo instances, not full Skills."""
        registry = SkillRegistry()
        info = _make_info(name="listed-skill")
        registry.register(info)

        result = registry.list()

        assert len(result) == 1
        assert isinstance(result[0], SkillInfo)
        assert result[0].name == "listed-skill"

    def test_list_multiple(self) -> None:
        """Test listing multiple registered skills."""
        registry = SkillRegistry()
        registry.register(_make_skill(name="a"))
        registry.register(_make_skill(name="b"))
        registry.register(_make_skill(name="c"))

        result = registry.list()

        assert len(result) == 3
        names = {info.name for info in result}
        assert names == {"a", "b", "c"}


class TestHas:
    """Tests for checking skill existence."""

    def test_has_registered(self) -> None:
        """Test has() returns True for registered skills."""
        registry = SkillRegistry()
        registry.register(_make_skill())

        assert registry.has("test-skill") is True

    def test_has_not_registered(self) -> None:
        """Test has() returns False for unregistered skills."""
        registry = SkillRegistry()

        assert registry.has("nonexistent") is False

    def test_has_after_deregister(self) -> None:
        """Test has() returns False after deregistering."""
        registry = SkillRegistry()
        registry.register(_make_skill())
        registry.deregister("test-skill")

        assert registry.has("test-skill") is False


class TestConflictDetection:
    """Tests for duplicate name detection."""

    def test_register_duplicate_raises_conflict(self) -> None:
        """Test that registering the same name twice raises SkillConflictError."""
        registry = SkillRegistry()
        registry.register(_make_skill(name="duplicate"))

        with pytest.raises(SkillConflictError) as exc_info:
            registry.register(_make_skill(name="duplicate", path=Path("/other/path")))

        assert exc_info.value.name == "duplicate"

    def test_register_duplicate_skill_info(self) -> None:
        """Test that registering duplicate SkillInfo raises conflict."""
        registry = SkillRegistry()
        registry.register(_make_info(name="dup"))

        with pytest.raises(SkillConflictError):
            registry.register(_make_info(name="dup"))

    def test_register_duplicate_path(self, tmp_path: Path) -> None:
        """Test that registering duplicate paths raises conflict."""
        skill_dir = _make_skill_dir(tmp_path, "path-dup")
        registry = SkillRegistry()
        registry.register(skill_dir)

        # Create another directory with the same skill name
        skill_dir2 = tmp_path / "other"
        skill_dir2.mkdir()
        skill_md = skill_dir2 / "SKILL.md"
        skill_md.write_text("---\nname: path-dup\ndescription: Another one\n---\nBody.")

        with pytest.raises(SkillConflictError):
            registry.register(skill_dir2)


class TestAsyncSafety:
    """Tests for async-safe concurrent access."""

    async def test_async_register(self) -> None:
        """Test async registration works."""
        registry = SkillRegistry()

        await registry.aregister(_make_skill())

        assert registry.has("test-skill")

    async def test_async_deregister(self) -> None:
        """Test async deregistration works."""
        registry = SkillRegistry()
        registry.register(_make_skill())

        await registry.aderegister("test-skill")

        assert not registry.has("test-skill")

    async def test_concurrent_registrations(self) -> None:
        """Test that concurrent async registrations are safe."""
        registry = SkillRegistry()

        async def register_skill(name: str) -> None:
            await registry.aregister(_make_skill(name=name, path=Path(f"/skills/{name}")))

        # Register 10 skills concurrently
        tasks = [register_skill(f"skill-{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        assert len(registry) == 10
        for i in range(10):
            assert registry.has(f"skill-{i}")

    async def test_concurrent_register_deregister(self) -> None:
        """Test that concurrent register and deregister operations are safe."""
        registry = SkillRegistry()

        # Pre-register some skills
        for i in range(5):
            registry.register(_make_skill(name=f"pre-{i}", path=Path(f"/skills/pre-{i}")))

        async def deregister_then_register(idx: int) -> None:
            await registry.aderegister(f"pre-{idx}")
            await registry.aregister(
                _make_skill(name=f"new-{idx}", path=Path(f"/skills/new-{idx}"))
            )

        tasks = [deregister_then_register(i) for i in range(5)]
        await asyncio.gather(*tasks)

        assert len(registry) == 5
        for i in range(5):
            assert not registry.has(f"pre-{i}")
            assert registry.has(f"new-{i}")

    async def test_async_register_conflict(self) -> None:
        """Test that async registration detects conflicts."""
        registry = SkillRegistry()
        await registry.aregister(_make_skill())

        with pytest.raises(SkillConflictError):
            await registry.aregister(_make_skill())

    async def test_async_deregister_not_found(self) -> None:
        """Test that async deregistration raises on missing skill."""
        registry = SkillRegistry()

        with pytest.raises(SkillNotFoundError):
            await registry.aderegister("nonexistent")


class TestLoadSkillFromPath:
    """Tests for the internal _load_skill_from_path function."""

    def test_load_from_directory(self, tmp_path: Path) -> None:
        """Test loading a skill from a directory."""
        skill_dir = _make_skill_dir(tmp_path, "loadable", "A loadable skill")

        skill = _load_skill_from_path(skill_dir)

        assert skill.info.name == "loadable"
        assert skill.info.description == "A loadable skill"
        assert skill.body is not None
        assert "Skill body here" in skill.body

    def test_load_from_skill_md_file(self, tmp_path: Path) -> None:
        """Test loading directly from a SKILL.md file."""
        skill_dir = _make_skill_dir(tmp_path, "direct")
        skill_file = skill_dir / "SKILL.md"

        skill = _load_skill_from_path(skill_file)

        assert skill.info.name == "direct"

    def test_load_nonexistent_path(self, tmp_path: Path) -> None:
        """Test loading from non-existent path raises SkillNotFoundError."""
        with pytest.raises(SkillNotFoundError):
            _load_skill_from_path(tmp_path / "nonexistent")

    def test_load_no_frontmatter(self, tmp_path: Path) -> None:
        """Test loading SKILL.md without frontmatter raises SkillValidationError."""
        skill_dir = tmp_path / "no-fm"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("Just plain text, no frontmatter.")

        with pytest.raises(SkillValidationError):
            _load_skill_from_path(skill_dir)

    def test_load_empty_body(self, tmp_path: Path) -> None:
        """Test loading SKILL.md with empty body sets body to None."""
        skill_dir = tmp_path / "empty-body"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: empty-body\ndescription: No body\n---\n")

        skill = _load_skill_from_path(skill_dir)

        assert skill.info.name == "empty-body"
        assert skill.body is None

    def test_load_scope_defaults_to_custom(self, tmp_path: Path) -> None:
        """Test that loaded skills default to CUSTOM scope."""
        skill_dir = _make_skill_dir(tmp_path, "scoped")

        skill = _load_skill_from_path(skill_dir)

        assert skill.info.scope is SkillScope.CUSTOM

    def test_load_optional_fields(self, tmp_path: Path) -> None:
        """Test loading SKILL.md with optional frontmatter fields."""
        skill_dir = tmp_path / "full-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: full-skill\n"
            "description: Full skill\n"
            "license: MIT\n"
            "model: gpt-4o\n"
            "user-invocable: false\n"
            "argument-hint: <path>\n"
            "---\n\n"
            "Body content."
        )

        skill = _load_skill_from_path(skill_dir)

        assert skill.info.license == "MIT"
        assert skill.info.model == "gpt-4o"
        assert skill.info.user_invocable is False
        assert skill.info.argument_hint == "<path>"


class TestRegistryLifecycle:
    """Integration-style tests for full registry lifecycle."""

    def test_register_get_deregister_cycle(self) -> None:
        """Test the complete lifecycle: register, get, deregister."""
        registry = SkillRegistry()

        # Register
        skill = _make_skill(name="lifecycle", body="# Lifecycle skill")
        registry.register(skill)
        assert registry.has("lifecycle")

        # Get
        result = registry.get("lifecycle")
        assert result is not None
        assert result.body == "# Lifecycle skill"

        # Deregister
        registry.deregister("lifecycle")
        assert not registry.has("lifecycle")
        assert registry.get("lifecycle") is None

    def test_mixed_registration_types(self, tmp_path: Path) -> None:
        """Test registering skills from different source types."""
        registry = SkillRegistry()

        # Register Skill instance
        registry.register(_make_skill(name="from-skill"))

        # Register SkillInfo
        registry.register(_make_info(name="from-info", path=Path("/info/path")))

        # Register Path
        skill_dir = _make_skill_dir(tmp_path, "from-path")
        registry.register(skill_dir)

        assert len(registry) == 3
        assert registry.has("from-skill")
        assert registry.has("from-info")
        assert registry.has("from-path")

        # List should return all three
        infos = registry.list()
        assert len(infos) == 3
        names = {info.name for info in infos}
        assert names == {"from-skill", "from-info", "from-path"}
