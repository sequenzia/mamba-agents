"""Tool registration and management."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolInfo:
    """Information about a registered tool.

    Attributes:
        name: Tool name.
        func: The tool function.
        description: Tool description.
        enabled: Whether the tool is currently enabled.
        group: Optional group/namespace for the tool.
    """

    name: str
    func: Callable[..., Any]
    description: str
    enabled: bool = True
    group: str | None = None


class ToolRegistry:
    """Registry for managing tool functions.

    Provides tool registration, enable/disable, and grouping functionality.
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, ToolInfo] = {}

    def register(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        group: str | None = None,
    ) -> Callable[..., Any]:
        """Register a tool function.

        Can be used as a decorator with or without arguments.

        Args:
            func: The tool function to register.
            name: Optional custom name (defaults to function name).
            description: Optional description (defaults to docstring).
            group: Optional group/namespace.

        Returns:
            The original function (for decorator use).
        """

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or f.__name__
            tool_desc = description or f.__doc__ or ""

            self._tools[tool_name] = ToolInfo(
                name=tool_name,
                func=f,
                description=tool_desc,
                group=group,
            )
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def get(self, name: str) -> ToolInfo | None:
        """Get a tool by name.

        Args:
            name: The tool name.

        Returns:
            ToolInfo if found, None otherwise.
        """
        return self._tools.get(name)

    def get_enabled(self) -> list[ToolInfo]:
        """Get all enabled tools.

        Returns:
            List of enabled ToolInfo objects.
        """
        return [t for t in self._tools.values() if t.enabled]

    def get_by_group(self, group: str) -> list[ToolInfo]:
        """Get tools by group.

        Args:
            group: The group name.

        Returns:
            List of ToolInfo objects in the group.
        """
        return [t for t in self._tools.values() if t.group == group]

    def enable(self, name: str) -> bool:
        """Enable a tool.

        Args:
            name: The tool name.

        Returns:
            True if the tool was found and enabled.
        """
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a tool.

        Args:
            name: The tool name.

        Returns:
            True if the tool was found and disabled.
        """
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    def list_all(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names.
        """
        return list(self._tools.keys())

    def as_functions(self) -> list[Callable[..., Any]]:
        """Get all enabled tools as a list of functions.

        Returns:
            List of tool functions.
        """
        return [t.func for t in self.get_enabled()]
