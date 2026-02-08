<!-- docs/api/skills/manager.md -->
# SkillManager

Main facade for skill discovery, registration, activation, and management.

!!! warning "Experimental"
    The skills subsystem is experimental. Public API may change in minor versions.

## Quick Example

```python
from mamba_agents.skills import SkillManager, SkillConfig

manager = SkillManager(config=SkillConfig())

# Discover skills from configured directories
discovered = manager.discover()

# Activate a skill with arguments
content = manager.activate("my-skill", arguments="file.txt")

# Get tools registered by an active skill
tools = manager.get_tools("my-skill")
```

## With Agent

The `Agent` class provides a facade over `SkillManager`, so you rarely need to
use it directly:

```python
from mamba_agents import Agent

agent = Agent(
    "gpt-4o",
    skills=["./code-review"],
    skill_dirs=[".mamba/skills"],
)

# Agent facade methods delegate to skill_manager
content = agent.invoke_skill("code-review", arguments="main.py")
skills = agent.list_skills()
```

## Discovery

```python
from mamba_agents.skills import SkillManager, SkillConfig

manager = SkillManager(config=SkillConfig(
    skills_dirs=[".mamba/skills"],
    custom_paths=["./vendor/skills"],
    auto_discover=True,
))

# Scan all configured directories for SKILL.md files
new_skills = manager.discover()
print(f"Found {len(new_skills)} new skills")

# Duplicate names are skipped on repeated calls
more = manager.discover()  # returns only newly found skills
```

## Registration

```python
from pathlib import Path
from mamba_agents.skills import SkillManager

manager = SkillManager()

# Register from a directory path
manager.register(Path("./my-skill"))

# Register from a SkillInfo or Skill instance
manager.register(skill_info)
manager.register(skill_instance)

# Remove a skill (deactivates first if active)
manager.deregister("my-skill")
```

## Activation & Deactivation

```python
manager = SkillManager()
manager.discover()

# Activate returns processed content with argument substitution
content = manager.activate("code-review", arguments="src/main.py")

# Re-activation refreshes with new arguments
content = manager.activate("code-review", arguments="src/utils.py")

# Deactivation is a no-op if skill is not active
manager.deactivate("code-review")
```

### Fork Execution Mode

Skills with `execution_mode: "fork"` delegate to a subagent instead of
returning content directly. This requires a linked `SubagentManager`:

```python
from mamba_agents.skills import SkillManager
from mamba_agents.subagents import SubagentManager

skill_mgr = SkillManager()
subagent_mgr = SubagentManager(parent_agent=agent)

# Wire the two managers together
skill_mgr.subagent_manager = subagent_mgr

# Now fork-mode skills delegate to subagents
result = skill_mgr.activate("fork-skill", arguments="task description")
```

## Tools

```python
# Get tools from a specific active skill
tools = manager.get_tools("my-skill")

# Get all tools from all active skills (with namespace prefixes)
all_tools = manager.get_all_tools()
# Tool names are prefixed: "my-skill:read_file", "my-skill:write_file"
```

## References (Tier 3)

```python
# List available reference files for a skill
refs = manager.get_references("my-skill")
# [Path(".mamba/skills/my-skill/references/api-docs.md"), ...]

# Load a specific reference file
content = manager.load_reference("my-skill", "api-docs.md")
```

## Validation

```python
from pathlib import Path

result = manager.validate(Path("./my-skill"))
if result.valid:
    print("Skill is valid")
else:
    for error in result.errors:
        print(f"Error: {error}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

## Error Handling

```python
from mamba_agents.skills import SkillManager
from mamba_agents.skills.errors import (
    SkillNotFoundError,
    SkillConflictError,
    SkillInvocationError,
)

manager = SkillManager()
manager.discover()

try:
    content = manager.activate("missing-skill")
except SkillNotFoundError:
    print("Skill not registered")

try:
    manager.register(Path("./duplicate-skill"))
except SkillConflictError:
    print("Skill name already registered")
```

## API Reference

::: mamba_agents.skills.manager.SkillManager
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - discover
        - register
        - deregister
        - get
        - list
        - activate
        - deactivate
        - validate
        - get_tools
        - get_all_tools
        - get_references
        - load_reference
        - subagent_manager

---

## SkillTestHarness

Test harness for validating and invoking skills without a full `Agent` instance.
Useful for skill authors who want to verify their SKILL.md files in isolation.

### Quick Example

```python
from pathlib import Path
from mamba_agents.skills.testing import SkillTestHarness

# From a skill directory
harness = SkillTestHarness(skill_path=Path("my-skill"))
skill = harness.load()
result = harness.validate()
content = harness.invoke("file.txt")
```

### Pytest Fixture

The `skill_harness` fixture provides a factory for test harness instances:

```python
from pathlib import Path

def test_my_skill(skill_harness):
    harness = skill_harness(path=Path("my-skill"))
    skill = harness.load()
    assert skill.info.name == "my-skill"

def test_skill_validation(skill_harness):
    harness = skill_harness(path=Path("my-skill"))
    result = harness.validate()
    assert result.valid
```

!!! tip "Register the fixture"
    Add `from mamba_agents.skills.testing import skill_harness` to your
    `conftest.py` to make the fixture available in all test files.

::: mamba_agents.skills.testing.SkillTestHarness
    options:
      show_root_heading: true
      show_source: true
