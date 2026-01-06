"""Built-in tools for pydantic-agent."""

from pydantic_agent.tools.bash import run_bash
from pydantic_agent.tools.filesystem import (
    append_file,
    copy_file,
    delete_file,
    file_info,
    list_directory,
    move_file,
    read_file,
    write_file,
)
from pydantic_agent.tools.glob import glob_search
from pydantic_agent.tools.grep import grep_search
from pydantic_agent.tools.registry import ToolRegistry

__all__ = [
    # Filesystem tools
    "read_file",
    "write_file",
    "append_file",
    "list_directory",
    "file_info",
    "delete_file",
    "move_file",
    "copy_file",
    # Search tools
    "glob_search",
    "grep_search",
    # Shell tools
    "run_bash",
    # Registry
    "ToolRegistry",
]
