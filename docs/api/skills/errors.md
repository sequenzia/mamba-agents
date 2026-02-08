<!-- docs/api/skills/errors.md -->
# Skill Errors

Exception classes for the skills subsystem.

!!! warning "Experimental"
    The skills subsystem is experimental. Public API may change in minor versions.

## Error Hierarchy

```
SkillError (base)
├── SkillNotFoundError(name, path)
├── SkillParseError(name, path, detail)
├── SkillValidationError(name, errors, path)
├── SkillLoadError(name, path, cause)
├── SkillConflictError(name, paths)
└── SkillInvocationError(name, source, reason)
```

## Quick Example

```python
from mamba_agents.skills import SkillManager
from mamba_agents.skills.errors import (
    SkillError,
    SkillNotFoundError,
    SkillConflictError,
    SkillInvocationError,
)

manager = SkillManager()
manager.discover()

try:
    content = manager.activate("my-skill", arguments="file.txt")
except SkillNotFoundError as e:
    print(f"Skill not found: {e.name}")
except SkillInvocationError as e:
    print(f"Cannot invoke {e.name} from {e.source}: {e.reason}")
except SkillError as e:
    # Catch-all for any skill error
    print(f"Skill error: {e.message}")
```

## When Raised

| Exception | Typical Trigger |
|-----------|----------------|
| `SkillNotFoundError` | `activate()` or `deregister()` called with an unregistered skill name; path does not exist or has no SKILL.md |
| `SkillParseError` | SKILL.md frontmatter contains invalid YAML syntax |
| `SkillValidationError` | Required fields (`name`, `description`) missing or field values fail schema validation |
| `SkillLoadError` | Permission denied or disk I/O error when reading SKILL.md |
| `SkillConflictError` | `register()` called with a skill name that already exists in the registry |
| `SkillInvocationError` | Model invocation blocked (`disable_model_invocation: true`), user invocation blocked (`user_invocable: false`), untrusted skill with fork mode, or circular skill-subagent reference detected |

## Exceptions

### SkillError

Base exception for all skill-related errors. Catch this to handle any
skill error with a single handler.

| Attribute | Type | Description |
|-----------|------|-------------|
| `message` | `str` | Human-readable error message |

```python
from mamba_agents.skills.errors import SkillError

try:
    manager.activate("some-skill")
except SkillError as e:
    # Handles any skill error
    print(f"Skill error: {e.message}")
```

::: mamba_agents.skills.errors.SkillError
    options:
      show_root_heading: true

### SkillNotFoundError

Raised when a skill path does not exist or a skill name is not in the registry.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name that was not found |
| `path` | `Path` | Filesystem path that was checked |

```python
from mamba_agents.skills.errors import SkillNotFoundError

try:
    manager.activate("nonexistent")
except SkillNotFoundError as e:
    print(f"Skill '{e.name}' not found at {e.path}")
```

::: mamba_agents.skills.errors.SkillNotFoundError
    options:
      show_root_heading: true

### SkillParseError

Raised when SKILL.md frontmatter YAML has syntax errors.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name whose frontmatter failed to parse |
| `path` | `Path` | Filesystem path of the SKILL.md file |
| `detail` | `str` | Description of the parse error |

```python
from mamba_agents.skills.errors import SkillParseError

try:
    manager.register(Path("./broken-skill"))
except SkillParseError as e:
    print(f"Parse error in {e.name}: {e.detail}")
```

::: mamba_agents.skills.errors.SkillParseError
    options:
      show_root_heading: true

### SkillValidationError

Raised when frontmatter fields fail schema validation (e.g., missing
required fields, invalid values).

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name that failed validation |
| `errors` | `list[str]` | List of validation error messages |
| `path` | `Path \| None` | Filesystem path, if available |

```python
from mamba_agents.skills.errors import SkillValidationError

try:
    manager.register(Path("./invalid-skill"))
except SkillValidationError as e:
    print(f"Validation failed for '{e.name}':")
    for err in e.errors:
        print(f"  - {err}")
```

::: mamba_agents.skills.errors.SkillValidationError
    options:
      show_root_heading: true

### SkillLoadError

Raised on permission denied or disk I/O errors during skill file loading.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name that failed to load |
| `path` | `Path` | Filesystem path that could not be read |
| `cause` | `Exception \| None` | Original exception that caused the failure |

```python
from mamba_agents.skills.errors import SkillLoadError

try:
    content = manager.activate("restricted-skill")
except SkillLoadError as e:
    print(f"Cannot load '{e.name}' from {e.path}")
    if e.cause:
        print(f"  Cause: {e.cause}")
```

::: mamba_agents.skills.errors.SkillLoadError
    options:
      show_root_heading: true

### SkillConflictError

Raised when duplicate skill names exist in the same scope or when
registering a skill that already exists in the registry.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name that has duplicates |
| `paths` | `list[Path]` | Filesystem paths where duplicates were found |

```python
from mamba_agents.skills.errors import SkillConflictError

try:
    manager.register(Path("./my-skill"))
except SkillConflictError as e:
    print(f"Duplicate '{e.name}' found at:")
    for path in e.paths:
        print(f"  - {path}")
```

::: mamba_agents.skills.errors.SkillConflictError
    options:
      show_root_heading: true

### SkillInvocationError

Raised when a skill cannot be invoked due to permission restrictions,
trust level violations, or circular references.

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name that cannot be invoked |
| `source` | `str` | Invocation source that was denied (e.g., `"model"`, `"user"`) |
| `reason` | `str` | Human-readable explanation of why invocation was denied |

```python
from mamba_agents.skills.errors import SkillInvocationError

try:
    content = manager.activate("model-only-skill")
except SkillInvocationError as e:
    print(f"Cannot invoke '{e.name}' from '{e.source}': {e.reason}")
```

::: mamba_agents.skills.errors.SkillInvocationError
    options:
      show_root_heading: true
