"""Security enforcement for filesystem operations."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, field_validator


class FilesystemSecurity(BaseModel):
    """Security enforcement for filesystem operations.

    Provides sandbox mode, path traversal prevention, and extension filtering.

    Attributes:
        base_directory: If set, restricts all operations to this directory.
        allowed_extensions: If set, only these extensions are permitted.
        denied_extensions: Extensions that are always blocked.
        max_file_size: Maximum file size in bytes for read operations.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    base_directory: Path | None = None
    allowed_extensions: set[str] | None = None
    denied_extensions: set[str] = set()
    max_file_size: int | None = None

    @field_validator("base_directory", mode="before")
    @classmethod
    def resolve_base_directory(cls, v: Path | str | None) -> Path | None:
        """Resolve base_directory to an absolute Path."""
        if v is None:
            return None
        return Path(v).resolve()

    def validate_path(self, path: str | Path) -> Path:
        """Validate and resolve a path against security constraints.

        Args:
            path: The path to validate.

        Returns:
            The resolved, validated Path object.

        Raises:
            PermissionError: If the path violates security constraints.
        """
        resolved = Path(path).resolve()

        # Check sandbox constraint
        if self.base_directory is not None:
            try:
                resolved.relative_to(self.base_directory)
            except ValueError:
                raise PermissionError(
                    f"Path outside allowed directory: {path} not in {self.base_directory}"
                )

        # Check extension constraints
        suffix = resolved.suffix.lower()

        if self.denied_extensions and suffix in self.denied_extensions:
            raise PermissionError(f"Extension {suffix} is denied")

        if self.allowed_extensions and suffix not in self.allowed_extensions:
            raise PermissionError(
                f"Extension {suffix} not allowed. Allowed: {self.allowed_extensions}"
            )

        return resolved

    def validate_read(self, path: Path) -> None:
        """Validate a file for reading.

        Args:
            path: The path to validate for reading.

        Raises:
            PermissionError: If the file exceeds size limits.
            FileNotFoundError: If the file doesn't exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if self.max_file_size is not None and path.is_file():
            size = path.stat().st_size
            if size > self.max_file_size:
                raise PermissionError(
                    f"File size {size} exceeds maximum {self.max_file_size}"
                )
