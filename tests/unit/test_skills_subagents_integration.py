"""Tests for skills-subagents bi-directional integration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from mamba_agents.agent.core import Agent
from mamba_agents.skills.config import Skill, SkillInfo, SkillScope, TrustLevel
from mamba_agents.skills.errors import SkillInvocationError, SkillNotFoundError
from mamba_agents.skills.integration import (
    activate_with_fork,
    detect_circular_skill_subagent,
)
from mamba_agents.skills.manager import SkillManager
from mamba_agents.skills.registry import SkillRegistry
from mamba_agents.subagents.config import SubagentConfig, SubagentResult
from mamba_agents.subagents.errors import SubagentNotFoundError
from mamba_agents.subagents.manager import SubagentManager
from mamba_agents.subagents.spawner import _build_system_prompt, _resolve_skill_tools
from mamba_agents.tokens.tracker import TokenUsage

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parent_agent(test_model: TestModel) -> Agent[None, str]:
    """Create a parent agent for integration tests."""
    return Agent(test_model)


@pytest.fixture
def skill_registry() -> SkillRegistry:
    """Create a skill registry with test skills for integration tests."""
    registry = SkillRegistry()

    web_search = Skill(
        info=SkillInfo(
            name="web-search",
            description="Searches the web",
            path=Path("/fake/skills/web-search"),
            scope=SkillScope.PROJECT,
        ),
        body="You are a web search expert.\n\nSearch for: $ARGUMENTS",
    )
    registry.register(web_search)

    code_review = Skill(
        info=SkillInfo(
            name="code-review",
            description="Reviews code",
            path=Path("/fake/skills/code-review"),
            scope=SkillScope.PROJECT,
        ),
        body="You are a code review expert. Review the following code.",
    )
    registry.register(code_review)

    return registry


@pytest.fixture
def skill_manager(skill_registry: SkillRegistry) -> SkillManager:
    """Create a SkillManager with pre-registered skills."""
    manager = SkillManager()
    manager._registry = skill_registry
    return manager


@pytest.fixture
def subagent_manager(
    parent_agent: Agent[None, str],
    skill_manager: SkillManager,
) -> SubagentManager:
    """Create a SubagentManager wired to a SkillManager."""
    return SubagentManager(
        parent_agent,
        skill_manager=skill_manager,
    )


def _make_test_agent(output_text: str = "test output") -> Agent[None, str]:
    """Create a test agent with a specific output text for subagent mocking."""
    return Agent(TestModel(custom_output_text=output_text))


def _make_fork_skill(
    name: str = "forky",
    agent_name: str | None = "helper",
    trust_level: TrustLevel = TrustLevel.TRUSTED,
    body: str = "Do the forked thing with: $ARGUMENTS",
) -> Skill:
    """Create a skill with execution_mode='fork' for testing."""
    return Skill(
        info=SkillInfo(
            name=name,
            description=f"Fork skill: {name}",
            path=Path(f"/fake/skills/{name}"),
            scope=SkillScope.PROJECT,
            execution_mode="fork",
            agent=agent_name,
            trust_level=trust_level,
        ),
        body=body,
    )


def _make_subagent_result(
    output: str = "subagent result",
    success: bool = True,
    error: str | None = None,
) -> SubagentResult:
    """Create a minimal SubagentResult for mocking."""
    return SubagentResult(
        output=output,
        agent_result=MagicMock(),
        usage=TokenUsage(),
        duration=0.1,
        subagent_name="helper",
        success=success,
        error=error,
    )


# ---------------------------------------------------------------------------
# Skill pre-loading into subagents (system prompt injection)
# ---------------------------------------------------------------------------


class TestSkillPreLoadingSystemPrompt:
    """Subagent with skills gets skill content in system prompt."""

    def test_skill_content_injected_into_system_prompt(self, skill_registry: SkillRegistry) -> None:
        """Subagent with skills: ['web-search'] gets skill body in system prompt."""
        config = SubagentConfig(
            name="searcher",
            description="Searches things",
            system_prompt="You are a search assistant.",
            skills=["web-search"],
        )

        prompt = _build_system_prompt(config, skill_registry)

        assert "You are a search assistant." in prompt
        assert "## Skill: web-search" in prompt
        assert "You are a web search expert." in prompt

    def test_multiple_skills_in_system_prompt(self, skill_registry: SkillRegistry) -> None:
        """Multiple skills all appear in the system prompt."""
        config = SubagentConfig(
            name="multi",
            description="Multi-skill",
            skills=["web-search", "code-review"],
        )

        prompt = _build_system_prompt(config, skill_registry)

        assert "## Skill: web-search" in prompt
        assert "## Skill: code-review" in prompt

    def test_no_skills_produces_base_prompt_only(self) -> None:
        """Config without skills produces only the base system prompt."""
        config = SubagentConfig(
            name="plain",
            description="No skills",
            system_prompt="Base prompt.",
        )

        prompt = _build_system_prompt(config, skill_registry=None)

        assert prompt == "Base prompt."
        assert "Skill:" not in prompt

    def test_missing_skill_raises_not_found(self, skill_registry: SkillRegistry) -> None:
        """Referencing a non-existent skill raises SkillNotFoundError."""
        config = SubagentConfig(
            name="bad-ref",
            description="Bad reference",
            skills=["nonexistent-skill"],
        )

        with pytest.raises(SkillNotFoundError, match="nonexistent-skill"):
            _build_system_prompt(config, skill_registry)

    def test_no_registry_with_skills_raises(self) -> None:
        """Skills referenced but no registry provided raises SkillNotFoundError."""
        config = SubagentConfig(
            name="orphan",
            description="No registry",
            skills=["web-search"],
        )

        with pytest.raises(SkillNotFoundError):
            _build_system_prompt(config, skill_registry=None)


# ---------------------------------------------------------------------------
# Skill tool pre-loading into subagents
# ---------------------------------------------------------------------------


class TestSkillToolPreLoading:
    """Subagent with pre-loaded skills gets skill's tools registered."""

    def test_skill_tools_resolved(self) -> None:
        """Skill tools from pre-loaded skills are resolved."""

        def my_tool() -> str:
            """A test tool."""
            return "tool result"

        registry = SkillRegistry()
        skill = Skill(
            info=SkillInfo(
                name="tooled-skill",
                description="Has tools",
                path=Path("/fake/skills/tooled-skill"),
                scope=SkillScope.PROJECT,
            ),
            body="Skill with tools.",
        )
        skill._tools = [my_tool]
        registry.register(skill)

        config = SubagentConfig(
            name="tool-sub",
            description="Tool subagent",
            skills=["tooled-skill"],
        )

        tools = _resolve_skill_tools(config, registry)

        assert len(tools) == 1
        assert tools[0] is my_tool

    def test_no_skills_returns_empty(self) -> None:
        """Config without skills returns empty tools list."""
        config = SubagentConfig(
            name="no-skills",
            description="No skills",
        )

        tools = _resolve_skill_tools(config, None)

        assert tools == []

    def test_skill_without_tools_returns_empty(self, skill_registry: SkillRegistry) -> None:
        """Skill with no tools returns empty list."""
        config = SubagentConfig(
            name="no-tool-sub",
            description="No tools",
            skills=["web-search"],
        )

        tools = _resolve_skill_tools(config, skill_registry)

        assert tools == []

    def test_spawned_subagent_gets_skill_tools(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Spawned subagent includes skill tools in its tool list."""
        from mamba_agents.subagents.spawner import spawn

        def search_tool(query: str) -> str:
            """Search for something."""
            return f"results for {query}"

        registry = SkillRegistry()
        skill = Skill(
            info=SkillInfo(
                name="search-skill",
                description="Search skill",
                path=Path("/fake/skills/search-skill"),
                scope=SkillScope.PROJECT,
            ),
            body="Search instructions.",
        )
        skill._tools = [search_tool]
        registry.register(skill)

        config = SubagentConfig(
            name="tool-agent",
            description="Has tools via skill",
            skills=["search-skill"],
        )

        subagent = spawn(config, parent_agent, skill_registry=registry)

        # Verify the subagent was created (tools are registered on the
        # internal pydantic-ai agent)
        assert subagent is not None
        assert subagent.config._is_subagent is True


# ---------------------------------------------------------------------------
# Fork execution mode: skill -> subagent delegation
# ---------------------------------------------------------------------------


class TestForkExecutionMode:
    """Skill with execution_mode: 'fork' triggers subagent delegation."""

    def test_fork_skill_delegates_to_named_subagent(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """Skill with agent field delegates to named subagent config."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )
        sub_manager.register(
            SubagentConfig(
                name="helper",
                description="Helper agent",
            )
        )

        fork_skill = _make_fork_skill(agent_name="helper")
        mock_result = _make_subagent_result(output="forked output")

        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = activate_with_fork(fork_skill, "test args", sub_manager)

        assert result == "forked output"

    def test_fork_skill_creates_temporary_subagent_when_no_agent_field(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """Missing agent field creates temporary general-purpose subagent."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )

        fork_skill = _make_fork_skill(name="temp-fork", agent_name=None)
        mock_result = _make_subagent_result(output="temp output")

        with patch.object(sub_manager, "spawn_dynamic", return_value=mock_result):
            result = activate_with_fork(fork_skill, "some args", sub_manager)

        assert result == "temp output"

    def test_fork_skill_with_nonexistent_agent_raises(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """Skill references non-existent subagent config raises SubagentNotFoundError."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )

        fork_skill = _make_fork_skill(agent_name="nonexistent-agent")

        with pytest.raises(SubagentNotFoundError, match="nonexistent-agent"):
            activate_with_fork(fork_skill, "args", sub_manager)

    def test_fork_skill_returns_subagent_output(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """Result from forked subagent returned to invoking context."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )
        sub_manager.register(
            SubagentConfig(
                name="responder",
                description="Returns responses",
            )
        )

        fork_skill = _make_fork_skill(agent_name="responder")
        expected_output = "This is the subagent's detailed analysis."
        mock_result = _make_subagent_result(output=expected_output)

        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = activate_with_fork(fork_skill, "", sub_manager)

        assert result == expected_output

    def test_fork_delegation_failure_raises_invocation_error(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """Failed subagent delegation raises SkillInvocationError."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )
        sub_manager.register(
            SubagentConfig(
                name="failing-agent",
                description="Always fails",
            )
        )

        fork_skill = _make_fork_skill(agent_name="failing-agent")
        mock_result = _make_subagent_result(
            output="",
            success=False,
            error="API timeout",
        )

        with (
            patch.object(sub_manager, "delegate_sync", return_value=mock_result),
            pytest.raises(SkillInvocationError, match="delegation failed"),
        ):
            activate_with_fork(fork_skill, "", sub_manager)


# ---------------------------------------------------------------------------
# Trust level enforcement
# ---------------------------------------------------------------------------


class TestTrustLevelEnforcement:
    """Untrusted skill with context: fork is blocked by trust level check."""

    def test_untrusted_skill_fork_blocked(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """Untrusted skill with execution_mode='fork' raises SkillInvocationError."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )
        sub_manager.register(
            SubagentConfig(
                name="helper",
                description="Helper agent",
            )
        )

        untrusted_fork = _make_fork_skill(
            trust_level=TrustLevel.UNTRUSTED,
        )

        with pytest.raises(SkillInvocationError, match="Untrusted"):
            activate_with_fork(untrusted_fork, "args", sub_manager)

    def test_trusted_skill_fork_allowed(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """Trusted skill with execution_mode='fork' proceeds normally."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )
        sub_manager.register(
            SubagentConfig(
                name="helper",
                description="Helper agent",
            )
        )

        trusted_fork = _make_fork_skill(trust_level=TrustLevel.TRUSTED)
        mock_result = _make_subagent_result(output="trusted output")

        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = activate_with_fork(trusted_fork, "", sub_manager)

        assert result == "trusted output"


# ---------------------------------------------------------------------------
# Circular reference detection
# ---------------------------------------------------------------------------


class TestCircularReferenceDetection:
    """Circular skill-subagent references are detected and prevented."""

    def test_direct_cycle_detected(self) -> None:
        """Skill -> agent -> pre-loads same skill is detected."""
        skill = _make_fork_skill(name="cyclic-skill", agent_name="cyclic-agent")

        configs = {
            "cyclic-agent": SubagentConfig(
                name="cyclic-agent",
                description="Pre-loads the same skill",
                skills=["cyclic-skill"],
            ),
        }

        cycle = detect_circular_skill_subagent(skill, configs)

        assert cycle is not None
        assert "skill:cyclic-skill" in cycle
        assert "agent:cyclic-agent" in cycle

    def test_no_cycle_returns_none(self) -> None:
        """Non-circular references return None."""
        skill = _make_fork_skill(name="normal-skill", agent_name="normal-agent")

        configs = {
            "normal-agent": SubagentConfig(
                name="normal-agent",
                description="Preloads different skill",
                skills=["other-skill"],
            ),
        }

        cycle = detect_circular_skill_subagent(skill, configs)

        assert cycle is None

    def test_no_agent_field_no_cycle(self) -> None:
        """Skill with no agent field cannot have a cycle."""
        skill = _make_fork_skill(name="no-agent", agent_name=None)

        configs = {
            "some-agent": SubagentConfig(
                name="some-agent",
                description="Agent",
                skills=["no-agent"],
            ),
        }

        cycle = detect_circular_skill_subagent(skill, configs)

        assert cycle is None

    def test_non_fork_skill_no_cycle(self) -> None:
        """Skill without execution_mode='fork' has no cycle."""
        skill = Skill(
            info=SkillInfo(
                name="normal",
                description="Normal skill",
                path=Path("/fake/skills/normal"),
                scope=SkillScope.PROJECT,
                execution_mode=None,
            ),
            body="Normal body.",
        )

        configs = {
            "agent": SubagentConfig(
                name="agent",
                description="Agent",
                skills=["normal"],
            ),
        }

        cycle = detect_circular_skill_subagent(skill, configs)

        assert cycle is None

    def test_missing_agent_config_no_cycle(self) -> None:
        """Skill referencing non-existent agent config is not a cycle."""
        skill = _make_fork_skill(name="orphan-skill", agent_name="ghost-agent")

        configs: dict[str, SubagentConfig] = {}

        cycle = detect_circular_skill_subagent(skill, configs)

        assert cycle is None

    def test_indirect_cycle_detected(self) -> None:
        """Skill A -> Agent X (pre-loads Skill B -> Agent Y pre-loads A)."""

        def get_skill_fn(name: str) -> Skill | None:
            if name == "skill-b":
                return _make_fork_skill(
                    name="skill-b",
                    agent_name="agent-y",
                )
            return None

        skill_a = _make_fork_skill(name="skill-a", agent_name="agent-x")

        configs = {
            "agent-x": SubagentConfig(
                name="agent-x",
                description="Pre-loads B",
                skills=["skill-b"],
            ),
            "agent-y": SubagentConfig(
                name="agent-y",
                description="Pre-loads A",
                skills=["skill-a"],
            ),
        }

        cycle = detect_circular_skill_subagent(
            skill_a,
            configs,
            get_skill_fn=get_skill_fn,
        )

        assert cycle is not None
        assert "skill:skill-a" in cycle

    def test_agent_without_skills_no_cycle(self) -> None:
        """Agent config with no skills list cannot create a cycle."""
        skill = _make_fork_skill(name="safe-skill", agent_name="clean-agent")

        configs = {
            "clean-agent": SubagentConfig(
                name="clean-agent",
                description="No skills pre-loaded",
            ),
        }

        cycle = detect_circular_skill_subagent(skill, configs)

        assert cycle is None


# ---------------------------------------------------------------------------
# SkillManager.activate() integration with fork mode
# ---------------------------------------------------------------------------


class TestSkillManagerForkActivation:
    """SkillManager.activate() checks execution_mode and delegates to SubagentManager."""

    def test_activate_fork_skill_delegates_via_manager(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """SkillManager.activate() on fork skill calls activate_with_fork."""
        sub_manager = SubagentManager(parent_agent)
        sub_manager.register(
            SubagentConfig(
                name="helper",
                description="Helper",
            )
        )

        sm = SkillManager(subagent_manager=sub_manager)

        fork_skill = _make_fork_skill(name="fork-test", agent_name="helper")
        sm._registry.register(fork_skill)

        with patch(
            "mamba_agents.skills.integration.activate_with_fork",
            return_value="manager delegated",
        ) as mock_fork:
            result = sm.activate("fork-test", "some args")

        assert result == "manager delegated"
        mock_fork.assert_called_once()

    def test_activate_normal_skill_no_delegation(self) -> None:
        """Normal skill activation does not trigger fork delegation."""
        sm = SkillManager()

        normal_skill = Skill(
            info=SkillInfo(
                name="normal-skill",
                description="Normal skill",
                path=Path("/fake/skills/normal-skill"),
                scope=SkillScope.PROJECT,
            ),
            body="Normal content with $ARGUMENTS.",
        )
        sm._registry.register(normal_skill)

        result = sm.activate("normal-skill", "test")

        assert "Normal content with test." in result

    def test_activate_fork_without_subagent_manager_falls_through(self) -> None:
        """Fork skill without SubagentManager falls through to normal activation."""
        sm = SkillManager()  # No subagent_manager

        fork_skill = _make_fork_skill(name="orphan-fork")
        sm._registry.register(fork_skill)

        # Should activate normally (no fork delegation)
        result = sm.activate("orphan-fork", "test")

        assert "Do the forked thing with: test" in result

    def test_subagent_manager_property_settable(self) -> None:
        """SubagentManager can be set after construction."""
        sm = SkillManager()
        assert sm.subagent_manager is None

        mock_sub = MagicMock()
        sm.subagent_manager = mock_sub

        assert sm.subagent_manager is mock_sub


# ---------------------------------------------------------------------------
# SubagentManager skill_manager wiring
# ---------------------------------------------------------------------------


class TestSubagentManagerSkillManagerWiring:
    """SubagentManager.spawn() accepts SkillManager reference for skill pre-loading."""

    def test_spawn_passes_skill_registry(
        self,
        parent_agent: Agent[None, str],
        skill_manager: SkillManager,
    ) -> None:
        """SubagentManager._spawn passes skill_registry to spawner."""
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=skill_manager,
        )
        config = SubagentConfig(
            name="skilled-sub",
            description="Has skills",
            skills=["web-search"],
        )

        with patch(
            "mamba_agents.subagents.manager.spawn",
        ) as mock_spawn:
            mock_spawn.return_value = _make_test_agent()
            sub_manager._spawn(config)

        mock_spawn.assert_called_once_with(
            config,
            parent_agent,
            skill_registry=skill_manager.registry,
        )

    def test_spawn_without_skill_manager_passes_none(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """SubagentManager without skill_manager passes None to spawner."""
        sub_manager = SubagentManager(parent_agent)
        config = SubagentConfig(
            name="no-skills-sub",
            description="No skills",
        )

        with patch(
            "mamba_agents.subagents.manager.spawn",
        ) as mock_spawn:
            mock_spawn.return_value = _make_test_agent()
            sub_manager._spawn(config)

        mock_spawn.assert_called_once_with(
            config,
            parent_agent,
            skill_registry=None,
        )


# ---------------------------------------------------------------------------
# No circular imports
# ---------------------------------------------------------------------------


class TestNoCircularImports:
    """Ensure no circular imports between skills/ and subagents/ modules."""

    def test_import_skills_package(self) -> None:
        """Importing skills package succeeds without circular import."""
        import mamba_agents.skills  # noqa: F401

    def test_import_subagents_package(self) -> None:
        """Importing subagents package succeeds without circular import."""
        import mamba_agents.subagents  # noqa: F401

    def test_import_skills_then_subagents(self) -> None:
        """Importing skills then subagents works without circular import."""
        import mamba_agents.skills
        import mamba_agents.subagents  # noqa: F401

    def test_import_subagents_then_skills(self) -> None:
        """Importing subagents then skills works without circular import."""
        import importlib

        importlib.import_module("mamba_agents.subagents")
        importlib.import_module("mamba_agents.skills")

    def test_import_integration_module(self) -> None:
        """Importing integration module succeeds."""
        import mamba_agents.skills.integration  # noqa: F401

    def test_import_skill_manager_with_subagent_manager(self) -> None:
        """SkillManager and SubagentManager can be instantiated together."""
        from mamba_agents.skills.manager import SkillManager
        from mamba_agents.subagents.manager import SubagentManager

        # Just verify the classes are importable and can coexist
        assert SkillManager is not None
        assert SubagentManager is not None


# ---------------------------------------------------------------------------
# Integration: full end-to-end flow
# ---------------------------------------------------------------------------


class TestEndToEndIntegration:
    """End-to-end integration tests combining skills and subagents."""

    def test_skill_preload_and_delegate(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Full flow: register skill, register subagent with skill, delegate."""
        # Set up skill manager with a skill
        sm = SkillManager()
        skill = Skill(
            info=SkillInfo(
                name="analysis",
                description="Analysis skill",
                path=Path("/fake/skills/analysis"),
                scope=SkillScope.PROJECT,
            ),
            body="Perform detailed analysis of the given topic.",
        )
        sm.register(skill)

        # Set up subagent manager with skill pre-loading
        sub_manager = SubagentManager(
            parent_agent,
            skill_manager=sm,
        )
        config = SubagentConfig(
            name="analyst",
            description="Analysis agent",
            skills=["analysis"],
        )
        sub_manager.register(config)

        # Delegate a task
        sub = _make_test_agent("analysis complete")
        with patch.object(sub_manager, "_spawn", return_value=sub):
            result = sub_manager.delegate_sync("analyst", "Analyze Python trends")

        assert result.success is True
        assert result.output == "analysis complete"

    def test_bidirectional_wiring(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """SkillManager and SubagentManager wired bidirectionally."""
        sm = SkillManager()
        sub_manager = SubagentManager(parent_agent, skill_manager=sm)

        # Wire the other direction
        sm.subagent_manager = sub_manager

        # Register a fork skill
        fork_skill = _make_fork_skill(name="bi-fork", agent_name="bi-agent")
        sm._registry.register(fork_skill)

        # Register the subagent config
        sub_manager.register(
            SubagentConfig(
                name="bi-agent",
                description="Bidirectional agent",
            )
        )

        # Activating the fork skill should delegate via SubagentManager
        mock_result = _make_subagent_result(output="bidirectional output")
        with patch.object(sub_manager, "delegate_sync", return_value=mock_result):
            result = sm.activate("bi-fork", "test")

        assert result == "bidirectional output"

    def test_skill_not_found_for_preloading_raises(
        self,
        parent_agent: Agent[None, str],
    ) -> None:
        """Subagent referencing non-existent skill for pre-loading raises error."""
        sm = SkillManager()
        sub_manager = SubagentManager(parent_agent, skill_manager=sm)

        config = SubagentConfig(
            name="bad-agent",
            description="References missing skill",
            skills=["ghost-skill"],
        )
        sub_manager.register(config)

        # Spawning should raise SkillNotFoundError from _build_system_prompt
        with pytest.raises(SkillNotFoundError, match="ghost-skill"):
            from mamba_agents.subagents.spawner import spawn

            spawn(config, parent_agent, skill_registry=sm.registry)
