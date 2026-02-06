"""Tests for subagents package __init__.py exports."""

from __future__ import annotations


class TestSubagentsPackageExports:
    """Tests that all public symbols are importable from mamba_agents.subagents."""

    def test_import_subagent_manager(self) -> None:
        """Test SubagentManager is importable from the package."""
        from mamba_agents.subagents import SubagentManager

        assert SubagentManager is not None

    def test_import_subagent_config(self) -> None:
        """Test SubagentConfig is importable from the package."""
        from mamba_agents.subagents import SubagentConfig

        assert SubagentConfig is not None

    def test_import_subagent_result(self) -> None:
        """Test SubagentResult is importable from the package."""
        from mamba_agents.subagents import SubagentResult

        assert SubagentResult is not None

    def test_import_delegation_handle(self) -> None:
        """Test DelegationHandle is importable from the package."""
        from mamba_agents.subagents import DelegationHandle

        assert DelegationHandle is not None

    def test_import_subagent_error(self) -> None:
        """Test SubagentError is importable from the package."""
        from mamba_agents.subagents import SubagentError

        assert SubagentError is not None

    def test_import_subagent_config_error(self) -> None:
        """Test SubagentConfigError is importable from the package."""
        from mamba_agents.subagents import SubagentConfigError

        assert SubagentConfigError is not None

    def test_import_subagent_not_found_error(self) -> None:
        """Test SubagentNotFoundError is importable from the package."""
        from mamba_agents.subagents import SubagentNotFoundError

        assert SubagentNotFoundError is not None

    def test_import_subagent_nesting_error(self) -> None:
        """Test SubagentNestingError is importable from the package."""
        from mamba_agents.subagents import SubagentNestingError

        assert SubagentNestingError is not None

    def test_import_subagent_delegation_error(self) -> None:
        """Test SubagentDelegationError is importable from the package."""
        from mamba_agents.subagents import SubagentDelegationError

        assert SubagentDelegationError is not None

    def test_import_subagent_timeout_error(self) -> None:
        """Test SubagentTimeoutError is importable from the package."""
        from mamba_agents.subagents import SubagentTimeoutError

        assert SubagentTimeoutError is not None


class TestSubagentsAllExports:
    """Tests for __all__ definition."""

    def test_all_is_defined(self) -> None:
        """Test __all__ is defined in the package."""
        import mamba_agents.subagents

        assert hasattr(mamba_agents.subagents, "__all__")

    def test_all_contains_expected_symbols(self) -> None:
        """Test __all__ contains all required public symbols."""
        from mamba_agents.subagents import __all__

        expected = {
            "SubagentManager",
            "SubagentConfig",
            "SubagentResult",
            "DelegationHandle",
            "SubagentError",
            "SubagentConfigError",
            "SubagentNotFoundError",
            "SubagentNestingError",
            "SubagentDelegationError",
            "SubagentTimeoutError",
        }
        assert expected == set(__all__)

    def test_all_is_alphabetically_sorted(self) -> None:
        """Test __all__ entries are alphabetically sorted."""
        from mamba_agents.subagents import __all__

        assert list(__all__) == sorted(__all__)

    def test_all_symbols_are_importable(self) -> None:
        """Test every symbol in __all__ is actually importable."""
        import mamba_agents.subagents

        for name in mamba_agents.subagents.__all__:
            assert hasattr(mamba_agents.subagents, name), (
                f"Symbol '{name}' listed in __all__ but not importable"
            )


class TestSubagentsNoCircularImports:
    """Tests that importing the package does not cause circular imports."""

    def test_package_imports_cleanly(self) -> None:
        """Test the package can be imported without circular import errors."""
        import importlib

        mod = importlib.import_module("mamba_agents.subagents")
        assert mod is not None

    def test_submodule_imports_after_package(self) -> None:
        """Test submodules still work after importing the package."""
        import mamba_agents.subagents  # noqa: F401
        from mamba_agents.subagents.config import SubagentConfig
        from mamba_agents.subagents.errors import SubagentError

        assert SubagentError is not None
        assert SubagentConfig is not None
