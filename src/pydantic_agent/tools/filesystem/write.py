"""File writing tools."""

from __future__ import annotations

from pathlib import Path

from pydantic_agent.tools.filesystem.security import FilesystemSecurity


def write_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = False,
    security: FilesystemSecurity | None = None,
) -> str:
    """Write or overwrite a file.

    Args:
        path: Path to the file to write.
        content: Content to write to the file.
        encoding: Character encoding (default: utf-8).
        create_parents: Create parent directories if they don't exist.
        security: Optional security context for path validation.

    Returns:
        The path of the written file.

    Raises:
        PermissionError: If access is denied or path is outside sandbox.
        FileNotFoundError: If parent directory doesn't exist and create_parents is False.
    """
    if security is not None:
        validated_path = security.validate_path(path)
    else:
        validated_path = Path(path)

    if create_parents:
        validated_path.parent.mkdir(parents=True, exist_ok=True)

    validated_path.write_text(content, encoding=encoding)
    return str(validated_path)


def append_file(
    path: str,
    content: str,
    encoding: str = "utf-8",
    security: FilesystemSecurity | None = None,
) -> str:
    """Append content to a file.

    Creates the file if it doesn't exist.

    Args:
        path: Path to the file to append to.
        content: Content to append.
        encoding: Character encoding (default: utf-8).
        security: Optional security context for path validation.

    Returns:
        The path of the file.

    Raises:
        PermissionError: If access is denied or path is outside sandbox.
    """
    if security is not None:
        validated_path = security.validate_path(path)
    else:
        validated_path = Path(path)

    with validated_path.open("a", encoding=encoding) as f:
        f.write(content)

    return str(validated_path)
