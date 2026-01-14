"""System prompt templates for ReAct workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_agent.workflows.react.config import ReActConfig


REACT_SYSTEM_PROMPT_TEMPLATE = """\
You are an AI assistant that solves tasks using the ReAct (Reasoning + Acting) approach.

For each step, follow this process:
1. Think about what you need to do next
2. Take an action by calling a tool
3. Observe the result
4. Repeat until you can provide a final answer

When you have gathered enough information to answer the task, call the {final_answer_tool} tool with your complete answer.

Remember:
- Think step by step
- Use tools to gather information - don't guess
- Verify your assumptions with tools when possible
- Call {final_answer_tool} when you're confident in your answer
"""

FORCE_ACTION_PROMPT = """\
You have been thinking without taking action. Please call a tool now to make progress on the task.
"""

CONTINUE_PROMPT = """\
Continue working on the task. Review the observations above and decide your next step.
"""


def build_react_system_prompt(config: ReActConfig) -> str:
    """Build the ReAct system prompt.

    Args:
        config: ReActConfig with prompt settings.

    Returns:
        Formatted system prompt.
    """
    return REACT_SYSTEM_PROMPT_TEMPLATE.format(
        final_answer_tool=config.final_answer_tool_name,
    )


def build_iteration_prompt(
    config: ReActConfig,
    scratchpad: str,
    force_action: bool = False,
) -> str:
    """Build the prompt for a ReAct iteration.

    Args:
        config: ReActConfig with prompt settings.
        scratchpad: Formatted scratchpad text with previous steps.
        force_action: Whether to add a prompt forcing tool usage.

    Returns:
        Prompt for the next iteration.
    """
    parts: list[str] = []

    # Include scratchpad if configured and non-empty
    if config.include_scratchpad and scratchpad:
        parts.append("Previous steps:")
        parts.append(scratchpad)
        parts.append("")

    # Add force action or continue prompt
    if force_action:
        parts.append(FORCE_ACTION_PROMPT)
    else:
        parts.append(CONTINUE_PROMPT)

    return "\n".join(parts)


def format_tool_call(tool_name: str, args: dict) -> str:
    """Format a tool call for display.

    Args:
        tool_name: Name of the tool.
        args: Tool arguments.

    Returns:
        Formatted string like "tool_name(arg1=val1, arg2=val2)".
    """
    if not args:
        return f"{tool_name}()"

    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    return f"{tool_name}({args_str})"
