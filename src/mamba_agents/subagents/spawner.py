"""Subagent spawning logic.

Creates isolated ``Agent`` instances from ``SubagentConfig`` definitions.
Each subagent gets its own ``ContextManager``, ``UsageTracker``, and other
subsystems, ensuring complete isolation from the parent agent.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from mamba_agents.agent.config import AgentConfig
from mamba_agents.skills.errors import SkillNotFoundError
from mamba_agents.subagents.config import SubagentConfig
from mamba_agents.subagents.errors import SubagentNestingError

if TYPE_CHECKING:
    from mamba_agents.agent.core import Agent
    from mamba_agents.skills.registry import SkillRegistry


def _enforce_no_nesting(parent_agent: Agent[Any, Any]) -> None:
    """Raise if the parent agent is already a subagent.

    Subagents cannot spawn sub-subagents. This prevents unbounded nesting
    depth and resource exhaustion.

    Args:
        parent_agent: The agent attempting to spawn a subagent.

    Raises:
        SubagentNestingError: If the parent agent is itself a subagent.
    """
    if parent_agent.config._is_subagent:
        parent_name = parent_agent.model_name or "unknown"
        raise SubagentNestingError(
            name="<new-subagent>",
            parent_name=parent_name,
        )


def _resolve_tools(
    config: SubagentConfig,
    parent_agent: Agent[Any, Any],
) -> list[Callable[..., Any]]:
    """Resolve tools for the subagent based on the allowlist and disallowed list.

    When ``config.tools`` is ``None``, no tools are inherited (fresh subagent).
    When ``config.tools`` is an empty list, the subagent has no tool access.
    When ``config.tools`` contains entries, only those tools are available.
    Tools in ``config.disallowed_tools`` are removed even if in the allowlist.

    String tool names are resolved against the parent agent's registered tools.
    Callable tools are passed through directly.

    Args:
        config: Subagent configuration with tool allowlist.
        parent_agent: Parent agent whose tools may be referenced.

    Returns:
        List of resolved callable tools for the subagent.
    """
    if config.tools is None:
        return []

    # Build lookup of parent tools by name from pydantic-ai's internal toolset
    parent_tools: dict[str, Callable[..., Any]] = {}
    pydantic_agent = getattr(parent_agent, "_agent", None)
    if pydantic_agent is not None:
        toolset = getattr(pydantic_agent, "_function_toolset", None)
        if toolset is not None:
            for name, tool_def in getattr(toolset, "tools", {}).items():
                if hasattr(tool_def, "function"):
                    parent_tools[name] = tool_def.function

    # Build set of disallowed tool names
    disallowed: set[str] = set(config.disallowed_tools or [])

    resolved: list[Callable[..., Any]] = []
    for tool in config.tools:
        if isinstance(tool, str):
            # Skip disallowed tools
            if tool in disallowed:
                continue
            # Resolve from parent or keep as string for later resolution
            if tool in parent_tools:
                resolved.append(parent_tools[tool])
        else:
            # Callable tool — check if its name is disallowed
            tool_name = getattr(tool, "__name__", None) or ""
            if tool_name in disallowed:
                continue
            resolved.append(tool)

    return resolved


def _build_system_prompt(
    config: SubagentConfig,
    skill_registry: SkillRegistry | None = None,
) -> str:
    """Build the system prompt for a subagent.

    The prompt is assembled from:
    1. The config's ``system_prompt`` field (string or template).
    2. Pre-loaded skill content (if ``config.skills`` is set).

    Args:
        config: Subagent configuration.
        skill_registry: Optional registry for resolving skill names.

    Returns:
        Assembled system prompt string.

    Raises:
        SkillNotFoundError: If a referenced skill is not found in the registry.
    """
    # Start with the base prompt
    base_prompt = config.system_prompt if isinstance(config.system_prompt, str) else ""

    # Pre-load skills into the prompt
    skill_sections: list[str] = []
    if config.skills:
        if skill_registry is None:
            raise SkillNotFoundError(
                name=config.skills[0],
                path="<registry>",
            )

        for skill_name in config.skills:
            skill = skill_registry.get(skill_name)
            if skill is None:
                raise SkillNotFoundError(
                    name=skill_name,
                    path="<registry>",
                )
            if skill.body:
                skill_sections.append(f"## Skill: {skill.info.name}\n\n{skill.body}")

    # Combine base prompt with skill content
    parts = [p for p in [base_prompt, *skill_sections] if p]
    return "\n\n".join(parts)


def _resolve_skill_tools(
    config: SubagentConfig,
    skill_registry: SkillRegistry | None,
) -> list[Callable[..., Any]]:
    """Resolve tools from pre-loaded skills.

    Args:
        config: Subagent configuration with skill names.
        skill_registry: Registry for resolving skill names.

    Returns:
        List of callable tools from the skills.
    """
    if not config.skills or skill_registry is None:
        return []

    tools: list[Callable[..., Any]] = []
    for skill_name in config.skills:
        skill = skill_registry.get(skill_name)
        if skill is not None and hasattr(skill, "_tools") and skill._tools:
            tools.extend(skill._tools)
    return tools


def spawn(
    config: SubagentConfig,
    parent_agent: Agent[Any, Any],
    skill_registry: SkillRegistry | None = None,
) -> Agent[Any, Any]:
    """Spawn an isolated Agent instance from a SubagentConfig.

    Creates a full ``Agent`` with its own context manager, usage tracker,
    and other subsystems. The subagent is marked with ``_is_subagent=True``
    to prevent further nesting.

    Args:
        config: Subagent configuration defining model, tools, and prompt.
        parent_agent: Parent agent providing model fallback and tool resolution.
        skill_registry: Optional skill registry for resolving skill pre-loading.

    Returns:
        A configured ``Agent`` instance ready for task delegation.

    Raises:
        SubagentNestingError: If the parent agent is itself a subagent.
        SkillNotFoundError: If a referenced skill is not found.
    """
    from mamba_agents.agent.core import Agent

    # Enforce no-nesting rule
    _enforce_no_nesting(parent_agent)

    # Determine model: use config model or inherit from parent
    model: str | None = config.model
    if model is None:
        model = parent_agent.model_name

    # Resolve tools from allowlist
    tools = _resolve_tools(config, parent_agent)

    # Resolve skill tools and add to tool list
    skill_tools = _resolve_skill_tools(config, skill_registry)
    if skill_tools:
        tools = tools + skill_tools

    # Build system prompt with skill content
    system_prompt = _build_system_prompt(config, skill_registry)

    # If the config has a TemplateConfig system_prompt and no skills override it,
    # use the TemplateConfig directly
    effective_prompt: str | Any = system_prompt
    if (
        config.system_prompt is not None
        and not isinstance(config.system_prompt, str)
        and not config.skills
    ):
        effective_prompt = config.system_prompt

    # Build agent config
    agent_config = config.config or AgentConfig()
    if isinstance(config.system_prompt, str) or system_prompt:
        agent_config = agent_config.model_copy(
            update={"system_prompt": effective_prompt},
        )

    # Set the subagent flag via private attribute
    agent_config._is_subagent = True

    # Create the subagent Agent instance
    # Model string is passed directly — invalid models surface at delegation time
    subagent: Agent[Any, Any] = Agent(
        model,
        config=agent_config,
        tools=tools if tools else None,
        settings=parent_agent.settings,
    )

    return subagent
