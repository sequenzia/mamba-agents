"""Termination detection utilities for ReAct workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_agent.agent.result import AgentResult


def detect_final_answer(
    result: AgentResult[Any],
    tool_name: str = "final_answer",
) -> tuple[bool, str | None]:
    """Detect if the final_answer tool was called.

    Inspects the agent result's new messages for a ToolCallPart
    with the specified tool name.

    Args:
        result: AgentResult from agent.run().
        tool_name: Name of the termination tool to detect.

    Returns:
        Tuple of (is_terminated, answer_content).
        If final_answer was called, returns (True, answer_string).
        Otherwise returns (False, None).
    """
    for msg in result.new_messages():
        msg_type = type(msg).__name__

        if msg_type == "ModelResponse":
            parts = getattr(msg, "parts", [])
            for part in parts:
                part_type = type(part).__name__

                if part_type == "ToolCallPart":
                    part_tool_name = getattr(part, "tool_name", "")
                    if part_tool_name == tool_name:
                        args = getattr(part, "args", {})
                        # Extract answer from args
                        if isinstance(args, dict):
                            answer = args.get("answer", str(args))
                        else:
                            answer = str(args)
                        return True, answer

    return False, None


def extract_tool_calls(result: AgentResult[Any]) -> list[dict[str, Any]]:
    """Extract all tool calls from an agent result.

    Args:
        result: AgentResult from agent.run().

    Returns:
        List of dicts with 'name', 'args', and 'id' keys.
    """
    calls: list[dict[str, Any]] = []

    for msg in result.new_messages():
        msg_type = type(msg).__name__

        if msg_type == "ModelResponse":
            parts = getattr(msg, "parts", [])
            for part in parts:
                part_type = type(part).__name__

                if part_type == "ToolCallPart":
                    calls.append(
                        {
                            "name": getattr(part, "tool_name", ""),
                            "args": getattr(part, "args", {}),
                            "id": getattr(part, "tool_call_id", ""),
                        }
                    )

    return calls


def extract_tool_results(result: AgentResult[Any]) -> list[dict[str, Any]]:
    """Extract tool return results from an agent result.

    Args:
        result: AgentResult from agent.run().

    Returns:
        List of dicts with 'name', 'content', and 'tool_call_id' keys.
    """
    results: list[dict[str, Any]] = []

    for msg in result.new_messages():
        msg_type = type(msg).__name__

        if msg_type == "ModelRequest":
            parts = getattr(msg, "parts", [])
            for part in parts:
                part_type = type(part).__name__

                if part_type == "ToolReturnPart":
                    results.append(
                        {
                            "name": getattr(part, "tool_name", ""),
                            "content": str(getattr(part, "content", "")),
                            "tool_call_id": getattr(part, "tool_call_id", ""),
                        }
                    )

    return results


def extract_text_content(result: AgentResult[Any]) -> str:
    """Extract text content from model response.

    Args:
        result: AgentResult from agent.run().

    Returns:
        Concatenated text content from all TextParts.
    """
    text_parts: list[str] = []

    for msg in result.new_messages():
        msg_type = type(msg).__name__

        if msg_type == "ModelResponse":
            parts = getattr(msg, "parts", [])
            for part in parts:
                part_type = type(part).__name__

                if part_type == "TextPart":
                    content = getattr(part, "content", "")
                    if content:
                        text_parts.append(content)

    return "\n".join(text_parts)
