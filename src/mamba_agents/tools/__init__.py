"""Built-in tools for mamba-agents.

Provides production-ready tools for common operations:

Filesystem Tools:
    read_file, write_file, append_file, delete_file,
    copy_file, move_file, list_directory, file_info

Search Tools:
    glob_search - Find files by pattern (e.g., "**/*.py")
    grep_search - Search file contents with regex

Shell Tools:
    run_bash - Execute shell commands with timeout

Usage with Agent:
    >>> from mamba_agents import Agent
    >>> from mamba_agents.tools import read_file, run_bash, glob_search
    >>> agent = Agent("gpt-4o", tools=[read_file, run_bash, glob_search])

Direct Usage:
    >>> from mamba_agents.tools import read_file, glob_search
    >>> content = read_file("config.json")
    >>> py_files = glob_search("**/*.py", root_dir="/project")

Custom Tools:
    >>> @agent.tool_plain
    ... def my_tool(x: str) -> str:
    ...     '''Tool description for the LLM.'''
    ...     return x.upper()

Graceful Error Handling (v0.1.2+):
    By default, tool exceptions are converted to error messages
    that the LLM can see and recover from. Opt out per-tool:

    >>> @agent.tool_plain(graceful_errors=False)
    ... def critical_tool(x: str) -> str:
    ...     '''Exceptions propagate immediately.'''
    ...     ...

See Also:
    - examples/tools/ for runnable examples
    - docs/user-guide/tools.md for detailed guide
"""

from mamba_agents.tools.bash import run_bash
from mamba_agents.tools.filesystem import (
    append_file,
    copy_file,
    delete_file,
    file_info,
    list_directory,
    move_file,
    read_file,
    write_file,
)
from mamba_agents.tools.glob import glob_search
from mamba_agents.tools.grep import grep_search
from mamba_agents.tools.registry import ToolRegistry

__all__ = [
    "ToolRegistry",
    "append_file",
    "copy_file",
    "delete_file",
    "file_info",
    "glob_search",
    "grep_search",
    "list_directory",
    "move_file",
    "read_file",
    "run_bash",
    "write_file",
]
