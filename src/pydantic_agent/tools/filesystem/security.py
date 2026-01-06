"""Security enforcement for filesystem operations."""

from __future__ import annotations

from pathlib import Path


class FilesystemSecurity:
    """Security enforcement for filesystem operations.

    Provides sandbox mode, path traversal prevention, and extension filtering.

    Attributes:
        base_directory: If set, restricts all operations to this directory.
        allowed_extensions: If set, only these extensions are permitted.
        denied_extensions: Extensions that are always blocked.
        max_file_size: Maximum file size in bytes for read operations.
    """

    def __init__(
        self,
        base_directory: Path | str | None = None,
        allowed_extensions: set[str] | None = None,
        denied_extensions: set[str] | None = None,
        max_file_size: int | None = None,
    ) -> None:
        """Initialize filesystem security.

        Args:
            base_directory: Optional sandbox directory. All paths must be within.
            allowed_extensions: Optional set of allowed extensions (e.g., {".txt", ".md"}).
            denied_extensions: Optional set of denied extensions (e.g., {".exe", ".sh"}).
            max_file_size: Optional maximum file size in bytes.
        """
        self.base_directory = Path(base_directory).resolve() if base_directory else None
        self.allowed_extensions = allowed_extensions
        self.denied_extensions = denied_extensions or set()
        self.max_file_size = max_file_size

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
