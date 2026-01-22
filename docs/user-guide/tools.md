# Working with Tools

Tools give your agent the ability to interact with external systems, files, and execute code.

## Built-in Tools

Mamba Agents includes a set of production-ready tools:

### Filesystem Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read contents of a file |
| `write_file` | Write or overwrite a file |
| `append_file` | Append content to a file |
| `list_directory` | List directory contents with metadata |
| `file_info` | Get file metadata (size, modified, created) |
| `delete_file` | Delete a file |
| `move_file` | Move or rename a file |
| `copy_file` | Copy a file |

### Search Tools

| Tool | Description |
|------|-------------|
| `glob_search` | Find files matching a glob pattern |
| `grep_search` | Search file contents with regex |

### Shell Tools

| Tool | Description |
|------|-------------|
| `run_bash` | Execute shell commands |

## Using Built-in Tools

```python
from mamba_agents import Agent
from mamba_agents.tools import (
    read_file,
    write_file,
    list_directory,
    glob_search,
    grep_search,
    run_bash,
)

# Create agent with tools
agent = Agent(
    "gpt-4o",
    tools=[read_file, write_file, list_directory, glob_search, grep_search, run_bash],
)

# The agent can now use these tools
result = agent.run_sync("List all Python files in the current directory")
```

## Tool Examples

### File Operations

```python
from mamba_agents.tools import read_file, write_file, list_directory, file_info

# Read a file
content = read_file("config.json")

# Write a file
write_file("output.txt", "Hello, World!")

# List directory contents
entries = list_directory("/project", recursive=True)
for entry in entries:
    print(f"{entry.name}: {entry.size} bytes")

# Get file metadata
info = file_info("README.md")
print(f"Size: {info.size}, Modified: {info.modified}")
```

### Search Operations

```python
from mamba_agents.tools import glob_search, grep_search

# Find files by pattern
py_files = glob_search("**/*.py", root_dir="/project")
print(f"Found {len(py_files)} Python files")

# Search file contents
matches = grep_search(
    pattern=r"def \w+\(",
    path="/project",
    file_pattern="*.py",
    context_lines=2,
)
for match in matches:
    print(f"{match.file}:{match.line}: {match.content}")
```

### Shell Commands

```python
from mamba_agents.tools import run_bash

# Run a command
result = run_bash("ls -la", timeout=30)
print(result.stdout)

if result.return_code != 0:
    print(f"Error: {result.stderr}")

# Check if command timed out
if result.timed_out:
    print("Command timed out")
```

## Creating Custom Tools

### Using the Decorator

```python
from mamba_agents import Agent

agent = Agent("gpt-4o")

@agent.tool
def calculate(expression: str) -> str:
    """
    Evaluate a mathematical expression.

    Args:
        expression: A valid Python math expression like "2 + 2"

    Returns:
        The result as a string
    """
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

@agent.tool
async def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text[:1000]  # First 1000 chars
```

### Using tool_plain

Use `tool_plain` when you don't need context:

```python
@agent.tool_plain
def get_current_time() -> str:
    """Get the current date and time."""
    from datetime import datetime
    return datetime.now().isoformat()

@agent.tool_plain
def random_number(min_val: int = 1, max_val: int = 100) -> int:
    """Generate a random number in the given range."""
    import random
    return random.randint(min_val, max_val)
```

### Standalone Tool Functions

Create tools as standalone functions:

```python
def my_tool(query: str) -> str:
    """Process a query."""
    return f"Processed: {query}"

# Register with agent
agent = Agent("gpt-4o", tools=[my_tool])
```

## Tool Best Practices

### Clear Docstrings

The docstring is sent to the model, so make it clear:

```python
@agent.tool
def search_database(
    query: str,
    limit: int = 10,
    offset: int = 0,
) -> list[dict]:
    """
    Search the database for matching records.

    Args:
        query: The search query string
        limit: Maximum number of results to return (default: 10)
        offset: Number of results to skip for pagination (default: 0)

    Returns:
        A list of matching records as dictionaries

    Example:
        search_database("user", limit=5) returns up to 5 user records
    """
    # Implementation
    ...
```

### Error Handling

By default, Mamba Agents automatically converts tool exceptions to `ModelRetry`, allowing the LLM to receive error feedback and attempt recovery instead of crashing the agent loop.

```python
@agent.tool_plain
def read_config(path: str) -> str:
    """Read a configuration file."""
    with open(path) as f:
        return f.read()  # FileNotFoundError is caught automatically
```

If the LLM calls this tool with a non-existent path, it receives an error message like `"FileNotFoundError: [Errno 2] No such file or directory: 'missing.txt'"` and can try a different path.

#### Disabling Graceful Errors

For critical tools that must fail immediately (propagating the exception):

```python
# Per-tool opt-out
@agent.tool_plain(graceful_errors=False)
def critical_operation(data: str) -> str:
    """Critical tool that must not silently fail."""
    # Exceptions will propagate and stop the agent
    ...

# Agent-level disable
config = AgentConfig(graceful_tool_errors=False)
agent = Agent("gpt-4o", config=config)
```

#### Manual Error Handling (Optional)

You can still handle errors manually if you want custom error messages:

```python
@agent.tool
def read_config(path: str) -> str:
    """Read a configuration file."""
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File '{path}' not found. Try listing the directory first."
    except PermissionError:
        return f"Error: Permission denied for '{path}'"
```

### Type Hints

Always use type hints for parameters and return values:

```python
from typing import Optional

@agent.tool
def format_data(
    data: dict,
    format: str = "json",
    indent: Optional[int] = 2,
) -> str:
    """Format data in the specified format."""
    ...
```

## Security Sandbox

Restrict filesystem operations to a safe directory:

```python
from mamba_agents.tools.filesystem import FilesystemSecurity

# Create security context
security = FilesystemSecurity(
    sandbox_mode=True,
    base_directory="/safe/project/path",
    allowed_extensions=[".txt", ".json", ".py", ".md"],
)

# Tools will respect the sandbox
from mamba_agents.tools import read_file, write_file

# This works - within sandbox
content = read_file("data.txt", security=security)

# This fails - outside sandbox
content = read_file("/etc/passwd", security=security)  # Raises error
```

### Security Options

| Option | Type | Description |
|--------|------|-------------|
| `sandbox_mode` | bool | Enable sandbox restrictions |
| `base_directory` | str | Root directory for all operations |
| `allowed_extensions` | list | File extensions that can be accessed |

## Tool Registry

For organizing many tools:

```python
from mamba_agents.tools import ToolRegistry

registry = ToolRegistry()

# Register tools
registry.register(read_file)
registry.register(write_file)
registry.register(my_custom_tool)

# Get all tools
all_tools = registry.get_all()

# Use with agent
agent = Agent("gpt-4o", tools=all_tools)
```

## Next Steps

- [Context Management](context-management.md) - Manage conversation history
- [Workflows](workflows.md) - Orchestrate multi-step tool usage
- [Creating Custom Tools Tutorial](../tutorials/custom-tools.md) - Step-by-step guide
