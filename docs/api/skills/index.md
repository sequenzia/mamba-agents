<!-- docs/api/skills/index.md -->
# Skills Module

Modular, discoverable agent capabilities based on the SKILL.md open standard.

!!! warning "Experimental"
    The skills subsystem is experimental. Public API may change in minor versions.

## Pages

| Page | Description |
|------|-------------|
| [SkillManager](manager.md) | Main facade for skill operations |
| [Configuration](config.md) | Skill, SkillInfo, SkillConfig, enums |
| [Errors](errors.md) | Skill exception hierarchy |

## Quick Example

```python
from mamba_agents import Agent

# Register skills at agent creation
agent = Agent(
    "gpt-4o",
    skills=["./my-skill"],       # paths to skill directories
    skill_dirs=[".mamba/skills"], # discover all skills in a directory
)

# Or use the SkillManager directly
from mamba_agents.skills import SkillManager, SkillConfig

manager = SkillManager(config=SkillConfig())
discovered = manager.discover()
content = manager.activate("my-skill", arguments="file.txt")
```

## Imports

```python
from mamba_agents import (
    # Manager
    SkillManager,
    # Data models
    Skill,
    SkillInfo,
    SkillConfig,
    # Enums
    SkillScope,
    TrustLevel,
    ValidationResult,
    # Errors
    SkillError,
    SkillNotFoundError,
    SkillParseError,
    SkillValidationError,
    SkillLoadError,
    SkillConflictError,
)

# Testing utilities
from mamba_agents.skills.testing import SkillTestHarness, skill_harness
```

## Key Concepts

### Progressive Disclosure

Skills use a three-tier loading model to minimize startup cost:

| Tier | What Loads | When |
|------|-----------|------|
| **Tier 1** — Metadata | YAML frontmatter only (`SkillInfo`) | Discovery / registration |
| **Tier 2** — Full body | Markdown body content (`Skill`) | First activation |
| **Tier 3** — References | Supplemental files from `references/` | On explicit request |

### Trust Levels

Skills inherit a trust level based on their discovery scope:

| Scope | Default Trust | Description |
|-------|---------------|-------------|
| `PROJECT` | `TRUSTED` | Project-level skills in `.mamba/skills/` |
| `USER` | `TRUSTED` | User-level skills in `~/.mamba/skills/` |
| `CUSTOM` | `UNTRUSTED` | Custom paths (unless listed in `trusted_paths`) |

Untrusted skills cannot use fork execution mode and have restricted tool access.

### Discovery Priority

When skills share the same name, the first discovered wins:

1. **Project** — `.mamba/skills/` (highest priority)
2. **User** — `~/.mamba/skills/`
3. **Custom** — paths from `SkillConfig.custom_paths` (lowest priority)
