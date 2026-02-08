"""Subagent subsystem exceptions."""

from __future__ import annotations


class SubagentError(Exception):
    """Base exception for all subagent-related errors.

    All custom exceptions in the subagents subsystem inherit from this class,
    allowing callers to catch all subagent errors with a single handler.

    Attributes:
        message: Human-readable error message.
    """

    def __init__(self, message: str) -> None:
        """Initialize the error.

        Args:
            message: Human-readable error message.
        """
        self.message = message
        super().__init__(message)

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{type(self).__name__}({self.message!r})"


class SubagentConfigError(SubagentError):
    """Raised when subagent configuration is invalid.

    Attributes:
        name: Subagent name with the invalid configuration.
        detail: Description of the configuration problem.
    """

    def __init__(self, name: str, detail: str) -> None:
        """Initialize the error.

        Args:
            name: Subagent name with the invalid configuration.
            detail: Description of the configuration problem.
        """
        self.name = name
        self.detail = detail
        super().__init__(f"Invalid configuration for subagent '{name}': {detail}")

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{type(self).__name__}(name={self.name!r}, detail={self.detail!r})"

    def __reduce__(self) -> tuple:
        """Support pickling with custom constructor arguments."""
        return (type(self), (self.name, self.detail))


class SubagentNotFoundError(SubagentError):
    """Raised when a referenced subagent config is not found.

    Attributes:
        config_name: Name of the subagent configuration that was not found.
        available: List of available configuration names, if known.
    """

    def __init__(
        self,
        config_name: str,
        available: list[str] | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            config_name: Name of the subagent configuration that was not found.
            available: List of available configuration names, if known.
        """
        self.config_name = config_name
        self.available = list(available) if available is not None else None
        available_str = ""
        if self.available is not None:
            available_str = f" Available configs: {', '.join(self.available)}"
        super().__init__(f"Subagent config '{config_name}' not found.{available_str}")

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{type(self).__name__}(config_name={self.config_name!r}, available={self.available!r})"
        )

    def __reduce__(self) -> tuple:
        """Support pickling with custom constructor arguments."""
        return (type(self), (self.config_name, self.available))


class SubagentNestingError(SubagentError):
    """Raised when a subagent attempts to spawn a sub-subagent.

    Subagents are not allowed to spawn their own child subagents. This
    constraint prevents unbounded nesting depth and resource exhaustion.

    Attributes:
        name: Name of the subagent that attempted nesting.
        parent_name: Name of the parent that originally spawned this subagent.
    """

    def __init__(self, name: str, parent_name: str) -> None:
        """Initialize the error.

        Args:
            name: Name of the subagent that attempted nesting.
            parent_name: Name of the parent that originally spawned this subagent.
        """
        self.name = name
        self.parent_name = parent_name
        super().__init__(
            f"Subagent '{name}' (child of '{parent_name}') attempted to spawn "
            f"a sub-subagent. Nesting is not allowed."
        )

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{type(self).__name__}(name={self.name!r}, parent_name={self.parent_name!r})"

    def __reduce__(self) -> tuple:
        """Support pickling with custom constructor arguments."""
        return (type(self), (self.name, self.parent_name))


class SubagentDelegationError(SubagentError):
    """Raised when an error occurs during task delegation to a subagent.

    Attributes:
        name: Name of the subagent that failed during delegation.
        task: The task description that was being delegated.
        cause: The underlying exception that caused the delegation failure.
    """

    def __init__(
        self,
        name: str,
        task: str,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            name: Name of the subagent that failed during delegation.
            task: The task description that was being delegated.
            cause: The underlying exception that caused the delegation failure.
        """
        self.name = name
        self.task = task
        self.cause = cause
        cause_str = f" Cause: {cause}" if cause else ""
        super().__init__(f"Delegation to subagent '{name}' failed for task: {task!r}.{cause_str}")

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{type(self).__name__}(name={self.name!r}, task={self.task!r}, cause={self.cause!r})"
        )

    def __reduce__(self) -> tuple:
        """Support pickling with custom constructor arguments."""
        return (type(self), (self.name, self.task, self.cause))


class SubagentTimeoutError(SubagentError):
    """Raised when a subagent exceeds its maximum allowed turns.

    Attributes:
        name: Name of the subagent that timed out.
        max_turns: The maximum number of turns allowed.
        turns_used: The number of turns actually used, if known.
    """

    def __init__(
        self,
        name: str,
        max_turns: int,
        turns_used: int | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            name: Name of the subagent that timed out.
            max_turns: The maximum number of turns allowed.
            turns_used: The number of turns actually used, if known.
        """
        self.name = name
        self.max_turns = max_turns
        self.turns_used = turns_used
        turns_str = f" (used {turns_used})" if turns_used is not None else ""
        super().__init__(f"Subagent '{name}' exceeded maximum of {max_turns} turns{turns_str}.")

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{type(self).__name__}(name={self.name!r}, "
            f"max_turns={self.max_turns!r}, turns_used={self.turns_used!r})"
        )

    def __reduce__(self) -> tuple:
        """Support pickling with custom constructor arguments."""
        return (type(self), (self.name, self.max_turns, self.turns_used))
