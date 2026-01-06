"""Message history management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MessageHistory:
    """Manages conversation message history.

    Provides methods for adding, retrieving, and manipulating messages.

    Attributes:
        messages: The list of messages.
        system_prompt: The system prompt (stored separately).
    """

    messages: list[dict[str, Any]] = field(default_factory=list)
    system_prompt: str | None = None

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Add a message to the history.

        Args:
            role: Message role (user, assistant, tool).
            content: Message content.
            **kwargs: Additional message fields.
        """
        message = {"role": role, "content": content, **kwargs}
        self.messages.append(message)

    def add_user_message(self, content: str) -> None:
        """Add a user message.

        Args:
            content: The message content.
        """
        self.add_message("user", content)

    def add_assistant_message(
        self, content: str, tool_calls: list[dict[str, Any]] | None = None
    ) -> None:
        """Add an assistant message.

        Args:
            content: The message content.
            tool_calls: Optional tool calls made by the assistant.
        """
        kwargs = {}
        if tool_calls:
            kwargs["tool_calls"] = tool_calls
        self.add_message("assistant", content, **kwargs)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        """Add a tool result message.

        Args:
            tool_call_id: ID of the tool call this is responding to.
            content: The tool result content.
        """
        self.add_message("tool", content, tool_call_id=tool_call_id)

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages.

        Returns:
            List of message dictionaries.
        """
        return self.messages.copy()

    def get_recent(self, n: int) -> list[dict[str, Any]]:
        """Get the n most recent messages.

        Args:
            n: Number of messages to retrieve.

        Returns:
            List of recent messages.
        """
        return self.messages[-n:] if n > 0 else []

    def get_turns(self) -> list[list[dict[str, Any]]]:
        """Get messages grouped by turns.

        A turn is a user message followed by assistant response(s).

        Returns:
            List of turns, each containing messages.
        """
        turns: list[list[dict[str, Any]]] = []
        current_turn: list[dict[str, Any]] = []

        for message in self.messages:
            if message["role"] == "user" and current_turn:
                turns.append(current_turn)
                current_turn = []

            current_turn.append(message)

        if current_turn:
            turns.append(current_turn)

        return turns

    def get_recent_turns(self, n: int) -> list[dict[str, Any]]:
        """Get messages from the n most recent turns.

        Args:
            n: Number of turns to retrieve.

        Returns:
            List of messages from recent turns.
        """
        turns = self.get_turns()
        recent_turns = turns[-n:] if n > 0 else []

        result = []
        for turn in recent_turns:
            result.extend(turn)

        return result

    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()

    def remove_oldest(self, n: int) -> list[dict[str, Any]]:
        """Remove and return the n oldest messages.

        Args:
            n: Number of messages to remove.

        Returns:
            The removed messages.
        """
        removed = self.messages[:n]
        self.messages = self.messages[n:]
        return removed

    def __len__(self) -> int:
        """Get the number of messages."""
        return len(self.messages)
