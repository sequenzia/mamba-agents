"""Message format conversion utilities.

Converts between pydantic-ai ModelMessage format and dict format for ContextManager.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage


def model_messages_to_dicts(messages: list[ModelMessage]) -> list[dict[str, Any]]:
    """Convert pydantic-ai ModelMessage objects to dict format.

    Args:
        messages: List of ModelRequest/ModelResponse objects from pydantic-ai.

    Returns:
        List of message dictionaries with role and content, compatible with ContextManager.
    """
    result: list[dict[str, Any]] = []

    for msg in messages:
        msg_type = type(msg).__name__

        if msg_type == "ModelRequest":
            # ModelRequest contains user prompts, system prompts, and tool returns
            for part in getattr(msg, "parts", []):
                part_type = type(part).__name__

                if part_type == "SystemPromptPart":
                    result.append(
                        {
                            "role": "system",
                            "content": getattr(part, "content", ""),
                        }
                    )
                elif part_type == "UserPromptPart":
                    result.append(
                        {
                            "role": "user",
                            "content": getattr(part, "content", ""),
                        }
                    )
                elif part_type == "ToolReturnPart":
                    result.append(
                        {
                            "role": "tool",
                            "tool_call_id": getattr(part, "tool_call_id", ""),
                            "name": getattr(part, "tool_name", ""),
                            "content": str(getattr(part, "content", "")),
                        }
                    )

        elif msg_type == "ModelResponse":
            # ModelResponse contains assistant text and tool calls
            text_parts: list[str] = []
            tool_calls: list[dict[str, Any]] = []

            for part in getattr(msg, "parts", []):
                part_type = type(part).__name__

                if part_type == "TextPart":
                    text_parts.append(getattr(part, "content", ""))
                elif part_type == "ToolCallPart":
                    args = getattr(part, "args", {})
                    # Convert args to JSON string if it's a dict
                    args_str = json.dumps(args) if isinstance(args, dict) else str(args)

                    tool_calls.append(
                        {
                            "id": getattr(part, "tool_call_id", ""),
                            "type": "function",
                            "function": {
                                "name": getattr(part, "tool_name", ""),
                                "arguments": args_str,
                            },
                        }
                    )

            # Create assistant message
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": " ".join(text_parts) if text_parts else "",
            }
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls

            result.append(assistant_msg)

    return result


def dicts_to_model_messages(messages: list[dict[str, Any]]) -> list[ModelMessage]:
    """Convert dict format messages to pydantic-ai ModelMessage format.

    Args:
        messages: List of message dictionaries with role and content.

    Returns:
        List of ModelRequest/ModelResponse objects suitable for pydantic-ai message_history.

    Note:
        This creates a representation compatible with pydantic-ai's expected format.
        Complex tool call scenarios may require additional handling.
    """
    from pydantic_ai.messages import (
        ModelRequest,
        ModelResponse,
        SystemPromptPart,
        TextPart,
        ToolCallPart,
        ToolReturnPart,
        UserPromptPart,
    )

    result: list[ModelMessage] = []
    current_request_parts: list[Any] = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            current_request_parts.append(SystemPromptPart(content=content))

        elif role == "user":
            current_request_parts.append(UserPromptPart(content=content))
            # Flush as request after user message
            if current_request_parts:
                result.append(ModelRequest(parts=current_request_parts))
                current_request_parts = []

        elif role == "assistant":
            # Flush any pending request parts
            if current_request_parts:
                result.append(ModelRequest(parts=current_request_parts))
                current_request_parts = []

            # Build response parts
            response_parts: list[Any] = []

            if content:
                response_parts.append(TextPart(content=content))

            # Handle tool calls if present
            tool_calls = msg.get("tool_calls", [])
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}

                response_parts.append(
                    ToolCallPart(
                        tool_name=func.get("name", ""),
                        args=args,
                        tool_call_id=tool_call.get("id", ""),
                    )
                )

            if response_parts:
                result.append(ModelResponse(parts=response_parts))

        elif role == "tool":
            # Tool return goes into a request
            current_request_parts.append(
                ToolReturnPart(
                    tool_name=msg.get("name", ""),
                    content=content,
                    tool_call_id=msg.get("tool_call_id", ""),
                )
            )

    # Flush any remaining request parts
    if current_request_parts:
        result.append(ModelRequest(parts=current_request_parts))

    return result
