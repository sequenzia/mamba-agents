"""File reading tool."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_agent.tools.filesystem.security import FilesystemSecurity


def read_file(
    path: str,
    encoding: str = "utf-8",
    security: "FilesystemSecurity | None" = None,
) -> str:
    """Read contents of a file.

    Args:
        path: Path to the file to read.
        encoding: Character encoding (default: utf-8).
        security: Optional security context for path validation.

    Returns:
        The file contents as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If access is denied or path is outside sandbox.
    """
    if security is not None:
        validated_path = security.validate_path(path)
        security.validate_read(validated_path)
    else:
        validated_path = Path(path)
        if not validated_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

    return validated_path.read_text(encoding=encoding)
