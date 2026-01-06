"""Grep/search tool for file contents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_agent.tools.filesystem.security import FilesystemSecurity


@dataclass
class GrepMatch:
    """A single grep match result.

    Attributes:
        file: Path to the file containing the match.
        line_number: Line number of the match (1-indexed).
        line: The matching line content.
        context_before: Lines before the match.
        context_after: Lines after the match.
    """

    file: str
    line_number: int
    line: str
    context_before: list[str]
    context_after: list[str]


def grep_search(
    pattern: str,
    path: str,
    recursive: bool = True,
    file_pattern: str = "*",
    context_lines: int = 0,
    ignore_case: bool = False,
    regex: bool = True,
    max_results: int = 100,
    security: "FilesystemSecurity | None" = None,
) -> list[GrepMatch]:
    """Search file contents for a pattern.

    Args:
        pattern: Pattern to search for (string or regex).
        path: File or directory to search.
        recursive: Search directories recursively.
        file_pattern: Glob pattern for files to search (e.g., "*.py").
        context_lines: Number of lines to include before/after matches.
        ignore_case: Case-insensitive search.
        regex: Treat pattern as regex (default: True).
        max_results: Maximum number of matches to return.
        security: Optional security context for path validation.

    Returns:
        List of GrepMatch objects.

    Raises:
        FileNotFoundError: If the path doesn't exist.
        PermissionError: If access is denied.
    """
    if security is not None:
        search_path = security.validate_path(path)
    else:
        search_path = Path(path)

    if not search_path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    # Compile the pattern
    flags = re.IGNORECASE if ignore_case else 0
    if regex:
        compiled = re.compile(pattern, flags)
    else:
        # Escape special regex characters for literal search
        compiled = re.compile(re.escape(pattern), flags)

    matches: list[GrepMatch] = []

    # Get files to search
    if search_path.is_file():
        files = [search_path]
    else:
        if recursive:
            files = list(search_path.rglob(file_pattern))
        else:
            files = list(search_path.glob(file_pattern))

    for file_path in files:
        if not file_path.is_file():
            continue

        if len(matches) >= max_results:
            break

        try:
            # Skip binary files
            content = file_path.read_bytes()
            if b"\x00" in content[:8192]:  # Check first 8KB for null bytes
                continue

            lines = content.decode("utf-8", errors="replace").splitlines()

            for i, line in enumerate(lines):
                if len(matches) >= max_results:
                    break

                if compiled.search(line):
                    # Get context lines
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)

                    match = GrepMatch(
                        file=str(file_path),
                        line_number=i + 1,  # 1-indexed
                        line=line,
                        context_before=lines[start:i],
                        context_after=lines[i + 1 : end],
                    )
                    matches.append(match)

        except (PermissionError, OSError):
            # Skip files we can't read
            continue

    return matches
