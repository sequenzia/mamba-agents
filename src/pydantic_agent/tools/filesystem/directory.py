"""Directory listing tool."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_agent.tools.filesystem.security import FilesystemSecurity


def list_directory(
    path: str,
    recursive: bool = False,
    max_depth: int = 2,
    security: "FilesystemSecurity | None" = None,
) -> list[dict[str, Any]]:
    """List contents of a directory.

    Args:
        path: Path to the directory to list.
        recursive: Whether to list recursively.
        max_depth: Maximum depth for recursive listing.
        security: Optional security context for path validation.

    Returns:
        List of dictionaries with file/directory information.

    Raises:
        FileNotFoundError: If the directory does not exist.
        NotADirectoryError: If the path is not a directory.
        PermissionError: If access is denied or path is outside sandbox.
    """
    if security is not None:
        validated_path = security.validate_path(path)
    else:
        validated_path = Path(path)

    if not validated_path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")

    if not validated_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {path}")

    entries: list[dict[str, Any]] = []

    def process_entry(entry_path: Path, current_depth: int) -> None:
        """Process a single directory entry."""
        if current_depth > max_depth:
            return

        try:
            stat = entry_path.stat()
            entry_info = {
                "name": entry_path.name,
                "path": str(entry_path),
                "is_file": entry_path.is_file(),
                "is_dir": entry_path.is_dir(),
                "size": stat.st_size if entry_path.is_file() else None,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
            entries.append(entry_info)

            # Recurse into directories if requested
            if recursive and entry_path.is_dir():
                for child in entry_path.iterdir():
                    process_entry(child, current_depth + 1)

        except PermissionError:
            # Skip entries we can't access
            entries.append({
                "name": entry_path.name,
                "path": str(entry_path),
                "error": "Permission denied",
            })

    for entry in validated_path.iterdir():
        process_entry(entry, 1)

    return entries
