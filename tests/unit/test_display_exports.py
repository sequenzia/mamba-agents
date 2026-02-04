"""Tests for display module public exports in __init__.py files."""

from __future__ import annotations


class TestDisplayModuleExports:
    """Tests for exports from mamba_agents.agent.display."""

    def test_import_display_preset(self) -> None:
        """DisplayPreset is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import DisplayPreset

        assert DisplayPreset is not None

    def test_import_message_renderer(self) -> None:
        """MessageRenderer is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import MessageRenderer

        assert MessageRenderer is not None

    def test_import_rich_renderer(self) -> None:
        """RichRenderer is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import RichRenderer

        assert RichRenderer is not None

    def test_import_plain_text_renderer(self) -> None:
        """PlainTextRenderer is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import PlainTextRenderer

        assert PlainTextRenderer is not None

    def test_import_html_renderer(self) -> None:
        """HtmlRenderer is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import HtmlRenderer

        assert HtmlRenderer is not None

    def test_import_print_stats(self) -> None:
        """print_stats is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import print_stats

        assert print_stats is not None

    def test_import_print_timeline(self) -> None:
        """print_timeline is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import print_timeline

        assert print_timeline is not None

    def test_import_print_tools(self) -> None:
        """print_tools is importable from mamba_agents.agent.display."""
        from mamba_agents.agent.display import print_tools

        assert print_tools is not None

    def test_all_display_exports_in_display_all(self) -> None:
        """All display public symbols are listed in display __all__."""
        import mamba_agents.agent.display as display_module

        expected = [
            "COMPACT",
            "DETAILED",
            "VERBOSE",
            "DisplayPreset",
            "HtmlRenderer",
            "MessageRenderer",
            "PlainTextRenderer",
            "RichRenderer",
            "get_preset",
            "print_stats",
            "print_timeline",
            "print_tools",
        ]
        for name in expected:
            assert name in display_module.__all__, f"{name} missing from display __all__"


class TestAgentModuleDisplayExports:
    """Tests for display re-exports from mamba_agents.agent."""

    def test_import_display_preset_from_agent(self) -> None:
        """DisplayPreset is importable from mamba_agents.agent."""
        from mamba_agents.agent import DisplayPreset

        assert DisplayPreset is not None

    def test_import_message_renderer_from_agent(self) -> None:
        """MessageRenderer is importable from mamba_agents.agent."""
        from mamba_agents.agent import MessageRenderer

        assert MessageRenderer is not None

    def test_import_rich_renderer_from_agent(self) -> None:
        """RichRenderer is importable from mamba_agents.agent."""
        from mamba_agents.agent import RichRenderer

        assert RichRenderer is not None

    def test_import_plain_text_renderer_from_agent(self) -> None:
        """PlainTextRenderer is importable from mamba_agents.agent."""
        from mamba_agents.agent import PlainTextRenderer

        assert PlainTextRenderer is not None

    def test_import_html_renderer_from_agent(self) -> None:
        """HtmlRenderer is importable from mamba_agents.agent."""
        from mamba_agents.agent import HtmlRenderer

        assert HtmlRenderer is not None

    def test_import_print_stats_from_agent(self) -> None:
        """print_stats is importable from mamba_agents.agent."""
        from mamba_agents.agent import print_stats

        assert print_stats is not None

    def test_import_print_timeline_from_agent(self) -> None:
        """print_timeline is importable from mamba_agents.agent."""
        from mamba_agents.agent import print_timeline

        assert print_timeline is not None

    def test_import_print_tools_from_agent(self) -> None:
        """print_tools is importable from mamba_agents.agent."""
        from mamba_agents.agent import print_tools

        assert print_tools is not None

    def test_all_display_exports_in_agent_all(self) -> None:
        """All display symbols are listed in mamba_agents.agent.__all__."""
        import mamba_agents.agent as agent_module

        expected = [
            "DisplayPreset",
            "HtmlRenderer",
            "MessageRenderer",
            "PlainTextRenderer",
            "RichRenderer",
            "print_stats",
            "print_timeline",
            "print_tools",
        ]
        for name in expected:
            assert name in agent_module.__all__, f"{name} missing from agent __all__"


class TestTopLevelDisplayExports:
    """Tests for display exports from mamba_agents (top-level package)."""

    def test_import_print_stats_from_top_level(self) -> None:
        """print_stats is importable from mamba_agents."""
        from mamba_agents import print_stats

        assert print_stats is not None

    def test_import_print_timeline_from_top_level(self) -> None:
        """print_timeline is importable from mamba_agents."""
        from mamba_agents import print_timeline

        assert print_timeline is not None

    def test_import_print_tools_from_top_level(self) -> None:
        """print_tools is importable from mamba_agents."""
        from mamba_agents import print_tools

        assert print_tools is not None

    def test_import_display_preset_from_top_level(self) -> None:
        """DisplayPreset is importable from mamba_agents."""
        from mamba_agents import DisplayPreset

        assert DisplayPreset is not None

    def test_import_message_renderer_from_top_level(self) -> None:
        """MessageRenderer is importable from mamba_agents."""
        from mamba_agents import MessageRenderer

        assert MessageRenderer is not None

    def test_import_rich_renderer_from_top_level(self) -> None:
        """RichRenderer is importable from mamba_agents."""
        from mamba_agents import RichRenderer

        assert RichRenderer is not None

    def test_import_plain_text_renderer_from_top_level(self) -> None:
        """PlainTextRenderer is importable from mamba_agents."""
        from mamba_agents import PlainTextRenderer

        assert PlainTextRenderer is not None

    def test_import_html_renderer_from_top_level(self) -> None:
        """HtmlRenderer is importable from mamba_agents."""
        from mamba_agents import HtmlRenderer

        assert HtmlRenderer is not None

    def test_all_display_exports_in_top_level_all(self) -> None:
        """All display symbols are listed in mamba_agents.__all__."""
        import mamba_agents

        expected = [
            "DisplayPreset",
            "HtmlRenderer",
            "MessageRenderer",
            "PlainTextRenderer",
            "RichRenderer",
            "print_stats",
            "print_timeline",
            "print_tools",
        ]
        for name in expected:
            assert name in mamba_agents.__all__, f"{name} missing from top-level __all__"


class TestDisplayExportIdentity:
    """Tests that display exports from different paths resolve to the same objects."""

    def test_display_preset_identity(self) -> None:
        """DisplayPreset from all import paths is the same class."""
        from mamba_agents import DisplayPreset as TopLevel
        from mamba_agents.agent import DisplayPreset as AgentLevel
        from mamba_agents.agent.display import DisplayPreset as DisplayLevel
        from mamba_agents.agent.display.presets import DisplayPreset as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel

    def test_message_renderer_identity(self) -> None:
        """MessageRenderer from all import paths is the same class."""
        from mamba_agents import MessageRenderer as TopLevel
        from mamba_agents.agent import MessageRenderer as AgentLevel
        from mamba_agents.agent.display import MessageRenderer as DisplayLevel
        from mamba_agents.agent.display.renderer import MessageRenderer as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel

    def test_rich_renderer_identity(self) -> None:
        """RichRenderer from all import paths is the same class."""
        from mamba_agents import RichRenderer as TopLevel
        from mamba_agents.agent import RichRenderer as AgentLevel
        from mamba_agents.agent.display import RichRenderer as DisplayLevel
        from mamba_agents.agent.display.rich_renderer import RichRenderer as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel

    def test_plain_text_renderer_identity(self) -> None:
        """PlainTextRenderer from all import paths is the same class."""
        from mamba_agents import PlainTextRenderer as TopLevel
        from mamba_agents.agent import PlainTextRenderer as AgentLevel
        from mamba_agents.agent.display import PlainTextRenderer as DisplayLevel
        from mamba_agents.agent.display.plain_renderer import PlainTextRenderer as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel

    def test_html_renderer_identity(self) -> None:
        """HtmlRenderer from all import paths is the same class."""
        from mamba_agents import HtmlRenderer as TopLevel
        from mamba_agents.agent import HtmlRenderer as AgentLevel
        from mamba_agents.agent.display import HtmlRenderer as DisplayLevel
        from mamba_agents.agent.display.html_renderer import HtmlRenderer as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel

    def test_print_stats_identity(self) -> None:
        """print_stats from all import paths is the same function."""
        from mamba_agents import print_stats as TopLevel
        from mamba_agents.agent import print_stats as AgentLevel
        from mamba_agents.agent.display import print_stats as DisplayLevel
        from mamba_agents.agent.display.functions import print_stats as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel

    def test_print_timeline_identity(self) -> None:
        """print_timeline from all import paths is the same function."""
        from mamba_agents import print_timeline as TopLevel
        from mamba_agents.agent import print_timeline as AgentLevel
        from mamba_agents.agent.display import print_timeline as DisplayLevel
        from mamba_agents.agent.display.functions import print_timeline as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel

    def test_print_tools_identity(self) -> None:
        """print_tools from all import paths is the same function."""
        from mamba_agents import print_tools as TopLevel
        from mamba_agents.agent import print_tools as AgentLevel
        from mamba_agents.agent.display import print_tools as DisplayLevel
        from mamba_agents.agent.display.functions import print_tools as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is DisplayLevel
        assert DisplayLevel is ModuleLevel


class TestNoCircularImports:
    """Tests that display imports do not cause circular import issues."""

    def test_import_display_module_directly(self) -> None:
        """Importing display module directly does not raise ImportError."""
        import mamba_agents.agent.display

        assert mamba_agents.agent.display is not None

    def test_import_agent_module_with_display(self) -> None:
        """Importing agent module (with display re-exports) does not raise."""
        import mamba_agents.agent

        assert mamba_agents.agent is not None

    def test_import_top_level_with_display(self) -> None:
        """Importing top-level package (with display exports) does not raise."""
        import mamba_agents

        assert mamba_agents is not None

    def test_import_display_then_messages(self) -> None:
        """Importing display before messages does not cause circular import."""
        from mamba_agents.agent.display import RichRenderer
        from mamba_agents.agent.messages import MessageQuery

        assert RichRenderer is not None
        assert MessageQuery is not None

    def test_import_messages_then_display(self) -> None:
        """Importing messages before display does not cause circular import."""
        from mamba_agents.agent.display import RichRenderer
        from mamba_agents.agent.messages import MessageQuery

        assert MessageQuery is not None
        assert RichRenderer is not None


class TestExistingExportsUnchanged:
    """Tests that existing exports still work after display additions."""

    def test_agent_still_importable(self) -> None:
        """Agent is still importable from top-level."""
        from mamba_agents import Agent

        assert Agent is not None

    def test_agent_config_still_importable(self) -> None:
        """AgentConfig is still importable from top-level."""
        from mamba_agents import AgentConfig

        assert AgentConfig is not None

    def test_agent_result_still_importable(self) -> None:
        """AgentResult is still importable from top-level."""
        from mamba_agents import AgentResult

        assert AgentResult is not None

    def test_message_query_still_importable(self) -> None:
        """MessageQuery is still importable from top-level."""
        from mamba_agents import MessageQuery

        assert MessageQuery is not None

    def test_agent_module_existing_exports(self) -> None:
        """Existing agent module exports are still present."""
        from mamba_agents.agent import (
            Agent,
            AgentConfig,
            AgentResult,
            MessageQuery,
            MessageStats,
            ToolCallInfo,
            Turn,
            dicts_to_model_messages,
            model_messages_to_dicts,
        )

        assert Agent is not None
        assert AgentConfig is not None
        assert AgentResult is not None
        assert MessageQuery is not None
        assert MessageStats is not None
        assert ToolCallInfo is not None
        assert Turn is not None
        assert dicts_to_model_messages is not None
        assert model_messages_to_dicts is not None
