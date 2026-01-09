"""Glob pattern matching tool."""

from __future__ import annotations

from pathlib import Path

from pydantic_agent.tools.filesystem.security import FilesystemSecurity


def glob_search(
    pattern: str,
    root_dir: str = ".",
    recursive: bool = True,
    max_results: int = 1000,
    security: FilesystemSecurity | None = None,
) -> list[str]:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern to match (e.g., "*.py", "**/*.txt").
        root_dir: Root directory to search from.
        recursive: Whether to search recursively (default: True).
        max_results: Maximum number of results to return.
        security: Optional security context for path validation.

    Returns:
        List of matching file paths.

    Raises:
        PermissionError: If access is denied or path is outside sandbox.
    """
    if security is not None:
        root = security.validate_path(root_dir)
    else:
        root = Path(root_dir)

    if not root.exists():
        raise FileNotFoundError(f"Directory not found: {root_dir}")

    if not root.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_dir}")

    # Use rglob for recursive, glob for non-recursive
    if recursive:
        matches = root.rglob(pattern)
    else:
        matches = root.glob(pattern)

    results: list[str] = []
    for match in matches:
        if len(results) >= max_results:
            break
        results.append(str(match))

    return results
