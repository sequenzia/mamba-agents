"""Tests for MessageQuery public exports in __init__.py files."""

from __future__ import annotations


class TestAgentModuleExports:
    """Tests for exports from mamba_agents.agent."""

    def test_import_message_query_from_agent(self) -> None:
        """MessageQuery is importable from mamba_agents.agent."""
        from mamba_agents.agent import MessageQuery

        assert MessageQuery is not None

    def test_import_message_stats_from_agent(self) -> None:
        """MessageStats is importable from mamba_agents.agent."""
        from mamba_agents.agent import MessageStats

        assert MessageStats is not None

    def test_import_tool_call_info_from_agent(self) -> None:
        """ToolCallInfo is importable from mamba_agents.agent."""
        from mamba_agents.agent import ToolCallInfo

        assert ToolCallInfo is not None

    def test_import_turn_from_agent(self) -> None:
        """Turn is importable from mamba_agents.agent."""
        from mamba_agents.agent import Turn

        assert Turn is not None

    def test_all_message_exports_in_agent_all(self) -> None:
        """All message types are listed in mamba_agents.agent.__all__."""
        import mamba_agents.agent as agent_module

        assert "MessageQuery" in agent_module.__all__
        assert "MessageStats" in agent_module.__all__
        assert "ToolCallInfo" in agent_module.__all__
        assert "Turn" in agent_module.__all__


class TestTopLevelExports:
    """Tests for exports from mamba_agents (top-level package)."""

    def test_import_message_query_from_top_level(self) -> None:
        """MessageQuery is importable from mamba_agents."""
        from mamba_agents import MessageQuery

        assert MessageQuery is not None

    def test_import_message_stats_from_top_level(self) -> None:
        """MessageStats is importable from mamba_agents."""
        from mamba_agents import MessageStats

        assert MessageStats is not None

    def test_import_tool_call_info_from_top_level(self) -> None:
        """ToolCallInfo is importable from mamba_agents."""
        from mamba_agents import ToolCallInfo

        assert ToolCallInfo is not None

    def test_import_turn_from_top_level(self) -> None:
        """Turn is importable from mamba_agents."""
        from mamba_agents import Turn

        assert Turn is not None

    def test_all_message_exports_in_top_level_all(self) -> None:
        """All message types are listed in mamba_agents.__all__."""
        import mamba_agents

        assert "MessageQuery" in mamba_agents.__all__
        assert "MessageStats" in mamba_agents.__all__
        assert "ToolCallInfo" in mamba_agents.__all__
        assert "Turn" in mamba_agents.__all__


class TestExportIdentity:
    """Tests that exports from different paths resolve to the same objects."""

    def test_message_query_identity(self) -> None:
        """MessageQuery from top-level and agent module are the same class."""
        from mamba_agents import MessageQuery as TopLevel
        from mamba_agents.agent import MessageQuery as AgentLevel
        from mamba_agents.agent.messages import MessageQuery as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is ModuleLevel

    def test_message_stats_identity(self) -> None:
        """MessageStats from top-level and agent module are the same class."""
        from mamba_agents import MessageStats as TopLevel
        from mamba_agents.agent import MessageStats as AgentLevel
        from mamba_agents.agent.messages import MessageStats as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is ModuleLevel

    def test_tool_call_info_identity(self) -> None:
        """ToolCallInfo from top-level and agent module are the same class."""
        from mamba_agents import ToolCallInfo as TopLevel
        from mamba_agents.agent import ToolCallInfo as AgentLevel
        from mamba_agents.agent.messages import ToolCallInfo as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is ModuleLevel

    def test_turn_identity(self) -> None:
        """Turn from top-level and agent module are the same class."""
        from mamba_agents import Turn as TopLevel
        from mamba_agents.agent import Turn as AgentLevel
        from mamba_agents.agent.messages import Turn as ModuleLevel

        assert TopLevel is AgentLevel
        assert AgentLevel is ModuleLevel


class TestExistingExportsUnchanged:
    """Tests that existing exports still work after the additions."""

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

    def test_agent_module_existing_exports(self) -> None:
        """Existing agent module exports are still present."""
        from mamba_agents.agent import (
            Agent,
            AgentConfig,
            AgentResult,
            dicts_to_model_messages,
            model_messages_to_dicts,
        )

        assert Agent is not None
        assert AgentConfig is not None
        assert AgentResult is not None
        assert dicts_to_model_messages is not None
        assert model_messages_to_dicts is not None
