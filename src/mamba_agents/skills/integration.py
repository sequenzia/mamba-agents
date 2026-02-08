"""Bi-directional integration between the skills and subagents subsystems.

Handles the wiring between skills and subagents:
- Skill activation with ``execution_mode: "fork"`` delegates to a subagent.
- Circular reference detection between skills and subagent configs.
- Trust level enforcement for fork-mode skills.

Uses lazy imports and ``TYPE_CHECKING`` guards to avoid circular dependencies
between the ``skills`` and ``subagents`` packages.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from mamba_agents.skills.config import Skill, TrustLevel
from mamba_agents.skills.errors import SkillInvocationError

if TYPE_CHECKING:
    from mamba_agents.subagents.manager import SubagentManager

logger = logging.getLogger(__name__)


def detect_circular_skill_subagent(
    skill: Skill,
    subagent_configs: dict[str, Any],
    get_skill_fn: Any = None,
) -> list[str] | None:
    """Detect circular references starting from a skill with fork execution mode.

    Follows the chain: skill (fork) -> agent config -> pre-loaded skills ->
    (check if any pre-loaded skill forks back to an agent that pre-loads
    the original skill).

    Args:
        skill: The skill being activated (must have ``execution_mode="fork"``).
        subagent_configs: Dictionary of subagent config name -> SubagentConfig.
        get_skill_fn: Callable that takes a skill name and returns a Skill or
            None. Used to look up pre-loaded skills' metadata.

    Returns:
        A list representing the circular path if detected, or ``None`` if
        no cycle exists.
    """
    if skill.info.execution_mode != "fork":
        return None

    agent_name = skill.info.agent
    if agent_name is None:
        return None  # Temporary agents don't have pre-loaded skills

    return _trace_cycle(
        start_skill=skill.info.name,
        agent_name=agent_name,
        subagent_configs=subagent_configs,
        get_skill_fn=get_skill_fn,
        visited=set(),
        path=[],
    )


def _trace_cycle(
    start_skill: str,
    agent_name: str,
    subagent_configs: dict[str, Any],
    get_skill_fn: Any,
    visited: set[str],
    path: list[str],
) -> list[str] | None:
    """Trace the skill -> agent -> skill chain looking for cycles.

    Args:
        start_skill: The original skill name we are checking for.
        agent_name: The subagent config name to check.
        subagent_configs: All registered subagent configs.
        get_skill_fn: Function to look up a Skill by name.
        visited: Set of visited agent config names.
        path: Current reference path being traced.

    Returns:
        Circular path list or None.
    """
    skill_node = f"skill:{start_skill}"
    agent_node = f"agent:{agent_name}"

    path.append(skill_node)
    path.append(agent_node)

    if agent_name in visited:
        return list(path)

    visited.add(agent_name)

    config = subagent_configs.get(agent_name)
    if config is None:
        return None

    # Check pre-loaded skills of this agent config
    pre_loaded_skills = getattr(config, "skills", None) or []

    for preloaded_name in pre_loaded_skills:
        # Direct cycle: the pre-loaded skill is the original skill
        if preloaded_name == start_skill:
            path.append(f"skill:{preloaded_name}")
            return list(path)

        # Indirect cycle: the pre-loaded skill also forks to an agent
        if get_skill_fn is not None:
            preloaded_skill = get_skill_fn(preloaded_name)
            if preloaded_skill is not None:
                preloaded_info = preloaded_skill.info
                if (
                    getattr(preloaded_info, "execution_mode", None) == "fork"
                    and getattr(preloaded_info, "agent", None) is not None
                ):
                    sub_result = _trace_cycle(
                        start_skill=start_skill,
                        agent_name=preloaded_info.agent,
                        subagent_configs=subagent_configs,
                        get_skill_fn=get_skill_fn,
                        visited=visited,
                        path=list(path),  # copy to avoid mutation
                    )
                    if sub_result is not None:
                        return sub_result

    return None


def activate_with_fork(
    skill: Skill,
    arguments: str,
    subagent_manager: SubagentManager,
) -> str:
    """Activate a fork-mode skill by delegating to a subagent.

    When a skill has ``execution_mode: "fork"``, instead of returning the
    skill body directly, this function:
    1. Checks trust level (untrusted skills cannot fork).
    2. Detects circular references.
    3. Resolves or creates a subagent config.
    4. Delegates the skill content as the task prompt to the subagent.
    5. Returns the subagent's output.

    Args:
        skill: The skill to activate (must have ``execution_mode="fork"``).
        arguments: Raw argument string for the skill.
        subagent_manager: The SubagentManager to delegate through.

    Returns:
        The subagent's output text.

    Raises:
        SkillInvocationError: If the skill is untrusted, has circular
            references, or delegation fails.
    """
    from mamba_agents.skills.invocation import activate
    from mamba_agents.subagents.config import SubagentConfig
    from mamba_agents.subagents.errors import SubagentNotFoundError

    # Step 1: Trust level check — untrusted skills cannot fork
    if skill.info.trust_level == TrustLevel.UNTRUSTED:
        raise SkillInvocationError(
            name=skill.info.name,
            source="code",
            reason="Untrusted skill cannot use 'context: fork' to spawn subagents",
        )

    # Step 2: Detect circular references
    cycle = detect_circular_skill_subagent(
        skill,
        {c.name: c for c in subagent_manager.list()},
        get_skill_fn=(
            subagent_manager._skill_manager.get
            if subagent_manager._skill_manager is not None
            else None
        ),
    )
    if cycle is not None:
        cycle_str = " -> ".join(cycle)
        raise SkillInvocationError(
            name=skill.info.name,
            source="code",
            reason=f"Circular skill-subagent reference detected: {cycle_str}",
        )

    # Step 3: Prepare the skill content as the task prompt
    # First activate the skill normally to get processed content
    content = activate(skill, arguments)

    # Step 4: Resolve subagent config
    agent_name = skill.info.agent

    if agent_name is not None:
        # Named subagent config — must exist
        config = subagent_manager.get(agent_name)
        if config is None:
            raise SubagentNotFoundError(
                config_name=agent_name,
                available=[c.name for c in subagent_manager.list()],
            )
        # Delegate via the named config
        result = subagent_manager.delegate_sync(agent_name, content)
    else:
        # No agent field — create a temporary general-purpose subagent
        temp_config = SubagentConfig(
            name=f"_skill_fork_{skill.info.name}",
            description=f"Temporary subagent for skill '{skill.info.name}'",
        )
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # We're in an async context — use nest_asyncio or run_until_complete
            # on a new thread. For simplicity, use delegate_sync which handles this.
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    subagent_manager.spawn_dynamic(temp_config, content),
                )
                result = future.result()
        else:
            result = asyncio.run(
                subagent_manager.spawn_dynamic(temp_config, content),
            )

    if not result.success:
        raise SkillInvocationError(
            name=skill.info.name,
            source="code",
            reason=f"Subagent delegation failed: {result.error}",
        )

    return result.output
