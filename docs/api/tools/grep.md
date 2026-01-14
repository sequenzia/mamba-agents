# Grep Tool

Search file contents with regex.

## Quick Example

```python
from pydantic_agent.tools import grep_search

# Search for pattern
matches = grep_search(
    pattern=r"def \w+\(",
    path="/project",
)

# With file filter
matches = grep_search(
    pattern="TODO",
    path="/src",
    file_pattern="*.py",
)

# With context lines
matches = grep_search(
    pattern="error",
    path="/logs",
    context_lines=2,
)

# Process results
for match in matches:
    print(f"{match.file}:{match.line}: {match.content}")
```

## API Reference

::: pydantic_agent.tools.grep.grep_search
    options:
      show_root_heading: true
      show_source: true
