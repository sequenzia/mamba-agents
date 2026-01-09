"""File information tool."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic_agent.tools.filesystem.security import FilesystemSecurity


def file_info(
    path: str,
    security: FilesystemSecurity | None = None,
) -> dict[str, Any]:
    """Get file or directory metadata.

    Args:
        path: Path to the file or directory.
        security: Optional security context for path validation.

    Returns:
        Dictionary with file metadata including:
        - name: The file name
        - path: Full path
        - is_file: Whether it's a file
        - is_dir: Whether it's a directory
        - size: Size in bytes (files only)
        - modified: Modification time (ISO format)
        - created: Creation time (ISO format)

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If access is denied or path is outside sandbox.
    """
    if security is not None:
        validated_path = security.validate_path(path)
    else:
        validated_path = Path(path)

    if not validated_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    stat = validated_path.stat()

    return {
        "name": validated_path.name,
        "path": str(validated_path),
        "is_file": validated_path.is_file(),
        "is_dir": validated_path.is_dir(),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
    }
