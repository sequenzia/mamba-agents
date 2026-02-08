"""Tests for skills package __init__.py exports."""

from __future__ import annotations


class TestSkillsPackageExports:
    """Tests that all public symbols are importable from mamba_agents.skills."""

    def test_import_skill_manager(self) -> None:
        """Test SkillManager is importable from the package."""
        from mamba_agents.skills import SkillManager

        assert SkillManager is not None

    def test_import_skill(self) -> None:
        """Test Skill is importable from the package."""
        from mamba_agents.skills import Skill

        assert Skill is not None

    def test_import_skill_info(self) -> None:
        """Test SkillInfo is importable from the package."""
        from mamba_agents.skills import SkillInfo

        assert SkillInfo is not None

    def test_import_skill_config(self) -> None:
        """Test SkillConfig is importable from the package."""
        from mamba_agents.skills import SkillConfig

        assert SkillConfig is not None

    def test_import_validation_result(self) -> None:
        """Test ValidationResult is importable from the package."""
        from mamba_agents.skills import ValidationResult

        assert ValidationResult is not None

    def test_import_skill_scope(self) -> None:
        """Test SkillScope is importable from the package."""
        from mamba_agents.skills import SkillScope

        assert SkillScope is not None

    def test_import_trust_level(self) -> None:
        """Test TrustLevel is importable from the package."""
        from mamba_agents.skills import TrustLevel

        assert TrustLevel is not None

    def test_import_skill_error(self) -> None:
        """Test SkillError is importable from the package."""
        from mamba_agents.skills import SkillError

        assert SkillError is not None

    def test_import_skill_not_found_error(self) -> None:
        """Test SkillNotFoundError is importable from the package."""
        from mamba_agents.skills import SkillNotFoundError

        assert SkillNotFoundError is not None

    def test_import_skill_parse_error(self) -> None:
        """Test SkillParseError is importable from the package."""
        from mamba_agents.skills import SkillParseError

        assert SkillParseError is not None

    def test_import_skill_validation_error(self) -> None:
        """Test SkillValidationError is importable from the package."""
        from mamba_agents.skills import SkillValidationError

        assert SkillValidationError is not None

    def test_import_skill_load_error(self) -> None:
        """Test SkillLoadError is importable from the package."""
        from mamba_agents.skills import SkillLoadError

        assert SkillLoadError is not None

    def test_import_skill_conflict_error(self) -> None:
        """Test SkillConflictError is importable from the package."""
        from mamba_agents.skills import SkillConflictError

        assert SkillConflictError is not None


class TestSkillsAllExports:
    """Tests for __all__ definition."""

    def test_all_is_defined(self) -> None:
        """Test __all__ is defined in the package."""
        import mamba_agents.skills

        assert hasattr(mamba_agents.skills, "__all__")

    def test_all_contains_expected_symbols(self) -> None:
        """Test __all__ contains all required public symbols."""
        from mamba_agents.skills import __all__

        expected = {
            "SkillManager",
            "Skill",
            "SkillInfo",
            "SkillConfig",
            "ValidationResult",
            "SkillScope",
            "TrustLevel",
            "SkillError",
            "SkillNotFoundError",
            "SkillParseError",
            "SkillValidationError",
            "SkillLoadError",
            "SkillConflictError",
        }
        assert expected == set(__all__)

    def test_all_symbols_are_importable(self) -> None:
        """Test every symbol in __all__ is actually importable."""
        import mamba_agents.skills

        for name in mamba_agents.skills.__all__:
            assert hasattr(mamba_agents.skills, name), (
                f"Symbol '{name}' listed in __all__ but not importable"
            )


class TestSkillsNoCircularImports:
    """Tests that importing the package does not cause circular imports."""

    def test_package_imports_cleanly(self) -> None:
        """Test the package can be imported without circular import errors."""
        import importlib

        mod = importlib.import_module("mamba_agents.skills")
        assert mod is not None

    def test_submodule_imports_after_package(self) -> None:
        """Test submodules still work after importing the package."""
        import mamba_agents.skills  # noqa: F401
        from mamba_agents.skills.config import Skill
        from mamba_agents.skills.errors import SkillError

        assert SkillError is not None
        assert Skill is not None
