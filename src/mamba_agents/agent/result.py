"""Agent result wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from pydantic_ai.result import RunResult
    from pydantic_ai.usage import Usage


T = TypeVar("T")


@dataclass
class AgentResult[T]:
    """Wrapper for agent run results with additional metadata.

    Provides convenient access to the result output, message history,
    and usage statistics.

    Attributes:
        _result: The underlying pydantic-ai RunResult.
    """

    _result: RunResult[T]

    @property
    def output(self) -> T:
        """Get the final output from the agent run.

        Returns:
            The typed output from the agent.
        """
        return self._result.output

    @property
    def data(self) -> T:
        """Alias for output (for backwards compatibility).

        Returns:
            The typed output from the agent.
        """
        return self._result.output

    def usage(self) -> Usage:
        """Get token usage statistics for this run.

        Returns:
            Usage statistics including input/output tokens.
        """
        return self._result.usage()

    def new_messages(self) -> list[Any]:
        """Get new messages generated during this run.

        Returns:
            List of messages from this run (for message history).
        """
        return self._result.new_messages()

    def all_messages(self) -> list[Any]:
        """Get all messages including history.

        Returns:
            Complete message history including new messages.
        """
        return self._result.all_messages()
