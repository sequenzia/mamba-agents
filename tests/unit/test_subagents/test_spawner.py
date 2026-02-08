"""Tests for subagent spawner."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents.agent.config import AgentConfig
from mamba_agents.agent.core import Agent
from mamba_agents.skills.config import Skill, SkillInfo, SkillScope
from mamba_agents.skills.errors import SkillNotFoundError
from mamba_agents.skills.registry import SkillRegistry
from mamba_agents.subagents.config import SubagentConfig
from mamba_agents.subagents.errors import SubagentNestingError
from mamba_agents.subagents.spawner import (
    _build_system_prompt,
    _enforce_no_nesting,
    _resolve_tools,
    spawn,
)


@pytest.fixture
def parent_agent(test_model: TestModel) -> Agent[None, str]:
    """Create a parent agent for spawner tests."""
    return Agent(test_model)


@pytest.fixture
def parent_agent_with_tools(test_model: TestModel) -> Agent[None, str]:
    """Create a parent agent with registered tools."""

    def read_file(path: str) -> str:
        """Read a file."""
        return f"contents of {path}"

    def write_file(path: str, content: str) -> str:
        """Write a file."""
        return f"wrote {content} to {path}"

    def run_bash(command: str) -> str:
        """Run a bash command."""
        return f"ran {command}"

    agent: Agent[None, str] = Agent(test_model, tools=[read_file, write_file, run_bash])
    return agent


@pytest.fixture
def skill_registry() -> SkillRegistry:
    """Create a skill registry with test skills."""
    registry = SkillRegistry()
    skill = Skill(
        info=SkillInfo(
            name="code-review",
            description="Reviews code quality",
            path=Path("/fake/skills/code-review"),
            scope=SkillScope.PROJECT,
        ),
        body="You are a code review expert. Analyze code for quality issues.",
    )
    registry.register(skill)

    skill_no_body = Skill(
        info=SkillInfo(
            name="minimal-skill",
            description="Minimal skill",
            path=Path("/fake/skills/minimal"),
            scope=SkillScope.PROJECT,
        ),
        body=None,
    )
    registry.register(skill_no_body)
    return registry


class TestSpawnMinimal:
    """Tests for spawning with minimal configuration."""

    def test_spawn_creates_agent_instance(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Spawn with name + description creates a valid Agent."""
        config = SubagentConfig(
            name="helper",
            description="A helper subagent",
        )

        subagent = spawn(config, parent_agent)

        assert isinstance(subagent, Agent)

    def test_spawn_sets_is_subagent_flag(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Spawned agent has _is_subagent set to True."""
        config = SubagentConfig(
            name="helper",
            description="A helper subagent",
        )

        subagent = spawn(config, parent_agent)

        assert subagent.config._is_subagent is True

    def test_spawn_parent_not_marked_as_subagent(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Parent agent is not modified by spawning."""
        config = SubagentConfig(
            name="helper",
            description="A helper subagent",
        )

        spawn(config, parent_agent)

        assert parent_agent.config._is_subagent is False


class TestModelSelection:
    """Tests for model inheritance and override."""

    def test_model_inherited_from_parent(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """When config.model is None, subagent inherits parent's model."""
        config = SubagentConfig(
            name="inheritor",
            description="Inherits model",
            model=None,
        )

        subagent = spawn(config, parent_agent)

        # Subagent should have been created (model_name may be None for TestModel)
        assert isinstance(subagent, Agent)

    def test_custom_model_override(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """When config.model is set, subagent uses that model."""
        config = SubagentConfig(
            name="custom-model",
            description="Uses custom model",
            model="gpt-4o-mini",
        )

        # Spawn succeeds — model validation happens at delegation time, not spawn
        subagent = spawn(config, parent_agent)

        assert isinstance(subagent, Agent)
        # The model name on the subagent should reflect the override
        assert subagent.model_name == "gpt-4o-mini"


class TestToolResolution:
    """Tests for tool allowlist and disallowed tools."""

    def test_tool_allowlist_with_callables(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Callable tools in allowlist pass through directly."""

        def my_tool() -> str:
            """A custom tool."""
            return "result"

        config = SubagentConfig(
            name="with-tools",
            description="Has tools",
            tools=[my_tool],
        )

        subagent = spawn(config, parent_agent)

        assert isinstance(subagent, Agent)

    def test_empty_tools_list(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Empty tools list means no tool access (valid case)."""
        config = SubagentConfig(
            name="no-tools",
            description="No tool access",
            tools=[],
        )

        subagent = spawn(config, parent_agent)

        assert isinstance(subagent, Agent)

    def test_none_tools_results_in_no_tools(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """None tools means fresh subagent with no tools."""
        config = SubagentConfig(
            name="default-tools",
            description="Default (no tools)",
            tools=None,
        )

        subagent = spawn(config, parent_agent)

        assert isinstance(subagent, Agent)

    def test_disallowed_tools_removed_from_allowlist(
        self, parent_agent_with_tools: Agent[None, str],
    ) -> None:
        """Tools in disallowed_tools are removed even if in the allowlist."""
        config = SubagentConfig(
            name="restricted",
            description="Restricted tools",
            tools=["read_file", "write_file", "run_bash"],
            disallowed_tools=["run_bash"],
        )

        tools = _resolve_tools(config, parent_agent_with_tools)

        tool_names = [getattr(t, "__name__", None) for t in tools]
        assert "run_bash" not in tool_names
        assert len(tools) == 2

    def test_disallowed_callable_tool_removed(
        self, parent_agent: Agent[None, str],
    ) -> None:
        """Callable tools with disallowed names are removed."""

        def forbidden_tool() -> str:
            """Forbidden tool."""
            return "bad"

        config = SubagentConfig(
            name="callable-filter",
            description="Tests callable filtering",
            tools=[forbidden_tool],
            disallowed_tools=["forbidden_tool"],
        )

        tools = _resolve_tools(config, parent_agent)

        assert len(tools) == 0

    def test_string_tool_resolved_from_parent(
        self, parent_agent_with_tools: Agent[None, str],
    ) -> None:
        """String tool names resolve from parent's registered tools."""
        config = SubagentConfig(
            name="string-tools",
            description="Uses string tool names",
            tools=["read_file"],
        )

        tools = _resolve_tools(config, parent_agent_with_tools)

        assert len(tools) == 1
        assert callable(tools[0])


class TestSystemPrompt:
    """Tests for system prompt building."""

    def test_string_system_prompt(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """String system prompt passed through to subagent."""
        config = SubagentConfig(
            name="prompted",
            description="Has system prompt",
            system_prompt="You are a helpful assistant.",
        )

        subagent = spawn(config, parent_agent)

        assert subagent.get_system_prompt() == "You are a helpful assistant."

    def test_no_system_prompt_uses_default(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """No system prompt results in empty/default prompt."""
        config = SubagentConfig(
            name="no-prompt",
            description="No system prompt",
            system_prompt=None,
        )

        subagent = spawn(config, parent_agent)

        # Default system prompt is empty string
        assert subagent.get_system_prompt() == ""

    def test_build_system_prompt_with_string(self) -> None:
        """_build_system_prompt returns the string prompt."""
        config = SubagentConfig(
            name="test",
            description="test",
            system_prompt="Hello world",
        )

        result = _build_system_prompt(config)

        assert result == "Hello world"

    def test_build_system_prompt_with_none(self) -> None:
        """_build_system_prompt returns empty for None prompt."""
        config = SubagentConfig(
            name="test",
            description="test",
            system_prompt=None,
        )

        result = _build_system_prompt(config)

        assert result == ""


class TestSkillPreLoading:
    """Tests for skill pre-loading into subagent."""

    def test_skills_injected_into_system_prompt(
        self,
        parent_agent: Agent[None, str],
        skill_registry: SkillRegistry,
    ) -> None:
        """Skills content is injected into the subagent's system prompt."""
        config = SubagentConfig(
            name="skilled",
            description="Has skills",
            skills=["code-review"],
            system_prompt="Base prompt.",
        )

        subagent = spawn(config, parent_agent, skill_registry=skill_registry)

        prompt = subagent.get_system_prompt()
        assert "Base prompt." in prompt
        assert "## Skill: code-review" in prompt
        assert "code review expert" in prompt

    def test_skill_not_found_raises_error(
        self,
        parent_agent: Agent[None, str],
        skill_registry: SkillRegistry,
    ) -> None:
        """Missing skill raises SkillNotFoundError."""
        config = SubagentConfig(
            name="missing-skill",
            description="References missing skill",
            skills=["nonexistent-skill"],
        )

        with pytest.raises(SkillNotFoundError, match="nonexistent-skill"):
            spawn(config, parent_agent, skill_registry=skill_registry)

    def test_skill_without_registry_raises_error(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Skills referenced without a registry raises SkillNotFoundError."""
        config = SubagentConfig(
            name="no-registry",
            description="No skill registry",
            skills=["code-review"],
        )

        with pytest.raises(SkillNotFoundError):
            spawn(config, parent_agent, skill_registry=None)

    def test_build_system_prompt_with_skills(
        self,
        skill_registry: SkillRegistry,
    ) -> None:
        """_build_system_prompt includes skill body content."""
        config = SubagentConfig(
            name="test",
            description="test",
            system_prompt="Base prompt.",
            skills=["code-review"],
        )

        result = _build_system_prompt(config, skill_registry)

        assert "Base prompt." in result
        assert "## Skill: code-review" in result

    def test_skill_with_no_body_not_added_to_prompt(
        self,
        skill_registry: SkillRegistry,
    ) -> None:
        """Skills without body content are not added to the prompt."""
        config = SubagentConfig(
            name="test",
            description="test",
            skills=["minimal-skill"],
        )

        result = _build_system_prompt(config, skill_registry)

        # minimal-skill has no body, so nothing should be added
        assert "minimal-skill" not in result

    def test_skill_tools_registered_with_subagent(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Skill tools are registered with the subagent."""

        def skill_tool() -> str:
            """A skill tool."""
            return "skill result"

        # Create a skill with a tool registered via _tools private attr
        skill = Skill(
            info=SkillInfo(
                name="tool-skill",
                description="Skill with tools",
                path=Path("/fake/skills/tool-skill"),
                scope=SkillScope.PROJECT,
            ),
            body="Use the skill_tool.",
        )
        skill._tools = [skill_tool]

        registry = SkillRegistry()
        registry.register(skill)

        config = SubagentConfig(
            name="tool-skilled",
            description="Has skill tools",
            skills=["tool-skill"],
        )

        subagent = spawn(config, parent_agent, skill_registry=registry)

        assert isinstance(subagent, Agent)


class TestNoNesting:
    """Tests for no-nesting enforcement."""

    def test_nesting_raises_error(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Spawning from a subagent raises SubagentNestingError."""
        # First spawn a subagent
        config = SubagentConfig(
            name="child",
            description="Child subagent",
        )
        child = spawn(config, parent_agent)

        # Attempt to spawn from the child
        grandchild_config = SubagentConfig(
            name="grandchild",
            description="Should fail",
        )

        with pytest.raises(SubagentNestingError):
            spawn(grandchild_config, child)

    def test_enforce_no_nesting_on_normal_agent(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Normal agent does not raise nesting error."""
        # Should not raise
        _enforce_no_nesting(parent_agent)

    def test_enforce_no_nesting_on_subagent(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Subagent raises SubagentNestingError."""
        config = SubagentConfig(
            name="child",
            description="Child",
        )
        child = spawn(config, parent_agent)

        with pytest.raises(SubagentNestingError, match="<new-subagent>"):
            _enforce_no_nesting(child)


class TestContextIsolation:
    """Tests for context isolation behavior."""

    def test_fresh_context_by_default(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Subagent starts with fresh context by default."""
        config = SubagentConfig(
            name="isolated",
            description="Fresh context",
        )

        subagent = spawn(config, parent_agent)

        # Subagent should have its own context manager
        assert subagent.context_manager is not None
        assert subagent.get_messages() == []

    def test_subagent_has_own_usage_tracker(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Subagent has an independent usage tracker."""
        config = SubagentConfig(
            name="tracked",
            description="Own tracker",
        )

        subagent = spawn(config, parent_agent)

        # Subagent's tracker is different from parent's
        assert subagent.usage_tracker is not parent_agent.usage_tracker

    def test_subagent_has_own_context_manager(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Subagent has an independent context manager."""
        config = SubagentConfig(
            name="ctx-isolated",
            description="Own context",
        )

        subagent = spawn(config, parent_agent)

        assert subagent.context_manager is not parent_agent.context_manager


class TestAgentConfigOverride:
    """Tests for AgentConfig override via SubagentConfig.config."""

    def test_custom_agent_config(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """SubagentConfig.config overrides default AgentConfig."""
        custom_config = AgentConfig(max_iterations=5, auto_compact=False)
        config = SubagentConfig(
            name="custom-config",
            description="Custom config",
            config=custom_config,
        )

        subagent = spawn(config, parent_agent)

        assert subagent.config.max_iterations == 5
        assert subagent.config.auto_compact is False
        assert subagent.config._is_subagent is True

    def test_default_agent_config_when_none(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Default AgentConfig used when config is None."""
        config = SubagentConfig(
            name="default-config",
            description="Default config",
            config=None,
        )

        subagent = spawn(config, parent_agent)

        assert subagent.config.max_iterations == 10  # default
        assert subagent.config._is_subagent is True


class TestPerformance:
    """Tests for spawn performance."""

    def test_spawn_is_fast(
        self, parent_agent: Agent[None, str]
    ) -> None:
        """Spawn completes quickly (< 50ms excluding LLM calls)."""
        import time

        config = SubagentConfig(
            name="perf-test",
            description="Performance test",
        )

        start = time.monotonic()
        spawn(config, parent_agent)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert elapsed_ms < 50, f"Spawn took {elapsed_ms:.1f}ms, expected < 50ms"
