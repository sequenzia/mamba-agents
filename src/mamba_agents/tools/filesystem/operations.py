"""File operations (delete, move, copy)."""

from __future__ import annotations

import shutil
from pathlib import Path

from mamba_agents.tools.filesystem.security import FilesystemSecurity


def delete_file(
    path: str,
    security: FilesystemSecurity | None = None,
) -> bool:
    """Delete a file.

    Args:
        path: Path to the file to delete.
        security: Optional security context for path validation.

    Returns:
        True if deletion was successful.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If access is denied or path is outside sandbox.
        IsADirectoryError: If the path is a directory.
    """
    validated_path = security.validate_path(path) if security is not None else Path(path)

    if not validated_path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if validated_path.is_dir():
        raise IsADirectoryError(f"Cannot delete directory with delete_file: {path}")

    validated_path.unlink()
    return True


def move_file(
    source: str,
    destination: str,
    security: FilesystemSecurity | None = None,
) -> str:
    """Move or rename a file.

    Args:
        source: Path to the source file.
        destination: Path to the destination (file or directory).
        security: Optional security context for path validation.

    Returns:
        The path of the moved file.

    Raises:
        FileNotFoundError: If the source file does not exist.
        PermissionError: If access is denied or path is outside sandbox.
    """
    if security is not None:
        source_path = security.validate_path(source)
        dest_path = security.validate_path(destination)
    else:
        source_path = Path(source)
        dest_path = Path(destination)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    # If destination is a directory, move file into it
    if dest_path.is_dir():
        dest_path = dest_path / source_path.name

    shutil.move(str(source_path), str(dest_path))
    return str(dest_path)


def copy_file(
    source: str,
    destination: str,
    security: FilesystemSecurity | None = None,
) -> str:
    """Copy a file.

    Args:
        source: Path to the source file.
        destination: Path to the destination (file or directory).
        security: Optional security context for path validation.

    Returns:
        The path of the copied file.

    Raises:
        FileNotFoundError: If the source file does not exist.
        PermissionError: If access is denied or path is outside sandbox.
    """
    if security is not None:
        source_path = security.validate_path(source)
        dest_path = security.validate_path(destination)
    else:
        source_path = Path(source)
        dest_path = Path(destination)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    # If destination is a directory, copy file into it
    if dest_path.is_dir():
        dest_path = dest_path / source_path.name

    shutil.copy2(str(source_path), str(dest_path))
    return str(dest_path)
