# MCP Errors

Exception classes for MCP configuration errors.

## Error Hierarchy

```
MCPConfigError (base)
├── MCPFileNotFoundError
├── MCPFileParseError
└── MCPServerValidationError
```

## Quick Example

```python
from mamba_agents.mcp import (
    MCPClientManager,
    MCPConfigError,
    MCPFileNotFoundError,
    MCPFileParseError,
    MCPServerValidationError,
)

try:
    manager = MCPClientManager.from_mcp_json(".mcp.json")
except MCPFileNotFoundError:
    print("Config file not found")
except MCPFileParseError as e:
    print(f"Invalid JSON: {e}")
except MCPServerValidationError as e:
    print(f"Invalid server entry: {e}")
except MCPConfigError as e:
    print(f"Configuration error: {e}")
```

## Exceptions

### MCPConfigError

Base exception for all MCP configuration errors. Catch this to handle any MCP config error.

```python
try:
    manager = MCPClientManager.from_mcp_json(".mcp.json")
except MCPConfigError as e:
    # Handles any MCP config error
    print(f"MCP config error: {e}")
```

### MCPFileNotFoundError

Raised when the `.mcp.json` file does not exist.

```python
from mamba_agents.mcp import load_mcp_json, MCPFileNotFoundError

try:
    configs = load_mcp_json("nonexistent.mcp.json")
except MCPFileNotFoundError:
    print("Config file not found, using defaults")
    configs = []
```

### MCPFileParseError

Raised when the file exists but contains invalid JSON.

```python
from mamba_agents.mcp import load_mcp_json, MCPFileParseError

try:
    configs = load_mcp_json(".mcp.json")
except MCPFileParseError as e:
    print(f"Fix your JSON syntax: {e}")
```

### MCPServerValidationError

Raised when a server entry in the file is invalid (e.g., missing required fields).

```python
from mamba_agents.mcp import load_mcp_json, MCPServerValidationError

try:
    configs = load_mcp_json(".mcp.json")
except MCPServerValidationError as e:
    print(f"Invalid server config: {e}")
```

Common validation errors:

- Missing both `command` and `url`
- Specifying both `command` and `url`

## API Reference

::: mamba_agents.mcp.errors.MCPConfigError
    options:
      show_root_heading: true

::: mamba_agents.mcp.errors.MCPFileNotFoundError
    options:
      show_root_heading: true

::: mamba_agents.mcp.errors.MCPFileParseError
    options:
      show_root_heading: true

::: mamba_agents.mcp.errors.MCPServerValidationError
    options:
      show_root_heading: true
