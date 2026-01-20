"""Base classes and utilities for tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ToolConfig(BaseModel):
    """Configuration for a tool.

    Attributes:
        enabled: Whether the tool is enabled.
        retries: Number of retries for this tool.
        timeout: Optional timeout in seconds.
    """

    enabled: bool = True
    retries: int = 2
    timeout: float | None = None


@dataclass
class ToolResult[T]:
    """Result from a tool execution.

    Attributes:
        success: Whether the tool executed successfully.
        data: The result data if successful.
        error: Error message if failed.
    """

    success: bool
    data: T | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: T) -> ToolResult[T]:
        """Create a successful result.

        Args:
            data: The result data.

        Returns:
            A successful ToolResult.
        """
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> ToolResult[Any]:
        """Create a failed result.

        Args:
            error: The error message.

        Returns:
            A failed ToolResult.
        """
        return cls(success=False, error=error)
