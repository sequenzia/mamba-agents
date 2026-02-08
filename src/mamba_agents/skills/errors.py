"""Skill subsystem exceptions."""

from __future__ import annotations

from pathlib import Path


class SkillError(Exception):
    """Base exception for all skill-related errors.

    All custom exceptions in the skills subsystem inherit from this class,
    allowing callers to catch all skill errors with a single handler.

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


class SkillNotFoundError(SkillError):
    """Raised when a skill path does not exist.

    Attributes:
        name: Skill name that was not found.
        path: Filesystem path that was checked.
    """

    def __init__(self, name: str, path: str | Path) -> None:
        """Initialize the error.

        Args:
            name: Skill name that was not found.
            path: Filesystem path that was checked.
        """
        self.name = name
        self.path = Path(path)
        super().__init__(f"Skill '{name}' not found at path: {self.path}")

    def __reduce__(self) -> tuple:
        """Support pickling by returning constructor arguments."""
        return (type(self), (self.name, str(self.path)))

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return f"{type(self).__name__}(name={self.name!r}, path={str(self.path)!r})"


class SkillParseError(SkillError):
    """Raised when SKILL.md frontmatter YAML has syntax errors.

    Attributes:
        name: Skill name whose frontmatter failed to parse.
        path: Filesystem path of the SKILL.md file.
    """

    def __init__(self, name: str, path: str | Path, detail: str) -> None:
        """Initialize the error.

        Args:
            name: Skill name whose frontmatter failed to parse.
            path: Filesystem path of the SKILL.md file.
            detail: Description of the parse error.
        """
        self.name = name
        self.path = Path(path)
        self.detail = detail
        super().__init__(f"Failed to parse frontmatter for skill '{name}' at {self.path}: {detail}")

    def __reduce__(self) -> tuple:
        """Support pickling by returning constructor arguments."""
        return (type(self), (self.name, str(self.path), self.detail))

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{type(self).__name__}(name={self.name!r}, "
            f"path={str(self.path)!r}, detail={self.detail!r})"
        )


class SkillValidationError(SkillError):
    """Raised when frontmatter fields fail validation.

    Attributes:
        name: Skill name that failed validation.
        errors: List of validation error messages.
        path: Filesystem path of the SKILL.md file, if available.
    """

    def __init__(
        self,
        name: str,
        errors: list[str],
        path: str | Path | None = None,
    ) -> None:
        """Initialize the error.

        Args:
            name: Skill name that failed validation.
            errors: List of validation error messages.
            path: Filesystem path of the SKILL.md file, if available.
        """
        self.name = name
        self.errors = list(errors)
        self.path = Path(path) if path is not None else None
        error_list = "; ".join(errors)
        path_str = f" at {self.path}" if self.path else ""
        super().__init__(f"Validation failed for skill '{name}'{path_str}: {error_list}")

    def __reduce__(self) -> tuple:
        """Support pickling by returning constructor arguments."""
        return (type(self), (self.name, self.errors, str(self.path) if self.path else None))

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{type(self).__name__}(name={self.name!r}, "
            f"errors={self.errors!r}, path={str(self.path) if self.path else None!r})"
        )


class SkillLoadError(SkillError):
    """Raised on permission denied or disk errors during skill loading.

    Attributes:
        name: Skill name that failed to load.
        path: Filesystem path that could not be read.
        cause: Original exception that caused the load failure.
    """

    def __init__(self, name: str, path: str | Path, cause: Exception | None = None) -> None:
        """Initialize the error.

        Args:
            name: Skill name that failed to load.
            path: Filesystem path that could not be read.
            cause: Original exception that caused the load failure.
        """
        self.name = name
        self.path = Path(path)
        self.cause = cause
        cause_str = f" ({cause})" if cause else ""
        super().__init__(f"Failed to load skill '{name}' from {self.path}{cause_str}")

    def __reduce__(self) -> tuple:
        """Support pickling by returning constructor arguments."""
        return (_rebuild_skill_load_error, (self.name, str(self.path), self.cause))

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{type(self).__name__}(name={self.name!r}, "
            f"path={str(self.path)!r}, cause={self.cause!r})"
        )


class SkillConflictError(SkillError):
    """Raised when duplicate skill names exist in the same scope.

    Attributes:
        name: Skill name that has duplicates.
        paths: Filesystem paths where duplicates were found.
    """

    def __init__(self, name: str, paths: list[str | Path]) -> None:
        """Initialize the error.

        Args:
            name: Skill name that has duplicates.
            paths: Filesystem paths where duplicates were found.
        """
        self.name = name
        self.paths = [Path(p) for p in paths]
        path_list = ", ".join(str(p) for p in self.paths)
        super().__init__(f"Duplicate skill '{name}' found in same scope: {path_list}")

    def __reduce__(self) -> tuple:
        """Support pickling by returning constructor arguments."""
        return (type(self), (self.name, [str(p) for p in self.paths]))

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        path_strs = [str(p) for p in self.paths]
        return f"{type(self).__name__}(name={self.name!r}, paths={path_strs!r})"


class SkillInvocationError(SkillError):
    """Raised when a skill cannot be invoked due to permission restrictions.

    Attributes:
        name: Skill name that cannot be invoked.
        source: Invocation source that was denied (e.g., "model", "user").
        reason: Human-readable explanation of why invocation was denied.
    """

    def __init__(self, name: str, source: str, reason: str) -> None:
        """Initialize the error.

        Args:
            name: Skill name that cannot be invoked.
            source: Invocation source that was denied.
            reason: Human-readable explanation of why invocation was denied.
        """
        self.name = name
        self.source = source
        self.reason = reason
        super().__init__(f"Cannot invoke skill '{name}' from source '{source}': {reason}")

    def __reduce__(self) -> tuple:
        """Support pickling by returning constructor arguments."""
        return (type(self), (self.name, self.source, self.reason))

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"{type(self).__name__}(name={self.name!r}, "
            f"source={self.source!r}, reason={self.reason!r})"
        )


def _rebuild_skill_load_error(
    name: str,
    path: str,
    cause: Exception | None,
) -> SkillLoadError:
    """Rebuild a SkillLoadError from pickled arguments."""
    return SkillLoadError(name, path, cause=cause)
