"""Tests for root mamba_agents package __init__.py exports."""

from __future__ import annotations


class TestRootPackageSkillExports:
    """Tests that all skill symbols are importable from mamba_agents root."""

    def test_import_skill_manager(self) -> None:
        """Test SkillManager is importable from the root package."""
        from mamba_agents import SkillManager

        assert SkillManager is not None

    def test_import_skill(self) -> None:
        """Test Skill is importable from the root package."""
        from mamba_agents import Skill

        assert Skill is not None

    def test_import_skill_info(self) -> None:
        """Test SkillInfo is importable from the root package."""
        from mamba_agents import SkillInfo

        assert SkillInfo is not None

    def test_import_skill_config(self) -> None:
        """Test SkillConfig is importable from the root package."""
        from mamba_agents import SkillConfig

        assert SkillConfig is not None

    def test_import_validation_result(self) -> None:
        """Test ValidationResult is importable from the root package."""
        from mamba_agents import ValidationResult

        assert ValidationResult is not None

    def test_import_skill_scope(self) -> None:
        """Test SkillScope is importable from the root package."""
        from mamba_agents import SkillScope

        assert SkillScope is not None

    def test_import_trust_level(self) -> None:
        """Test TrustLevel is importable from the root package."""
        from mamba_agents import TrustLevel

        assert TrustLevel is not None

    def test_import_skill_error(self) -> None:
        """Test SkillError is importable from the root package."""
        from mamba_agents import SkillError

        assert SkillError is not None

    def test_import_skill_not_found_error(self) -> None:
        """Test SkillNotFoundError is importable from the root package."""
        from mamba_agents import SkillNotFoundError

        assert SkillNotFoundError is not None

    def test_import_skill_parse_error(self) -> None:
        """Test SkillParseError is importable from the root package."""
        from mamba_agents import SkillParseError

        assert SkillParseError is not None

    def test_import_skill_validation_error(self) -> None:
        """Test SkillValidationError is importable from the root package."""
        from mamba_agents import SkillValidationError

        assert SkillValidationError is not None

    def test_import_skill_load_error(self) -> None:
        """Test SkillLoadError is importable from the root package."""
        from mamba_agents import SkillLoadError

        assert SkillLoadError is not None

    def test_import_skill_conflict_error(self) -> None:
        """Test SkillConflictError is importable from the root package."""
        from mamba_agents import SkillConflictError

        assert SkillConflictError is not None


class TestRootPackageSubagentExports:
    """Tests that all subagent symbols are importable from mamba_agents root."""

    def test_import_subagent_manager(self) -> None:
        """Test SubagentManager is importable from the root package."""
        from mamba_agents import SubagentManager

        assert SubagentManager is not None

    def test_import_subagent_config(self) -> None:
        """Test SubagentConfig is importable from the root package."""
        from mamba_agents import SubagentConfig

        assert SubagentConfig is not None

    def test_import_subagent_result(self) -> None:
        """Test SubagentResult is importable from the root package."""
        from mamba_agents import SubagentResult

        assert SubagentResult is not None

    def test_import_delegation_handle(self) -> None:
        """Test DelegationHandle is importable from the root package."""
        from mamba_agents import DelegationHandle

        assert DelegationHandle is not None

    def test_import_subagent_error(self) -> None:
        """Test SubagentError is importable from the root package."""
        from mamba_agents import SubagentError

        assert SubagentError is not None

    def test_import_subagent_config_error(self) -> None:
        """Test SubagentConfigError is importable from the root package."""
        from mamba_agents import SubagentConfigError

        assert SubagentConfigError is not None

    def test_import_subagent_not_found_error(self) -> None:
        """Test SubagentNotFoundError is importable from the root package."""
        from mamba_agents import SubagentNotFoundError

        assert SubagentNotFoundError is not None

    def test_import_subagent_nesting_error(self) -> None:
        """Test SubagentNestingError is importable from the root package."""
        from mamba_agents import SubagentNestingError

        assert SubagentNestingError is not None

    def test_import_subagent_delegation_error(self) -> None:
        """Test SubagentDelegationError is importable from the root package."""
        from mamba_agents import SubagentDelegationError

        assert SubagentDelegationError is not None

    def test_import_subagent_timeout_error(self) -> None:
        """Test SubagentTimeoutError is importable from the root package."""
        from mamba_agents import SubagentTimeoutError

        assert SubagentTimeoutError is not None


