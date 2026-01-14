# Tools Module

Built-in tools for agent use.

## Available Tools

| Tool | Description |
|------|-------------|
| [Filesystem](filesystem.md) | File operations |
| [Bash](bash.md) | Shell commands |
| [Glob](glob.md) | Pattern matching |
| [Grep](grep.md) | Content search |
| [ToolRegistry](registry.md) | Tool management |

## Quick Example

```python
from pydantic_agent import Agent
from pydantic_agent.tools import (
    read_file,
    write_file,
    list_directory,
    glob_search,
    grep_search,
    run_bash,
)

agent = Agent(
    "gpt-4o",
    tools=[read_file, write_file, glob_search, grep_search, run_bash],
)
```

## Tool Categories

### File Operations
- `read_file` - Read file contents
- `write_file` - Write to file
- `append_file` - Append to file
- `list_directory` - List directory
- `file_info` - Get file metadata
- `delete_file` - Delete file
- `move_file` - Move/rename file
- `copy_file` - Copy file

### Search
- `glob_search` - Find files by pattern
- `grep_search` - Search file contents

### Shell
- `run_bash` - Execute commands
