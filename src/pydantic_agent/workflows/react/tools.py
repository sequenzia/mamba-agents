"""Tool factories for ReAct workflow."""

from __future__ import annotations

from collections.abc import Callable


def create_final_answer_tool() -> Callable[[str], str]:
    """Create the final_answer tool for workflow termination.

    This tool signals that the agent has completed its task and is
    ready to provide the final answer. The workflow detects this
    tool call and terminates.

    Returns:
        Tool function that can be registered with agent.tool_plain().

    Example:
        >>> agent.tool_plain(
        ...     create_final_answer_tool(),
        ...     name="final_answer",
        ... )
    """

    def final_answer(answer: str) -> str:
        """Submit the final answer to complete the task.

        Call this tool when you have gathered enough information
        and are ready to provide the final answer to the user's task.

        Args:
            answer: The complete final answer to the user's task.

        Returns:
            Confirmation message.
        """
        # Truncate for display if very long
        preview = answer[:100] + "..." if len(answer) > 100 else answer
        return f"Final answer submitted: {preview}"

    return final_answer
