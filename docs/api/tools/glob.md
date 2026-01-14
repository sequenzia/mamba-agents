# Glob Tool

Find files by pattern.

## Quick Example

```python
from pydantic_agent.tools import glob_search

# Find Python files
files = glob_search("**/*.py")

# In specific directory
files = glob_search("*.json", root_dir="/config")

# Multiple patterns
files = glob_search("**/*.{py,js,ts}")
```

## Pattern Syntax

| Pattern | Matches |
|---------|---------|
| `*` | Any characters in filename |
| `**` | Any directories |
| `?` | Single character |
| `[abc]` | Character set |
| `{a,b}` | Alternatives |

## API Reference

::: pydantic_agent.tools.glob.glob_search
    options:
      show_root_heading: true
      show_source: true
