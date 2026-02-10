"""Tests for invoke_skill pydantic-ai tool registration and behavior.

Verifies that when init_skills() is called and skills exist, a pydantic-ai
tool named ``invoke_skill`` is registered on the underlying agent, allowing
the model to dynamically invoke skills during agent.run().
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from pydantic_ai.models.test import TestModel

from mamba_agents import Agent
from mamba_agents.skills.config import (
    Skill,
    SkillInfo,
    SkillScope,
    TrustLevel,
)
from mamba_agents.skills.invocation import InvocationSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_SKILL_MD = """\
---
name: {name}
description: {description}
---

# {name}

Skill body with $ARGUMENTS placeholder.
"""


def _make_info(
    name: str = "test-skill",
    description: str = "A test skill",
    path: Path | None = None,
    scope: SkillScope = SkillScope.PROJECT,
    trust_level: TrustLevel = TrustLevel.TRUSTED,
    disable_model_invocation: bool = False,
    execution_mode: str | None = None,
    agent: str | None = None,
) -> SkillInfo:
    """Create a minimal SkillInfo for testing."""
    return SkillInfo(
        name=name,
        description=description,
        path=path or Path(f"/skills/{name}"),
        scope=scope,
        trust_level=trust_level,
        disable_model_invocation=disable_model_invocation,
        execution_mode=execution_mode,
        agent=agent,
    )


def _make_skill(
    name: str = "test-skill",
    description: str = "A test skill",
    path: Path | None = None,
    body: str | None = "Skill body with $ARGUMENTS placeholder.",
    is_active: bool = False,
    disable_model_invocation: bool = False,
    execution_mode: str | None = None,
    agent: str | None = None,
) -> Skill:
    """Create a minimal Skill for testing."""
    return Skill(
        info=_make_info(
            name=name,
            description=description,
            path=path,
            disable_model_invocation=disable_model_invocation,
            execution_mode=execution_mode,
            agent=agent,
        ),
        body=body,
        is_active=is_active,
    )


def _make_skill_dir(
    base_dir: Path,
    name: str,
    description: str = "A test skill",
    body: str | None = None,
    disable_model_invocation: bool = False,
) -> Path:
    """Create a skill directory with a valid SKILL.md file."""
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = f"---\nname: {name}\ndescription: {description}\n"
    if disable_model_invocation:
        frontmatter += "disable-model-invocation: true\n"
    frontmatter += "---\n\n"
    content = frontmatter + (body or f"# {name}\n\nSkill body with $ARGUMENTS placeholder.\n")
    (skill_dir / "SKILL.md").write_text(content)
    return skill_dir


def _get_tool_names(agent: Agent) -> set[str]:
    """Helper to get the set of tool names from the underlying pydantic-ai agent."""
    return set(agent._agent._function_toolset.tools.keys())


# ---------------------------------------------------------------------------
# Tests: Tool Registration
# ---------------------------------------------------------------------------


class TestInvokeSkillToolRegistration:
    """Tests for invoke_skill tool registration in init_skills()."""

    def test_tool_registered_when_skills_exist(self, test_model: TestModel) -> None:
        """invoke_skill tool is registered when init_skills() is called with skills."""
        skill = _make_skill(name="my-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        assert "invoke_skill" in _get_tool_names(agent)

    def test_tool_not_registered_when_no_skills(self, test_model: TestModel) -> None:
        """invoke_skill tool is NOT registered when init_skills() has no skills."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_skills()

        assert "invoke_skill" not in _get_tool_names(agent)

    def test_tool_not_registered_with_empty_skills_list(self, test_model: TestModel) -> None:
        """invoke_skill tool is NOT registered with empty skills list."""
        agent: Agent[None, str] = Agent(test_model, skills=[])

        assert "invoke_skill" not in _get_tool_names(agent)

    def test_tool_registered_with_skill_dirs(self, test_model: TestModel, tmp_path: Path) -> None:
        """invoke_skill tool is registered when skills are discovered from dirs."""
        scan_dir = tmp_path / "skills"
        scan_dir.mkdir()
        _make_skill_dir(scan_dir, "dir-skill")

        agent: Agent[None, str] = Agent(test_model, skill_dirs=[scan_dir])

        assert "invoke_skill" in _get_tool_names(agent)

    def test_tool_registered_with_multiple_skills(self, test_model: TestModel) -> None:
        """invoke_skill tool is registered with multiple skills."""
        skill1 = _make_skill(name="skill-one", description="First skill")
        skill2 = _make_skill(name="skill-two", description="Second skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill1, skill2])

        assert "invoke_skill" in _get_tool_names(agent)

    def test_tool_not_present_without_init(self, test_model: TestModel) -> None:
        """Agent without any skill init has no invoke_skill tool."""
        agent: Agent[None, str] = Agent(test_model)

        assert "invoke_skill" not in _get_tool_names(agent)


# ---------------------------------------------------------------------------
# Tests: Tool Description
# ---------------------------------------------------------------------------


class TestInvokeSkillToolDescription:
    """Tests for invoke_skill tool description content."""

    def test_description_includes_skill_names(self, test_model: TestModel) -> None:
        """Tool description lists available skill names."""
        skill1 = _make_skill(name="code-review", description="Reviews code quality")
        skill2 = _make_skill(name="summarize", description="Summarizes text")
        agent: Agent[None, str] = Agent(test_model, skills=[skill1, skill2])

        tool = agent._agent._function_toolset.tools["invoke_skill"]
        desc = tool.description
        assert "code-review" in desc
        assert "Reviews code quality" in desc
        assert "summarize" in desc
        assert "Summarizes text" in desc

    def test_description_excludes_disabled_skills(self, test_model: TestModel) -> None:
        """Skills with disable_model_invocation=True are excluded from description."""
        visible = _make_skill(name="visible", description="Visible skill")
        hidden = _make_skill(
            name="hidden",
            description="Hidden skill",
            disable_model_invocation=True,
        )
        agent: Agent[None, str] = Agent(test_model, skills=[visible, hidden])

        tool = agent._agent._function_toolset.tools["invoke_skill"]
        desc = tool.description
        assert "visible" in desc
        assert "Visible skill" in desc
        assert "hidden" not in desc.lower().split("invoke")[0]  # not in skill list part


# ---------------------------------------------------------------------------
# Tests: Model Invocation Permission
# ---------------------------------------------------------------------------


class TestInvokeSkillPermissions:
    """Tests for invoke_skill permission checks."""

    def test_disable_model_invocation_returns_error(self, test_model: TestModel) -> None:
        """Skill with disable_model_invocation returns error when model calls it."""
        hidden = _make_skill(
            name="hidden-skill",
            description="Hidden skill",
            disable_model_invocation=True,
        )
        visible = _make_skill(name="visible-skill", description="Visible skill")
        agent: Agent[None, str] = Agent(test_model, skills=[visible, hidden])

        # Directly call the tool function to check behavior
        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="hidden-skill", arguments=""))
        assert "Error" in result
        assert "model invocation disabled" in result

    def test_invocation_source_model_used(self, test_model: TestModel) -> None:
        """InvocationSource.MODEL is used when model invokes skill via tool."""
        skill = _make_skill(name="test-skill", description="Test")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        with patch("mamba_agents.skills.invocation.activate") as mock_activate:
            mock_activate.return_value = "activated content"

            tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
            tool_func = tool_obj.function

            import asyncio

            asyncio.run(tool_func(name="test-skill", arguments="hello"))

            mock_activate.assert_called_once()
            call_args = mock_activate.call_args
            assert call_args.kwargs.get("source") == InvocationSource.MODEL

    def test_user_invocable_false_does_not_block_model(self, test_model: TestModel) -> None:
        """user_invocable=False does NOT block model invocation (only blocks USER)."""
        info = _make_info(
            name="user-blocked",
            description="Blocks users only",
        )
        # user_invocable defaults to True; set to False for this test
        info.user_invocable = False
        skill = Skill(
            info=info,
            body="User-blocked skill body with $ARGUMENTS placeholder.",
        )
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="user-blocked", arguments=""))
        # Should succeed (not error) because MODEL is allowed even with user_invocable=False
        assert "Error" not in result
        assert "User-blocked skill body" in result


