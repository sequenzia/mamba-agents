<!-- docs/api/skills/config.md -->
# Configuration

Skill data models, enums, and configuration for the skills subsystem.

!!! warning "Experimental"
    The skills subsystem is experimental. Public API may change in minor versions.

## Quick Example

```python
from mamba_agents.skills import (
    SkillConfig,
    SkillInfo,
    Skill,
    SkillScope,
    TrustLevel,
    ValidationResult,
)

# Configure skill discovery
config = SkillConfig(
    skills_dirs=[".mamba/skills"],
    custom_paths=["./vendor/skills"],
    namespace_tools=True,
    trusted_paths=["./vendor/skills"],  # trust custom path
)
```

## Enums

### SkillScope

Determines where a skill was discovered and its default trust level.

| Value | Description | Default Trust |
|-------|-------------|---------------|
| `PROJECT` | Project-level skill from `.mamba/skills/` | `TRUSTED` |
| `USER` | User-level skill from `~/.mamba/skills/` | `TRUSTED` |
| `CUSTOM` | Skill from a custom configured path | `UNTRUSTED` |

```python
from mamba_agents.skills import SkillScope

scope = SkillScope.PROJECT
assert scope.value == "project"
```

::: mamba_agents.skills.config.SkillScope
    options:
      show_root_heading: true
      members: false

### TrustLevel

Controls what capabilities a skill is permitted to use.

| Value | Description |
|-------|-------------|
| `TRUSTED` | Full access to tools and model invocation |
| `UNTRUSTED` | Restricted access; hooks and fork execution are blocked |

```python
from mamba_agents.skills import TrustLevel

level = TrustLevel.TRUSTED
assert level.value == "trusted"
```

::: mamba_agents.skills.config.TrustLevel
    options:
      show_root_heading: true
      members: false

## Data Models

### SkillInfo

Metadata about a discovered skill, loaded eagerly at discovery time (Tier 1).
Contains all frontmatter fields from the SKILL.md specification plus
mamba-agents extensions.

#### Key Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | *required* | Validated skill identifier |
| `description` | `str` | *required* | Human-readable description |
| `path` | `Path` | *required* | Directory containing the SKILL.md file |
| `scope` | `SkillScope` | *required* | Discovery scope (project, user, custom) |
| `license` | `str \| None` | `None` | SPDX license identifier |
| `compatibility` | `str \| None` | `None` | Compatibility constraints (e.g., tool or version) |
| `metadata` | `dict[str, str] \| None` | `None` | Arbitrary key-value metadata from frontmatter |
| `allowed_tools` | `list[str] \| None` | `None` | Tool names this skill is permitted to use |
| `model` | `str \| None` | `None` | Model override for skill execution |
| `execution_mode` | `str \| None` | `None` | Execution mode (`"fork"` or `None`) |
| `agent` | `str \| None` | `None` | Subagent config name for fork mode |
| `disable_model_invocation` | `bool` | `False` | Block LLM-initiated invocation |
| `user_invocable` | `bool` | `True` | Allow user-initiated invocation |
| `argument_hint` | `str \| None` | `None` | Hint text for skill argument input |
| `hooks` | `dict[str, Any] \| None` | `None` | Reserved for future lifecycle hooks |
| `trust_level` | `TrustLevel` | `TRUSTED` | Resolved trust level |

```python
from pathlib import Path
from mamba_agents.skills import SkillInfo, SkillScope, TrustLevel

info = SkillInfo(
    name="code-review",
    description="Reviews code for common issues",
    path=Path(".mamba/skills/code-review"),
    scope=SkillScope.PROJECT,
    allowed_tools=["read_file", "grep_search"],
    trust_level=TrustLevel.TRUSTED,
)
```

::: mamba_agents.skills.config.SkillInfo
    options:
      show_root_heading: true
      show_source: true

### Skill

Full skill with lazily-loaded body content and runtime activation state.
Wraps a `SkillInfo` with the markdown body from SKILL.md.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `info` | `SkillInfo` | *required* | Skill metadata (always loaded) |
| `body` | `str \| None` | `None` | SKILL.md markdown body (lazy loaded) |
| `is_active` | `bool` | `False` | Whether the skill is currently activated |

!!! note "Private Attributes"
    `Skill` has a private `_tools` attribute (`list[Callable]`) that stores
    registered tool callables at runtime. It is excluded from serialization.

```python
from mamba_agents.skills import Skill, SkillInfo, SkillScope

skill = Skill(
    info=SkillInfo(
        name="my-skill",
        description="Example skill",
        path=Path(".mamba/skills/my-skill"),
        scope=SkillScope.PROJECT,
    ),
    body="You are a helpful assistant.\n\nProcess: $ARGUMENTS",
)
```

::: mamba_agents.skills.config.Skill
    options:
      show_root_heading: true
      show_source: true

## Configuration

### SkillConfig

Configuration for the skill subsystem. Used by `SkillManager` and
`AgentSettings.skills`.

#### Key Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `skills_dirs` | `list[Path]` | `[Path(".mamba/skills")]` | Directories to scan for project-level skills |
| `user_skills_dir` | `Path` | `Path("~/.mamba/skills")` | User-level skills directory (`~` is expanded) |
| `custom_paths` | `list[Path]` | `[]` | Additional search paths for skill discovery |
| `auto_discover` | `bool` | `True` | Auto-discover skills on startup |
| `namespace_tools` | `bool` | `True` | Prefix skill tools with the skill name |
| `trusted_paths` | `list[Path]` | `[]` | Paths to treat as trusted (in addition to project/user) |

```python
from pathlib import Path
from mamba_agents.skills import SkillConfig

# Default configuration
config = SkillConfig()

# Custom configuration
config = SkillConfig(
    skills_dirs=[Path(".mamba/skills"), Path("extra/skills")],
    custom_paths=[Path("./vendor/skills")],
    trusted_paths=[Path("./vendor/skills")],
    namespace_tools=False,
    auto_discover=True,
)
```

!!! tip "Trusting custom paths"
    Custom paths default to `UNTRUSTED`. Add them to `trusted_paths` to
    grant full tool access and fork execution to skills from those directories.

::: mamba_agents.skills.config.SkillConfig
    options:
      show_root_heading: true
      show_source: true

### ValidationResult

Result from validating a skill against the SKILL.md schema.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `valid` | `bool` | *required* | Whether the skill passed validation |
| `errors` | `list[str]` | `[]` | Validation error messages |
| `warnings` | `list[str]` | `[]` | Validation warnings |
| `skill_path` | `Path \| None` | `None` | Path to the validated skill |
| `trust_level` | `TrustLevel \| None` | `None` | Resolved trust level |

```python
from mamba_agents.skills import SkillManager
from pathlib import Path

manager = SkillManager()
result = manager.validate(Path("./my-skill"))

if result.valid:
    print("Skill is valid")
    if result.warnings:
        for w in result.warnings:
            print(f"  Warning: {w}")
else:
    for e in result.errors:
        print(f"  Error: {e}")
```

::: mamba_agents.skills.config.ValidationResult
    options:
      show_root_heading: true
      show_source: true
