# Bash Tool

Execute shell commands.

## Quick Example

```python
from pydantic_agent.tools import run_bash

# Run a command
result = run_bash("ls -la")
print(result.stdout)

# With timeout
result = run_bash("long_command", timeout=60)

# Check result
if result.return_code == 0:
    print("Success!")
else:
    print(f"Error: {result.stderr}")

if result.timed_out:
    print("Command timed out")
```

## BashResult

| Field | Type | Description |
|-------|------|-------------|
| `stdout` | str | Standard output |
| `stderr` | str | Standard error |
| `return_code` | int | Exit code |
| `timed_out` | bool | Did it timeout? |

## API Reference

::: pydantic_agent.tools.bash.run_bash
    options:
      show_root_heading: true
      show_source: true

::: pydantic_agent.tools.bash.BashResult
    options:
      show_root_heading: true