# ---------------------------------------------------------------------------
# Tests: Error Handling
# ---------------------------------------------------------------------------


class TestInvokeSkillErrorHandling:
    """Tests for invoke_skill error handling — returns error strings, never raises."""

    def test_unknown_skill_returns_error_message(self, test_model: TestModel) -> None:
        """Unknown skill name returns error message, not exception."""
        skill = _make_skill(name="real-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="nonexistent", arguments=""))
        assert "Error" in result
        assert "nonexistent" in result
        assert "not found" in result

    def test_error_message_lists_available_skills(self, test_model: TestModel) -> None:
        """Error message for unknown skill lists available skills."""
        skill = _make_skill(name="available-skill", description="Available")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="missing", arguments=""))
        assert "available-skill" in result

    def test_never_raises_exceptions(self, test_model: TestModel) -> None:
        """Tool never raises exceptions — always returns error strings."""
        skill = _make_skill(name="error-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        # Force an exception by patching activate to raise
        with patch(
            "mamba_agents.skills.invocation.activate",
            side_effect=RuntimeError("Something went wrong"),
        ):
            tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
            tool_func = tool_obj.function

            import asyncio

            result = asyncio.run(tool_func(name="error-skill", arguments=""))
            assert "Error" in result
            assert "RuntimeError" in result
            assert "Something went wrong" in result

    def test_fork_mode_without_subagent_manager_returns_error(self, test_model: TestModel) -> None:
        """Fork-mode skill without SubagentManager returns error."""
        skill = _make_skill(
            name="fork-skill",
            description="Fork skill",
            execution_mode="fork",
        )
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="fork-skill", arguments=""))
        assert "Error" in result
        assert "fork" in result.lower()