class TestRootAllExports:
    """Tests for __all__ definition on root package."""

    def test_all_is_defined(self) -> None:
        """Test __all__ is defined in the root package."""
        import mamba_agents

        assert hasattr(mamba_agents, "__all__")

    def test_all_contains_new_skill_symbols(self) -> None:
        """Test __all__ contains all new skill symbols."""
        from mamba_agents import __all__

        skill_symbols = {
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
        assert skill_symbols.issubset(set(__all__))

    def test_all_contains_new_subagent_symbols(self) -> None:
        """Test __all__ contains all new subagent symbols."""
        from mamba_agents import __all__

        subagent_symbols = {
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
        assert subagent_symbols.issubset(set(__all__))

    def test_all_contains_existing_symbols(self) -> None:
        """Test __all__ still contains all pre-existing symbols."""
        from mamba_agents import __all__

        existing_symbols = {
            "Agent",
            "AgentConfig",
            "AgentResult",
            "AgentSettings",
            "CompactionConfig",
            "CompactionResult",
            "ContextState",
            "CostBreakdown",
            "DisplayPreset",
            "HtmlRenderer",
            "MCPAuthConfig",
            "MCPClientManager",
            "MCPServerConfig",
            "MessageQuery",
            "MessageRenderer",
            "MessageStats",
            "PlainTextRenderer",
            "PromptConfig",
            "PromptManager",
            "PromptTemplate",
            "RichRenderer",
            "TemplateConfig",
            "TokenUsage",
            "ToolCallInfo",
            "Turn",
            "UsageRecord",
            "Workflow",
            "WorkflowConfig",
            "WorkflowHooks",
            "WorkflowResult",
            "WorkflowState",
            "WorkflowStep",
            "__version__",
            "print_stats",
            "print_timeline",
            "print_tools",
        }
        assert existing_symbols.issubset(set(__all__))

    def test_all_is_alphabetically_sorted(self) -> None:
        """Test __all__ entries are alphabetically sorted."""
        from mamba_agents import __all__

        assert list(__all__) == sorted(__all__)

    def test_all_symbols_are_importable(self) -> None:
        """Test every symbol in __all__ is actually importable."""
        import mamba_agents

        for name in mamba_agents.__all__:
            assert hasattr(mamba_agents, name), (
                f"Symbol '{name}' listed in __all__ but not importable"
            )


class TestRootNoCircularImports:
    """Tests that importing the root package does not cause circular imports."""

    def test_package_imports_cleanly(self) -> None:
        """Test the root package can be imported without circular import errors."""
        import importlib

        mod = importlib.import_module("mamba_agents")
        assert mod is not None

    def test_submodule_imports_after_root_package(self) -> None:
        """Test submodules still work after importing the root package."""
        import mamba_agents  # noqa: F401
        from mamba_agents.skills import SkillManager
        from mamba_agents.subagents import SubagentManager

        assert SkillManager is not None
        assert SubagentManager is not None

    def test_root_and_subpackage_symbols_are_same_objects(self) -> None:
        """Test symbols from root and subpackage are the same object."""
        from mamba_agents import SkillManager as RootSkillManager
        from mamba_agents import SubagentManager as RootSubagentManager
        from mamba_agents.skills import SkillManager as SubSkillManager
        from mamba_agents.subagents import SubagentManager as SubSubagentManager

        assert RootSkillManager is SubSkillManager
        assert RootSubagentManager is SubSubagentManager


class TestBackwardCompatibility:
    """Tests that existing imports still work after adding new exports."""

    def test_agent_import(self) -> None:
        """Test Agent is still importable from root."""
        from mamba_agents import Agent

        assert Agent is not None

    def test_agent_settings_import(self) -> None:
        """Test AgentSettings is still importable from root."""
        from mamba_agents import AgentSettings

        assert AgentSettings is not None

    def test_workflow_imports(self) -> None:
        """Test workflow symbols are still importable from root."""
        from mamba_agents import Workflow, WorkflowConfig, WorkflowResult

        assert Workflow is not None
        assert WorkflowConfig is not None
        assert WorkflowResult is not None

    def test_mcp_imports(self) -> None:
        """Test MCP symbols are still importable from root."""
        from mamba_agents import MCPAuthConfig, MCPClientManager, MCPServerConfig

        assert MCPAuthConfig is not None
        assert MCPClientManager is not None
        assert MCPServerConfig is not None

    def test_version_import(self) -> None:
        """Test __version__ is still importable from root."""
        from mamba_agents import __version__

        assert isinstance(__version__, str)
