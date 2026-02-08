"""Skill invocation, argument substitution, and activation lifecycle.

Handles the full skill activation lifecycle: permission checks, lazy body
loading, argument substitution, tool registration, and deactivation with
state restoration.
"""

from __future__ import annotations

import re
import shlex
from enum import Enum

from mamba_agents.skills.config import Skill, SkillInfo
from mamba_agents.skills.errors import SkillInvocationError
from mamba_agents.skills.loader import load_full


class InvocationSource(str, Enum):
    """Source of a skill invocation request.

    Attributes:
        MODEL: Invoked by the LLM model during conversation.
        USER: Invoked directly by the user (e.g., slash command).
        CODE: Invoked programmatically from application code.
    """

    MODEL = "model"
    USER = "user"
    CODE = "code"


# Pattern for $ARGUMENTS[N] syntax — e.g., $ARGUMENTS[0], $ARGUMENTS[12]
_ARGUMENTS_INDEX_PATTERN = re.compile(r"\$ARGUMENTS\[(\d+)\]")

# Pattern for $N positional syntax — e.g., $0, $1, $12
# Uses word boundary to avoid matching things like $100 inside other text
_POSITIONAL_PATTERN = re.compile(r"\$(\d+)(?=\s|$|[^0-9\[])")


def check_invocation_permission(
    skill: SkillInfo,
    source: InvocationSource,
) -> bool:
    """Check whether a skill can be invoked from the given source.

    Invocation control via frontmatter flags:
    - ``disable_model_invocation=True``: only user/code can invoke
    - ``user_invocable=False``: only model/code can invoke
    - Default (both False/True respectively): all sources can invoke
    - ``CODE`` source is always permitted

    Args:
        skill: Skill metadata containing invocation flags.
        source: The source requesting invocation.

    Returns:
        ``True`` if the invocation is permitted, ``False`` otherwise.
    """
    # Code invocations are always allowed
    if source == InvocationSource.CODE:
        return True

    # Model invocations blocked when disable_model_invocation is True
    if source == InvocationSource.MODEL and skill.disable_model_invocation:
        return False

    # User invocations blocked when user_invocable is False
    return not (source == InvocationSource.USER and not skill.user_invocable)


def parse_arguments(raw: str) -> list[str]:
    """Parse a raw argument string into individual arguments.

    Splits on whitespace while preserving quoted strings. Both single
    and double quotes are supported. Empty input returns an empty list.

    Args:
        raw: Raw argument string (e.g., ``'file.txt "hello world" --flag'``).

    Returns:
        List of parsed argument strings.

    Examples:
        >>> parse_arguments('hello world')
        ['hello', 'world']
        >>> parse_arguments('"hello world" foo')
        ['hello world', 'foo']
        >>> parse_arguments('')
        []
    """
    if not raw or not raw.strip():
        return []

    try:
        return shlex.split(raw)
    except ValueError:
        # Fallback for malformed quotes: simple whitespace split
        return raw.split()


def substitute_arguments(content: str, arguments: str) -> str:
    """Perform argument substitution on skill content.

    Substitution rules (applied in order):
    1. ``$ARGUMENTS`` is replaced with the full argument string (all occurrences).
    2. ``$ARGUMENTS[N]`` is replaced with positional argument N (0-indexed).
    3. ``$N`` is replaced with positional argument N (0-indexed).
    4. If none of ``$ARGUMENTS``, ``$ARGUMENTS[N]``, or ``$N`` appear in the
       content, the arguments are appended as ``ARGUMENTS: <value>``.

    Missing positional arguments resolve to empty strings.

    Args:
        content: Skill body content with placeholders.
        arguments: Raw argument string to substitute.

    Returns:
        Content with all argument placeholders replaced.
    """
    parsed = parse_arguments(arguments)

    # Track whether any substitution placeholder was found
    has_full_placeholder = "$ARGUMENTS" in content
    has_indexed_placeholder = bool(_ARGUMENTS_INDEX_PATTERN.search(content))
    has_positional_placeholder = bool(_POSITIONAL_PATTERN.search(content))

    has_any_placeholder = (
        has_full_placeholder or has_indexed_placeholder or has_positional_placeholder
    )

    # Step 1: Replace $ARGUMENTS[N] first (before $ARGUMENTS, to avoid partial match)
    def _replace_indexed(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        if idx < len(parsed):
            return parsed[idx]
        return ""

    result = _ARGUMENTS_INDEX_PATTERN.sub(_replace_indexed, content)

    # Step 2: Replace $ARGUMENTS with full argument string
    # After indexed replacements, any remaining $ARGUMENTS are the bare form
    result = result.replace("$ARGUMENTS", arguments)

    # Step 3: Replace $N positional placeholders
    def _replace_positional(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        if idx < len(parsed):
            return parsed[idx]
        return ""

    result = _POSITIONAL_PATTERN.sub(_replace_positional, result)

    # Step 4: If no placeholders found, append arguments
    if not has_any_placeholder and arguments.strip():
        result = result.rstrip("\n") + "\n\nARGUMENTS: " + arguments + "\n"

    return result


def activate(
    skill: Skill,
    arguments: str = "",
    *,
    source: InvocationSource = InvocationSource.CODE,
) -> str:
    """Activate a skill: check permissions, load body, substitute arguments.

    Full activation lifecycle:
    1. Check invocation permissions against the source.
    2. Load the full SKILL.md body if not already loaded.
    3. Perform argument substitution on the body.
    4. Mark the skill as active and store its allowed tools.
    5. Return the processed skill content.

    Args:
        skill: The skill to activate.
        arguments: Raw argument string to pass to the skill.
        source: The invocation source (model, user, or code).

    Returns:
        Processed skill content with arguments substituted.

    Raises:
        SkillInvocationError: If the source lacks permission to invoke.
    """
    # Step 1: Check permissions
    if not check_invocation_permission(skill.info, source):
        if source == InvocationSource.MODEL:
            reason = "model invocation is disabled for this skill"
        elif source == InvocationSource.USER:
            reason = "user invocation is disabled for this skill"
        else:
            reason = "invocation denied"

        raise SkillInvocationError(
            name=skill.info.name,
            source=source.value,
            reason=reason,
        )

    # Step 2: Lazy-load body if not present
    if skill.body is None and skill.info.path is not None:
        skill_file = skill.info.path / "SKILL.md"
        if skill_file.exists():
            loaded = load_full(skill_file, scope=skill.info.scope)
            skill.body = loaded.body

    # Use body content (may still be None if no file exists)
    body = skill.body or ""

    # Step 3: Perform argument substitution
    processed = substitute_arguments(body, arguments)

    # Step 4: Mark as active and store previous tool state
    skill.is_active = True

    # Step 5: Return processed content
    return processed


def deactivate(skill: Skill) -> None:
    """Deactivate a skill and restore previous state.

    Marks the skill as inactive and clears any runtime tool registrations.

    Args:
        skill: The skill to deactivate.
    """
    skill.is_active = False
    # Clear registered tools — the caller (SkillManager) is responsible
    # for restoring the agent's previous tool state from its own snapshot.
    skill._tools = []