# ---------------------------------------------------------------------------
# Tests: Edge Cases
# ---------------------------------------------------------------------------


class TestInvokeSkillEdgeCases:
    """Tests for invoke_skill edge cases."""

    def test_skill_registered_after_init_available_on_next_call(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Skill registered after init_skills() is available on next invoke_skill call."""
        initial = _make_skill(name="initial-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[initial])

        # Register a new skill after init
        new_dir = _make_skill_dir(tmp_path, "later-skill", description="Added later")
        agent.register_skill(new_dir)

        # The tool should be able to invoke the new skill
        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="later-skill", arguments=""))
        # Should succeed because the tool queries the live registry
        assert "Error" not in result

    def test_arguments_passed_to_skill(self, test_model: TestModel) -> None:
        """Arguments are passed through to skill activation."""
        skill = _make_skill(
            name="arg-skill",
            body="Process: $ARGUMENTS",
        )
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="arg-skill", arguments="hello world"))
        assert "hello world" in result

    def test_empty_arguments_default(self, test_model: TestModel) -> None:
        """Empty arguments string works correctly."""
        skill = _make_skill(
            name="no-arg-skill",
            body="No args needed.",
        )
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        tool_func = tool_obj.function

        import asyncio

        result = asyncio.run(tool_func(name="no-arg-skill", arguments=""))
        assert "No args needed" in result


# ---------------------------------------------------------------------------
# Tests: Integration — Model invokes skill during agent.run()
# ---------------------------------------------------------------------------


class TestInvokeSkillIntegration:
    """Integration tests for model invoking skills via invoke_skill tool."""

    async def test_model_invokes_skill_during_run(self, tmp_path: Path) -> None:
        """Model invokes the invoke_skill tool during agent.run() via TestModel."""
        # TestModel with call_tools='all' (default) calls all registered tools
        model = TestModel()
        skill_dir = _make_skill_dir(
            tmp_path, "greet", description="Greets the user", body="Hello, $ARGUMENTS!"
        )

        agent: Agent[None, str] = Agent(model, skills=[skill_dir])

        # Run the agent — TestModel will call invoke_skill automatically
        result = await agent.run("Say hello to Bob")

        # The model should have called the invoke_skill tool
        # Result should complete without error
        assert result.output is not None

    async def test_model_run_with_multiple_skills(self, tmp_path: Path) -> None:
        """Model can run when multiple skills are registered."""
        model = TestModel()
        _make_skill_dir(tmp_path, "skill-a", description="Skill A")
        _make_skill_dir(tmp_path, "skill-b", description="Skill B")

        agent: Agent[None, str] = Agent(
            model,
            skill_dirs=[tmp_path],
        )

        result = await agent.run("Do something")
        assert result.output is not None

    async def test_fork_mode_skill_via_invoke_skill_tool(self, test_model: TestModel) -> None:
        """Fork-mode skill invoked via invoke_skill tool delegates to subagent."""
        fork_skill = _make_skill(
            name="fork-skill",
            description="A fork skill",
            execution_mode="fork",
            body="Fork task content.",
        )
        agent: Agent[None, str] = Agent(test_model, skills=[fork_skill])
        agent.init_subagents()

        # Mock the activate_with_fork to return a result
        with patch(
            "mamba_agents.skills.integration.activate_with_fork",
            new_callable=AsyncMock,
            return_value="Fork result from subagent",
        ):
            tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
            tool_func = tool_obj.function

            result = await tool_func(name="fork-skill", arguments="test args")
            assert result == "Fork result from subagent"


# ---------------------------------------------------------------------------
# Tests: Tool Parameters
# ---------------------------------------------------------------------------


class TestInvokeSkillToolParameters:
    """Tests for invoke_skill tool parameter structure."""

    def test_tool_accepts_name_parameter(self, test_model: TestModel) -> None:
        """invoke_skill tool accepts 'name' parameter."""
        skill = _make_skill(name="param-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        params = tool_obj.function_schema.json_schema
        assert "name" in params.get("properties", {})

    def test_tool_accepts_arguments_parameter(self, test_model: TestModel) -> None:
        """invoke_skill tool accepts 'arguments' parameter."""
        skill = _make_skill(name="param-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        params = tool_obj.function_schema.json_schema
        assert "arguments" in params.get("properties", {})

    def test_arguments_parameter_has_default(self, test_model: TestModel) -> None:
        """'arguments' parameter has a default value (empty string)."""
        skill = _make_skill(name="param-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        tool_obj = agent._agent._function_toolset.tools["invoke_skill"]
        params = tool_obj.function_schema.json_schema
        # 'arguments' should not be in 'required' since it has a default
        required = params.get("required", [])
        assert "arguments" not in required


# ---------------------------------------------------------------------------
# Tests: Dynamic Description Updates
# ---------------------------------------------------------------------------


class TestInvokeSkillDynamicDescription:
    """Tests for invoke_skill tool description updates on register/deregister."""

    def test_description_updated_after_register_skill(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Tool description includes newly registered skill after register_skill()."""
        initial = _make_skill(name="initial-skill", description="Initial skill")
        agent: Agent[None, str] = Agent(test_model, skills=[initial])

        # Description should only mention initial-skill
        tool = agent._agent._function_toolset.tools["invoke_skill"]
        assert "initial-skill" in tool.description
        assert "new-skill" not in tool.description

        # Register a new skill
        new_dir = _make_skill_dir(tmp_path, "new-skill", description="Newly added")
        agent.register_skill(new_dir)

        # Description should now include both skills
        tool = agent._agent._function_toolset.tools["invoke_skill"]
        assert "initial-skill" in tool.description
        assert "new-skill" in tool.description
        assert "Newly added" in tool.description

    def test_description_updated_after_deregister_skill(
        self, test_model: TestModel
    ) -> None:
        """Tool description excludes deregistered skill after deregister_skill()."""
        skill1 = _make_skill(name="keep-skill", description="Keeper")
        skill2 = _make_skill(name="remove-skill", description="To be removed")
        agent: Agent[None, str] = Agent(test_model, skills=[skill1, skill2])

        # Both should be in description initially
        tool = agent._agent._function_toolset.tools["invoke_skill"]
        assert "keep-skill" in tool.description
        assert "remove-skill" in tool.description

        # Deregister one skill
        agent.deregister_skill("remove-skill")

        # Description should only include the remaining skill
        tool = agent._agent._function_toolset.tools["invoke_skill"]
        assert "keep-skill" in tool.description
        assert "remove-skill" not in tool.description

    def test_tool_removed_when_all_skills_deregistered(
        self, test_model: TestModel
    ) -> None:
        """invoke_skill tool is removed when all skills are deregistered."""
        skill = _make_skill(name="only-skill", description="The only one")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        assert "invoke_skill" in _get_tool_names(agent)

        agent.deregister_skill("only-skill")

        assert "invoke_skill" not in _get_tool_names(agent)

    def test_description_reflects_final_state_after_rapid_changes(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Description reflects final state after rapid register/deregister cycles."""
        skill_a = _make_skill(name="skill-a", description="Skill A")
        agent: Agent[None, str] = Agent(test_model, skills=[skill_a])

        # Register skill-b
        dir_b = _make_skill_dir(tmp_path, "skill-b", description="Skill B")
        agent.register_skill(dir_b)

        # Deregister skill-a
        agent.deregister_skill("skill-a")

        # Register skill-c
        dir_c = _make_skill_dir(tmp_path, "skill-c", description="Skill C")
        agent.register_skill(dir_c)

        # Final state: skill-b and skill-c
        tool = agent._agent._function_toolset.tools["invoke_skill"]
        assert "skill-a" not in tool.description
        assert "skill-b" in tool.description
        assert "Skill B" in tool.description
        assert "skill-c" in tool.description
        assert "Skill C" in tool.description

    def test_tool_re_created_after_all_removed_then_new_registered(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """Tool is re-created when skills are registered after all were removed."""
        skill = _make_skill(name="temp-skill", description="Temporary")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        # Remove all skills
        agent.deregister_skill("temp-skill")
        assert "invoke_skill" not in _get_tool_names(agent)

        # Register a new skill
        new_dir = _make_skill_dir(tmp_path, "fresh-skill", description="Brand new")
        agent.register_skill(new_dir)

        # Tool should be back
        assert "invoke_skill" in _get_tool_names(agent)
        tool = agent._agent._function_toolset.tools["invoke_skill"]
        assert "fresh-skill" in tool.description
        assert "Brand new" in tool.description

    def test_register_skill_on_empty_init_creates_tool(
        self, test_model: TestModel, tmp_path: Path
    ) -> None:
        """register_skill() creates invoke_skill tool when init_skills() had no skills."""
        agent: Agent[None, str] = Agent(test_model)
        agent.init_skills()

        # No tool initially (no skills)
        assert "invoke_skill" not in _get_tool_names(agent)

        # Register a skill
        skill_dir = _make_skill_dir(tmp_path, "late-skill", description="Late arrival")
        agent.register_skill(skill_dir)

        # Tool should now exist
        assert "invoke_skill" in _get_tool_names(agent)
        tool = agent._agent._function_toolset.tools["invoke_skill"]
        assert "late-skill" in tool.description

    def test_deregister_nonexistent_skill_raises(self, test_model: TestModel) -> None:
        """deregister_skill() raises SkillNotFoundError for unknown skills."""
        from mamba_agents.skills.errors import SkillNotFoundError

        skill = _make_skill(name="real-skill")
        agent: Agent[None, str] = Agent(test_model, skills=[skill])

        import pytest

        with pytest.raises(SkillNotFoundError):
            agent.deregister_skill("nonexistent")
