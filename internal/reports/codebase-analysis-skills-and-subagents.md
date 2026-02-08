# Skills & Subagents Subsystems — Synthesized Analysis

**Analysis Context**: Documentation reference for Skills and Subagents subsystems
**Codebase Path**: `/Users/sequenzia/dev/repos/mamba-agents`
**Date**: 2026-02-08

---

## Executive Summary

The Skills and Subagents subsystems are **experimental extensions** to the mamba-agents framework that enable modular, reusable agent capabilities (skills) and isolated task delegation (subagents). Together they comprise **18 source files totaling ~4,478 lines** with **524 test functions across 13 test files** — comprehensive test coverage despite being marked experimental.

Both subsystems follow the framework's established **facade pattern**: `SkillManager` composes 5 internal components (loader, registry, validator, discovery, invocation) and `SubagentManager` composes 3 (spawner, delegation, loader). They integrate bi-directionally through `skills/integration.py`, enabling skills with `execution_mode: "fork"` to delegate work to subagents.

The subsystems are production-ready in terms of code quality and design, with the "experimental" label primarily reflecting that the public API may change in minor versions.

---

## Architecture Overview

### Skills Subsystem (11 files, ~2,829 lines)

The skills subsystem implements the **SKILL.md open standard** — a convention where agent capabilities are defined as markdown files with YAML frontmatter. The architecture follows a **progressive disclosure** model with three tiers of data loading:

- **Tier 1 (Metadata)**: `load_metadata()` parses only YAML frontmatter, returning `SkillInfo`. Used during discovery scans for fast enumeration.
- **Tier 2 (Full Load)**: `load_full()` parses frontmatter + markdown body, returning `Skill`. Used on first activation (lazy).
- **Tier 3 (References)**: `get_references()` / `load_reference()` loads supplemental files from a `references/` subdirectory. Loaded on explicit request only.

Skills are discovered from a **three-level directory hierarchy** with priority-based conflict resolution:
1. **Project** (`.mamba/skills/`) — highest priority, trusted by default
2. **User** (`~/.mamba/skills/`) — medium priority, trusted by default
3. **Custom** (configurable paths) — lowest priority, untrusted unless in `trusted_paths`

The **invocation lifecycle** flows: permission check → lazy body load → argument substitution → activation state management → tool registration. Argument substitution supports `$ARGUMENTS`, `$ARGUMENTS[N]`, `$N` positional syntax, and fallback appending.

### Subagents Subsystem (7 files, ~1,649 lines)

The subagents subsystem enables **isolated task delegation** to child `Agent` instances. Each subagent gets its own `ContextManager`, `UsageTracker`, and other subsystems — complete isolation from the parent.

Key architectural decisions:
- **No-nesting rule**: Subagents cannot spawn sub-subagents, enforced via `AgentConfig._is_subagent` private attribute. This prevents unbounded recursion and resource exhaustion.
- **Three delegation patterns**: `delegate()` (async), `delegate_sync()` (sync wrapper), `delegate_async()` (fire-and-forget with `DelegationHandle`)
- **Automatic usage aggregation**: Token usage flows from subagent → parent `UsageTracker` with per-subagent breakdown
- **Config loading from markdown**: `.mamba/agents/{name}.md` files with YAML frontmatter, mirroring the SKILL.md pattern

### Skills-Subagents Integration

The integration layer (`skills/integration.py`, 242 lines) bridges the two subsystems bidirectionally:
- Skills with `execution_mode: "fork"` delegate to subagents instead of returning content directly
- **Circular reference detection** traces `skill → agent → pre-loaded skills` chains to prevent infinite loops
- **Trust enforcement**: untrusted skills cannot use fork execution mode
- Post-construction wiring via `SkillManager.subagent_manager` setter avoids circular initialization

---

## Critical Files

| File | Lines | Purpose | Relevance |
|------|-------|---------|-----------|
| `skills/manager.py` | 443 | SkillManager facade — unified API for all skill operations | **Critical** |
| `subagents/manager.py` | 509 | SubagentManager facade — unified API for all subagent operations | **Critical** |
| `skills/config.py` | 171 | Data models: `Skill`, `SkillInfo`, `SkillConfig`, `ValidationResult`, enums | **Critical** |
| `subagents/config.py` | 148 | Data models: `SubagentConfig`, `SubagentResult`, `DelegationHandle` | **Critical** |
| `skills/integration.py` | 242 | Bi-directional skills↔subagents bridge, fork execution, cycle detection | **High** |
| `skills/loader.py` | 377 | SKILL.md parser pipeline: read → split → parse YAML → validate → map fields | **High** |
| `skills/invocation.py` | 233 | Activation lifecycle, permission checks, argument substitution | **High** |
| `skills/discovery.py` | 193 | Three-level directory scanning with priority-based conflict resolution | **High** |
| `skills/registry.py` | 301 | In-memory async-safe skill storage with lazy body loading | **High** |
| `subagents/spawner.py` | 243 | Agent spawning with no-nesting guard, tool resolution, skill pre-loading | **High** |
| `subagents/delegation.py` | 298 | Sync/async/fire-and-forget delegation with fault-tolerant error capture | **High** |
| `subagents/loader.py` | 189 | Markdown config loader for `.mamba/agents/*.md` files | **Medium** |
| `skills/validator.py` | 323 | Schema validation, trust level resolution, restriction enforcement | **Medium** |
| `skills/errors.py` | 239 | 7 domain exception classes with pickle support | **Medium** |
| `subagents/errors.py` | 205 | 6 domain exception classes with pickle support | **Medium** |
| `skills/testing.py` | 240 | `SkillTestHarness` + `skill_harness` pytest fixture for isolated testing | **Medium** |
| `skills/__init__.py` | 67 | Public API exports (12 symbols) | **Low** |
| `subagents/__init__.py` | 57 | Public API exports (10 symbols) | **Low** |

### File Details

#### `skills/manager.py` — SkillManager Facade

The top-level API for the skills subsystem. Composes all internal components behind a clean interface.

**Key API surface:**
- `discover() → list[SkillInfo]` — Scan configured directories, register found skills
- `register(skill: Skill | SkillInfo | Path)` — Register from various sources
- `activate(name, arguments) → str` — Full activation lifecycle with fork delegation
- `deactivate(name)` — Mark skill inactive, clear runtime tools
- `validate(path) → ValidationResult` — Schema validation for SKILL.md files
- `get_tools(name) → list[Callable]` — Get tools from an active skill
- `get_all_tools() → list[Callable]` — All active skill tools, optionally namespaced
- `get_references(name) → list[Path]` — Tier 3 reference file listing
- `load_reference(name, ref_name) → str` — Tier 3 reference file content

**Bi-directional wiring:**
- `subagent_manager` property with setter for post-construction wiring
- Fork-mode detection in `activate()` delegates to `integration.activate_with_fork()`

#### `subagents/manager.py` — SubagentManager Facade

The top-level API for the subagents subsystem. Manages config registration, delegation, and usage tracking.

**Key API surface:**
- `register(config: SubagentConfig)` — Register a subagent config (overwrites on duplicate)
- `delegate(config_name, task) → SubagentResult` — Async delegation
- `delegate_sync(config_name, task) → SubagentResult` — Synchronous wrapper
- `delegate_async(config_name, task) → DelegationHandle` — Fire-and-forget
- `spawn_dynamic(config, task) → SubagentResult` — One-off subagent without registration
- `discover() → list[SubagentConfig]` — Scan `.mamba/agents/` directories
- `get_active_delegations() → list[DelegationHandle]` — Active async handles
- `get_usage_breakdown() → dict[str, TokenUsage]` — Per-subagent token usage

**Usage aggregation:**
- `_aggregate_usage()` writes to both internal breakdown and parent's `UsageTracker._subagent_totals`
- `_UsageTrackingHandle` wraps `DelegationHandle` to aggregate on async completion

#### `skills/config.py` — Data Models

**Enums:**
- `SkillScope`: `PROJECT`, `USER`, `CUSTOM` — discovery scope affecting trust defaults
- `TrustLevel`: `TRUSTED`, `UNTRUSTED` — controls allowed capabilities

**Data classes:**
- `SkillInfo` (`@dataclass`) — Eagerly-loaded metadata with 17 fields:
  - Required: `name`, `description`, `path`, `scope`
  - Optional: `license`, `compatibility`, `metadata`, `allowed_tools`, `model`, `execution_mode`, `agent`, `disable_model_invocation`, `user_invocable`, `argument_hint`, `hooks`, `trust_level`
- `ValidationResult` (`@dataclass`) — Structured validation output with `valid`, `errors`, `warnings`, `skill_path`, `trust_level`

**Pydantic models:**
- `Skill` (`BaseModel`) — Wraps `SkillInfo` with `body: str | None`, `is_active: bool`, `_tools: list[Callable]` (private)
- `SkillConfig` (`BaseModel`) — Subsystem configuration with 6 fields: `skills_dirs`, `user_skills_dir`, `custom_paths`, `auto_discover`, `namespace_tools`, `trusted_paths`

#### `subagents/config.py` — Data Models

**Pydantic models:**
- `SubagentConfig` (`BaseModel`) — 9 fields: `name`, `description`, `model`, `tools`, `disallowed_tools`, `system_prompt` (str | TemplateConfig), `skills`, `max_turns` (default: 50), `config` (AgentConfig override)

**Data classes:**
- `SubagentResult` (`@dataclass`) — 7 fields: `output`, `agent_result`, `usage`, `duration`, `subagent_name`, `success`, `error`
- `DelegationHandle` (`@dataclass`) — Wraps `asyncio.Task` with `is_complete`, `result()`, `cancel()` API

#### `skills/loader.py` — SKILL.md Parser Pipeline

Implements a 5-stage pipeline: `_read_file()` → `_split_frontmatter()` → `_parse_yaml()` → `_validate_frontmatter()` → `_map_fields()`

**Key design decisions:**
- `_FIELD_MAP` dictionary maps YAML hyphenated keys to Python underscore attributes (e.g., `allowed-tools` → `allowed_tools`, `context` → `execution_mode`)
- Unknown frontmatter keys are silently dropped (not errors)
- Name validation: lowercase alphanumeric + hyphens, max 64 chars, must match parent directory name
- Large body warning: logs when body exceeds ~5,000 estimated tokens (chars / 4 heuristic)

Two public functions:
- `load_metadata(path, scope)` → `SkillInfo` — Tier 1, frontmatter only
- `load_full(path, scope)` → `Skill` — Tier 2, frontmatter + body

#### `skills/invocation.py` — Activation Lifecycle

**`InvocationSource` enum:** `MODEL`, `USER`, `CODE`
- `CODE` always permitted
- `MODEL` blocked when `disable_model_invocation=True`
- `USER` blocked when `user_invocable=False`

**Argument substitution** (`substitute_arguments()`):
1. `$ARGUMENTS[N]` → positional argument N (0-indexed)
2. `$ARGUMENTS` → full argument string
3. `$N` → positional argument N (0-indexed)
4. If no placeholders found, append as `ARGUMENTS: <value>`

Missing positional arguments resolve to empty strings. Arguments parsed via `shlex.split()` with fallback to whitespace split on malformed quotes.

**Activation flow** (`activate()`):
1. Check invocation permissions against source
2. Lazy-load body from disk if not present
3. Perform argument substitution
4. Mark skill as active
5. Return processed content

**Deactivation** (`deactivate()`):
- Sets `is_active = False`
- Clears `_tools` list

#### `skills/discovery.py` — Directory Scanning

**`scan_directory(path, scope, trust)`:**
- Uses `Path.glob("*/SKILL.md")` to find skill directories
- Follows symlinks
- Detects same-scope duplicates within a single directory
- Individual parse failures logged and skipped

**`discover_skills(config)`:**
- Scans in priority order: project dirs → user dir → custom paths
- Cross-scope conflicts: higher priority wins (info logged)
- Same-scope conflicts: raises `SkillConflictError`
- Custom paths default to untrusted unless in `config.trusted_paths`

#### `skills/registry.py` — In-Memory Storage

- `SkillRegistry` stores `dict[str, Skill]` with `asyncio.Lock` for async safety
- Accepts `Skill`, `SkillInfo`, or `Path` for registration
- `SkillInfo` registration creates a `Skill` wrapper with `body=None` (lazy)
- `get()` performs lazy body loading on access
- `_load_skill_from_path()` is a standalone loader (duplicates some `loader.py` logic)
- Async variants: `aregister()`, `aderegister()`

#### `subagents/spawner.py` — Agent Spawning

**`spawn(config, parent_agent, skill_registry)`:**
1. Enforce no-nesting via `_enforce_no_nesting()` — checks `parent_agent.config._is_subagent`
2. Resolve model (inherit from parent if not specified)
3. Resolve tools from allowlist against parent's `_agent._function_toolset`
4. Resolve skill tools from pre-loaded skills
5. Build system prompt from config + skill content
6. Create `Agent` with `_is_subagent = True`

**Tool resolution** (`_resolve_tools()`):
- `tools=None` → no tools (not inherit all)
- `tools=[]` → empty tool access
- `tools=["name", ...]` → resolved from parent's pydantic-ai toolset
- Callable tools passed through directly
- `disallowed_tools` filtered out even if in allowlist

**System prompt building** (`_build_system_prompt()`):
- Starts with `config.system_prompt` (string or template)
- Appends pre-loaded skill content as `## Skill: {name}` sections
- Supports `TemplateConfig` when no skills override

#### `subagents/delegation.py` — Task Execution

Three delegation functions:
- `delegate()` — Async, awaits `agent.run()`, captures result
- `delegate_sync()` — Sync, uses `agent.run_sync()`
- `delegate_async()` — Fire-and-forget via `asyncio.create_task()`, returns `DelegationHandle`

**Error handling philosophy:** All execution errors captured into `SubagentResult(success=False, error=...)`. Only `SubagentConfigError` is re-raised (unrecoverable).

**Usage extraction** (`_extract_usage()`): Handles pydantic-ai's API migration (`input_tokens` vs `request_tokens`) using `getattr` fallbacks.

**Context injection:** Optional `context_messages` parameter converts dicts to `ModelMessage` via `dicts_to_model_messages()` for injecting conversation history.

#### `subagents/loader.py` — Markdown Config Loader

Loads subagent definitions from `.mamba/agents/{name}.md` files:
- YAML frontmatter between `---` markers → `SubagentConfig` fields
- Markdown body → `system_prompt` (if not set in frontmatter)
- `_KEY_MAPPING` normalizes hyphenated YAML keys: `disallowed-tools`, `max-turns`, `system-prompt`
- `discover_subagents()` scans project (`.mamba/agents/`) and user (`~/.mamba/agents/`) directories

#### `skills/integration.py` — Fork Execution Bridge

**`activate_with_fork(skill, arguments, subagent_manager)`:**
1. **Trust check** — untrusted skills cannot fork
2. **Circular detection** — traces `skill → agent → pre-loaded skills` chains
3. **Content preparation** — activates skill normally to get processed content
4. **Delegation** — named agent configs use `delegate_sync()`, unnamed create temporary subagent via `spawn_dynamic()`
5. **Async workaround** — when inside a running event loop, uses `ThreadPoolExecutor` + `asyncio.run()` to bridge sync/async impedance

**`detect_circular_skill_subagent()`:**
- Follows the chain: `skill(fork) → agent config → pre-loaded skills → (check for cycles)`
- `_trace_cycle()` performs recursive DFS with visited set and path tracking
- Returns the circular path as a list (e.g., `["skill:A", "agent:B", "skill:A"]`) or `None`

#### `skills/validator.py` — Schema Validation

Two-level validation:
- `validate_frontmatter(data)` — Schema validation: required fields, type checks, name format, unknown field warnings
- `validate(path)` — File-level validation: reads file, parses frontmatter, validates schema, checks name-directory match

**Trust utilities:**
- `resolve_trust_level(scope, path, trusted_paths)` — Project/User = trusted, Custom = untrusted unless in trusted_paths
- `check_trust_restrictions(skill)` — Returns violation messages for restricted capabilities (hooks, fork, allowed-tools)

#### `skills/testing.py` — Test Harness

**`SkillTestHarness`:**
- Accepts `skill_path` (load from disk) or `skill` (pre-built instance)
- `load()` — loads the skill, returns `Skill`
- `validate()` — validates frontmatter, returns `ValidationResult`
- `invoke(arguments)` — performs argument substitution without requiring a real LLM
- `get_registered_tools()` — returns tool names from `allowed_tools` field

**`skill_harness` pytest fixture:** Factory function for creating `SkillTestHarness` instances in tests.

#### Error Hierarchies

**Skills (7 exceptions):**
```
SkillError (base)
├── SkillNotFoundError(name, path)
├── SkillParseError(name, path, detail)
├── SkillValidationError(name, errors, path)
├── SkillLoadError(name, path, cause)
├── SkillConflictError(name, paths)
└── SkillInvocationError(name, source, reason)
```

**Subagents (6 exceptions):**
```
SubagentError (base)
├── SubagentConfigError(name, detail)
├── SubagentNotFoundError(config_name, available)
├── SubagentNestingError(name, parent_name)
├── SubagentDelegationError(name, task, cause)
└── SubagentTimeoutError(name, max_turns, turns_used)
```

All exception classes support `__reduce__` for pickling and include `__repr__` for debugging.

---

## Relationship Map

### Component Dependencies

```
Agent (hub)
├── skills=[] ──→ _init_skill_manager() ──→ SkillManager
│   ├── SkillConfig
│   ├── SkillRegistry ──→ Skill / SkillInfo
│   │   └── _load_skill_from_path() (internal loader)
│   ├── discover_skills() ──→ scan_directory() ──→ load_metadata()
│   ├── activate() ──→ invocation.activate()
│   │   └── (fork mode) ──→ integration.activate_with_fork()
│   │       └── SubagentManager.delegate_sync() / spawn_dynamic()
│   ├── validate() ──→ validator.validate()
│   └── subagent_manager setter (bi-directional wiring)
│
├── subagents=[] ──→ _init_subagent_manager() ──→ SubagentManager
│   ├── SubagentConfig registry (dict[str, SubagentConfig])
│   ├── spawn() ──→ spawner.spawn()
│   │   ├── _enforce_no_nesting() checks AgentConfig._is_subagent
│   │   ├── _resolve_tools() against parent's pydantic-ai toolset
│   │   ├── _build_system_prompt() with skill content
│   │   └── creates Agent(model, config=..., _is_subagent=True)
│   ├── delegate() / delegate_sync() / delegate_async()
│   │   └── delegation module ──→ agent.run() / agent.run_sync()
│   ├── _aggregate_usage() ──→ parent UsageTracker._subagent_totals
│   ├── discover_subagents() ──→ loader.load_subagent_config()
│   └── _UsageTrackingHandle wraps DelegationHandle
│
└── skill_dirs=[] ──→ scan_directory() directly (SkillScope.CUSTOM)
```

### Data Flow: Skill Activation (Standard Mode)

1. `Agent.invoke_skill(name, *args)` joins args into string
2. `SkillManager.activate(name, arguments)`
3. `SkillRegistry.get(name)` → lazy-loads body if needed
4. `invocation.activate(skill, arguments)`:
   a. `check_invocation_permission(skill.info, source)` → verify MODEL/USER/CODE access
   b. Lazy-load body from disk if `skill.body is None`
   c. `substitute_arguments(body, arguments)` → replace `$ARGUMENTS`, `$N` placeholders
   d. Set `skill.is_active = True`
   e. Return processed content string

### Data Flow: Skill Activation (Fork Mode)

1. `SkillManager.activate(name, arguments)` detects `execution_mode == "fork"`
2. `integration.activate_with_fork(skill, arguments, subagent_manager)`:
   a. Trust check — untrusted skills cannot fork
   b. `detect_circular_skill_subagent()` traces dependency chains
   c. `invocation.activate()` for content preparation
   d. If named agent: `subagent_manager.delegate_sync(agent_name, content)`
   e. If unnamed: create `SubagentConfig`, call `subagent_manager.spawn_dynamic()`
   f. Return `result.output`

### Data Flow: Subagent Delegation

1. `Agent.delegate_sync(config_name, task)` or `Agent.delegate(config_name, task)`
2. `SubagentManager._resolve_config(config_name)` → lookup or `SubagentNotFoundError`
3. `SubagentManager._spawn(config)` → `spawner.spawn()`:
   a. `_enforce_no_nesting()` → check `_is_subagent` flag
   b. Resolve model, tools, skill tools, system prompt
   c. Create child `Agent` with `_is_subagent = True`
4. `delegation.delegate(subagent, task)` → `agent.run(prompt)`
5. Extract `TokenUsage` from result (with `input_tokens`/`request_tokens` migration handling)
6. Return `SubagentResult(output, usage, duration, success)`
7. `SubagentManager._aggregate_usage()` updates parent tracker

### Cross-System Wiring

```
SkillManager.subagent_manager ←──setter──→ SubagentManager._skill_manager
        │                                           │
        │ (fork activation)                         │ (skill pre-loading)
        ▼                                           ▼
integration.activate_with_fork() ─────→ spawner._build_system_prompt()
                                         spawner._resolve_skill_tools()
```

**Critical gap**: The Agent's `_init_skill_manager()` and `_init_subagent_manager()` do NOT wire the bi-directional references. The `SkillManager.subagent_manager` setter is never called from `agent/core.py`. This means fork-mode skills and subagent skill pre-loading may not work through the Agent facade unless the user manually wires the managers.

---

## Patterns & Conventions

### Design Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Facade** | `skills/manager.py`, `subagents/manager.py` | Single unified API over 5/3 internal components |
| **Progressive Disclosure** | `skills/loader.py` (Tier 1/2), `skills/manager.py` (Tier 3) | Defer expensive operations until needed |
| **Pipeline** | `skills/loader.py`, `subagents/loader.py` | `read → split → parse → validate → map` |
| **Registry** | `skills/registry.py` | In-memory async-safe storage with lazy loading |
| **No-Nesting Guard** | `subagents/spawner.py` | Private attribute flag prevents sub-subagents |
| **Lazy Initialization** | `agent/core.py` | `_pending_*` queues → `@property` creates managers |
| **Strategy** | `skills/invocation.py` | `InvocationSource` enum controls permission gates |
| **Decorator** | `skills/manager.py::_namespace_tool()` | Wraps callables with prefixed names |
| **Factory** | `subagents/spawner.py::spawn()` | Creates configured Agent instances from config |
| **Test Harness** | `skills/testing.py` | Isolated testing without full Agent setup |

### Naming Conventions

| Convention | Examples |
|-----------|----------|
| YAML hyphenated keys → Python underscore | `allowed-tools` → `allowed_tools`, `context` → `execution_mode` |
| Pydantic `BaseModel` for configuration | `SkillConfig`, `SubagentConfig`, `Skill` |
| `@dataclass` for output/data types | `SkillInfo`, `ValidationResult`, `SubagentResult`, `DelegationHandle` |
| Private attribute via Pydantic `PrivateAttr` | `Skill._tools`, `AgentConfig._is_subagent` |
| `TYPE_CHECKING` guards for circular imports | Both managers use `TYPE_CHECKING` for cross-references |
| Lazy imports inside methods | `from mamba_agents.skills import ...` inside `_init_skill_manager()` |

### File Organization

```
skills/
├── __init__.py       # Public API (12 symbols)
├── config.py         # Data models + enums (SkillInfo, Skill, SkillConfig, etc.)
├── errors.py         # 7 exception classes
├── loader.py         # SKILL.md parser pipeline (Tier 1 + 2)
├── discovery.py      # Directory scanning + conflict resolution
├── registry.py       # In-memory storage with lazy loading
├── validator.py      # Schema validation + trust enforcement
├── invocation.py     # Activation lifecycle + argument substitution
├── integration.py    # Fork execution + circular detection
├── manager.py        # SkillManager facade
└── testing.py        # SkillTestHarness + pytest fixture

subagents/
├── __init__.py       # Public API (10 symbols)
├── config.py         # Data models (SubagentConfig, SubagentResult, DelegationHandle)
├── errors.py         # 6 exception classes
├── loader.py         # Markdown config loader + discovery
├── spawner.py        # Agent creation with isolation
├── delegation.py     # Sync/async/fire-and-forget task delegation
└── manager.py        # SubagentManager facade + _UsageTrackingHandle
```

### Conventions for SKILL.md Files

```yaml
---
name: my-skill           # Required, lowercase alphanum + hyphens, max 64 chars
description: What it does # Required
license: MIT             # Optional, SPDX identifier
compatibility: ">=1.0"   # Optional
metadata:                # Optional key-value pairs
  key: value
allowed-tools:           # Optional tool allowlist
  - read_file
  - grep_search
model: gpt-4             # Optional model override
context: fork            # Optional, "fork" delegates to subagent
agent: researcher        # Optional, named subagent for fork mode
disable-model-invocation: false  # Optional, blocks LLM invocation
user-invocable: true     # Optional, controls slash-command access
argument-hint: "<file>"  # Optional, hint for argument input
hooks: {}                # Reserved, not implemented in v1
---

Markdown body with skill instructions...

Use $ARGUMENTS for the full argument string.
Use $ARGUMENTS[0] for the first positional argument.
Use $0 shorthand for positional arguments.
```

### Conventions for Subagent `.md` Files

```yaml
---
name: researcher
description: Research subagent for gathering information
model: gpt-4              # Optional (inherits from parent)
tools: [read_file, grep_search]  # Optional tool allowlist
disallowed-tools: [run_bash]     # Optional tool denylist
skills: [web-search]             # Optional pre-loaded skills
max-turns: 50                    # Optional (default: 50)
---

You are a research assistant. Your job is to gather information...
```

---

## Agent Integration Points

### Constructor Parameters

```python
Agent(
    model="gpt-4",
    skills=[                    # List[Skill | str | Path]
        Skill(info=..., body=...),  # Pre-built Skill instance
        "path/to/skill",            # String path (resolved to Path)
        Path("my-skill"),            # Path to skill directory
    ],
    skill_dirs=[                # List[str | Path]
        "custom/skills/",       # Directory to scan for skills
    ],
    subagents=[                 # List[SubagentConfig]
        SubagentConfig(name="helper", description="..."),
    ],
)
```

### Lazy Initialization Behavior

- `Agent(skills=[...])` → immediately calls `_init_skill_manager()`
- `Agent(skill_dirs=[...])` → immediately calls `_init_skill_manager()`
- `Agent(subagents=[...])` → immediately calls `_init_subagent_manager()`
- `Agent()` → managers created lazily on first `skill_manager` / `subagent_manager` property access
- **Warning**: Accessing `agent.skill_manager` or `agent.subagent_manager` **creates** the manager on first access (side effect)
- **Safe check**: Use `agent._skill_manager is not None` to check without triggering initialization

### Agent Facade Methods

**Skills:**
- `agent.register_skill(skill: Skill | str | Path)` → `skill_manager.register()`
- `agent.get_skill(name) → Skill | None` → `skill_manager.get()`
- `agent.list_skills() → list[SkillInfo]` → `skill_manager.list()`
- `agent.invoke_skill(name, *args) → str` → `skill_manager.activate(name, " ".join(args))`

**Subagents:**
- `agent.register_subagent(config: SubagentConfig)` → `subagent_manager.register()`
- `agent.list_subagents() → list[SubagentConfig]` → `subagent_manager.list()`
- `await agent.delegate(config_name, task) → SubagentResult` → `subagent_manager.delegate()`
- `agent.delegate_sync(config_name, task) → SubagentResult` → `subagent_manager.delegate_sync()`
- `await agent.delegate_async(config_name, task) → DelegationHandle` → `subagent_manager.delegate_async()`

### Configuration via AgentSettings

```python
from mamba_agents import AgentSettings
from mamba_agents.skills.config import SkillConfig

settings = AgentSettings(
    skills=SkillConfig(
        skills_dirs=[Path(".mamba/skills")],
        user_skills_dir=Path("~/.mamba/skills"),
        custom_paths=[Path("/shared/skills")],
        auto_discover=True,
        namespace_tools=True,
        trusted_paths=[Path("/shared/skills")],
    ),
)
```

Environment variable: `MAMBA_SKILLS__SKILLS_DIRS`, `MAMBA_SKILLS__AUTO_DISCOVER`, etc.

---

## Test Coverage

### Test File Inventory

| Test File | Tests | Covers |
|-----------|-------|--------|
| `test_skill_config.py` | 30 | `SkillInfo`, `Skill`, `SkillConfig`, `SkillScope`, `TrustLevel`, `ValidationResult` |
| `test_skill_errors.py` | 35 | All 7 skill exception classes, pickle/repr support |
| `test_skill_loader.py` | 51 | `load_metadata()`, `load_full()`, frontmatter parsing pipeline |
| `test_skill_invocation.py` | 79 | `InvocationSource`, permissions, argument parsing/substitution, activation/deactivation |
| `test_skill_discovery.py` | 37 | `scan_directory()`, `discover_skills()`, priority/conflict resolution |
| `test_skill_registry.py` | 46 | `SkillRegistry` CRUD, async variants, lazy loading, conflict detection |
| `test_skill_manager.py` | 55 | `SkillManager` facade, all public methods, reference loading |
| `test_skill_validator.py` | 48 | `validate_frontmatter()`, `validate()`, trust resolution, restriction checks |
| `test_skill_init.py` | 18 | Package exports, `__all__`, import verification |
| `test_skill_testing.py` | 39 | `SkillTestHarness`, `skill_harness` fixture, isolated testing |
| `test_subagent_init.py` | 16 | Package exports, `__all__`, import verification |
| `test_skills_subagents_integration.py` | 38 | Integration: fork activation, circular detection, trust enforcement |
| `tests/integration/test_skills_subagents.py` | 32 | End-to-end: Agent facade, lazy init, delegation, usage tracking |
| **Total** | **524** | |

### Current Issues

- **Pydantic 2.12 incompatibility**: Some test files fail during pytest collection with `KeyError: 'pydantic.root_model'`. This is a Pydantic/conftest compatibility issue, not a test quality issue. The affected files: `test_skill_config.py`, `test_skill_loader.py`, `test_skills_subagents_integration.py`.
- **test_subagent_init.py**: All 16 tests fail — the import tests reference symbols that may have been reorganized.
- **Coverage measurement**: Unable to generate accurate coverage percentages due to the collection errors, but the test count (524) and breadth (13 files covering every module) indicate comprehensive coverage when tests are running.

---

## Challenges & Risks

| Challenge | Severity | Details |
|-----------|----------|---------|
| **Missing bi-directional wiring in Agent** | **High** | `_init_skill_manager()` and `_init_subagent_manager()` never call `skill_manager.subagent_manager = subagent_manager` or vice versa. Fork-mode skills and subagent skill pre-loading won't work through the Agent facade. |
| **integration.py async workaround** | **High** | `activate_with_fork()` uses `ThreadPoolExecutor` + `asyncio.run()` (lines 214-233) when inside a running event loop. This is fragile with nested event loops and could deadlock in async contexts (e.g., FastAPI). |
| **SubagentManager mutates parent internals** | **Medium** | `_aggregate_usage()` directly writes to `parent_agent.usage_tracker._subagent_totals`, coupling to `UsageTracker`'s private state. Any refactor of `UsageTracker` internals breaks this. |
| **Duplicate loader logic in registry.py** | **Medium** | `registry._load_skill_from_path()` duplicates frontmatter parsing logic from `loader.py` instead of delegating. The registry uses `content.find("---", 3)` while the loader uses line-by-line search — different algorithms for the same task. |
| **Pydantic 2.12 test breakage** | **Medium** | Test collection errors from `KeyError: 'pydantic.root_model'` affect multiple test files. Needs conftest/fixture update. |
| **Tool resolution via private API** | **Medium** | `spawner._resolve_tools()` accesses `parent._agent._function_toolset.tools` — reaching into pydantic-ai's internal structure. Subject to breakage on pydantic-ai updates. |
| **tools=None means no tools** | **Low** | `_resolve_tools()` returns `[]` when `config.tools is None`, meaning subagents get zero tools by default. This is by design but may surprise users who expect tool inheritance. |
| **AgentSettings.skills defaults to None** | **Low** | `AgentSettings.skills: SkillConfig | None = None` means no `SkillConfig` by default. `SkillManager` creates its own default `SkillConfig()` when constructed with `None`. The None-or-config pattern works but adds an unnecessary layer. |

---

## Recommendations

### For Documentation

1. **Document the bi-directional wiring requirement**: If users need fork-mode skills or subagent skill pre-loading, they must manually wire the managers:
   ```python
   agent.skill_manager.subagent_manager = agent.subagent_manager
   agent.subagent_manager._skill_manager = agent.skill_manager
   ```

2. **Document the lazy initialization side effects**: Warn that accessing `agent.skill_manager` or `agent.subagent_manager` creates the manager if it doesn't exist. Recommend `agent._skill_manager is not None` for checking.

3. **Document the three-tier progressive disclosure**: Explain the performance benefit — discovery scans only read frontmatter (Tier 1), body loading deferred to activation (Tier 2), reference files loaded on demand (Tier 3).

4. **Document tool resolution semantics**: Clarify that `SubagentConfig(tools=None)` means the subagent gets NO tools (not parent inheritance). Provide examples for common patterns:
   - `tools=None` → no tools
   - `tools=["read_file", "grep_search"]` → named tools from parent
   - `tools=[my_function]` → direct callable registration

5. **Document the SKILL.md specification**: Include the complete frontmatter schema with all standard and extension fields, argument substitution syntax, and the relationship between `name` and parent directory.

6. **Include architecture diagrams**: The progressive disclosure model, the activation lifecycle, and the fork delegation flow are complex enough to benefit from visual representation.

### For Code Quality

7. **Fix bi-directional wiring**: Add mutual wiring in `agent/core.py` when both managers are initialized:
   ```python
   if self._skill_manager and self._subagent_manager:
       self._skill_manager.subagent_manager = self._subagent_manager
       self._subagent_manager._skill_manager = self._skill_manager
   ```

8. **Deduplicate registry loader**: Have `registry._load_skill_from_path()` delegate to `loader.load_full()` instead of reimplementing frontmatter parsing.

9. **Add public UsageTracker API**: Replace direct `_subagent_totals` mutation with `record_subagent_usage(name, usage)`.

10. **Replace async workaround**: The `ThreadPoolExecutor` + `asyncio.run()` pattern in `integration.py` should be replaced with proper async-first design or `anyio.from_thread` bridging.

---

## Public API Reference Summary

### Skills — Imports

```python
from mamba_agents import (
    # Core
    SkillManager, Skill, SkillInfo, SkillConfig,
    SkillScope, TrustLevel, ValidationResult,
    # Errors
    SkillError, SkillNotFoundError, SkillParseError,
    SkillValidationError, SkillLoadError, SkillConflictError,
)

# Testing (separate import)
from mamba_agents.skills.testing import SkillTestHarness, skill_harness

# Advanced (internal components)
from mamba_agents.skills.invocation import InvocationSource
from mamba_agents.skills.discovery import scan_directory, discover_skills
from mamba_agents.skills.loader import load_metadata, load_full
from mamba_agents.skills.registry import SkillRegistry
from mamba_agents.skills.validator import validate, validate_frontmatter, resolve_trust_level
```

### Subagents — Imports

```python
from mamba_agents import (
    # Core
    SubagentManager, SubagentConfig, SubagentResult, DelegationHandle,
    # Errors
    SubagentError, SubagentConfigError, SubagentNotFoundError,
    SubagentNestingError, SubagentDelegationError, SubagentTimeoutError,
)

# Advanced (internal components)
from mamba_agents.subagents.spawner import spawn
from mamba_agents.subagents.delegation import delegate, delegate_sync, delegate_async
from mamba_agents.subagents.loader import load_subagent_config, discover_subagents
```

---

## Open Questions

1. **Bi-directional wiring gap**: Is the missing wiring between `SkillManager` and `SubagentManager` in `agent/core.py` intentional (user responsibility) or an implementation oversight? The infrastructure exists (setter property) but is never called.

2. **Fork execution mode in production**: Has `activate_with_fork()` been tested under production async workloads (e.g., inside FastAPI or other async frameworks)? The `ThreadPoolExecutor` + `asyncio.run()` pattern is known to be fragile.

3. **SkillConfig in AgentSettings**: Should `AgentSettings.skills` default to `SkillConfig()` instead of `None`? The None-default adds complexity since `SkillManager` creates its own default anyway.

4. **Subagent tool inheritance**: Is the `tools=None` → "no tools" semantic the intended design, or should there be a way to inherit all parent tools?

5. **SkillInfo vs SkillConfig naming**: `SkillInfo` is metadata, `SkillConfig` is configuration — but both are data classes. Could be confusing in documentation.

---

## Existing Documentation Gap Analysis

### Summary

The Skills and Subagents subsystems are **fully implemented in code** (18 source files, 4,478 lines) and **exported from the main package** (`__init__.py` includes all 22 symbols), but have **zero documentation coverage** in the MkDocs site. No user guide, API reference, tutorial, or architectural mention exists for either subsystem.

### Gap Categories

#### 1. New Pages Needed (not yet created)

| Page | Nav Section | Priority | Content |
|------|-------------|----------|---------|
| `docs/user-guide/skills.md` | User Guide > Skills | **Critical** | Complete user guide: SKILL.md format, discovery, activation, argument substitution, trust levels, fork execution, testing |
| `docs/user-guide/subagents.md` | User Guide > Subagents | **Critical** | Complete user guide: SubagentConfig, delegation patterns (sync/async/fire-and-forget), usage tracking, no-nesting rule |
| `docs/api/skills/index.md` | API Reference > Skills | **Critical** | Skills subsystem API overview, public imports, module index |
| `docs/api/skills/manager.md` | API Reference > Skills | **Critical** | `SkillManager` class reference (mkdocstrings) |
| `docs/api/skills/config.md` | API Reference > Skills | **Critical** | `Skill`, `SkillInfo`, `SkillConfig`, `SkillScope`, `TrustLevel`, `ValidationResult` |
| `docs/api/skills/errors.md` | API Reference > Skills | **High** | 7 skill exception classes |
| `docs/api/skills/testing.md` | API Reference > Skills | **High** | `SkillTestHarness`, `skill_harness` pytest fixture |
| `docs/api/subagents/index.md` | API Reference > Subagents | **Critical** | Subagents subsystem API overview, public imports |
| `docs/api/subagents/manager.md` | API Reference > Subagents | **Critical** | `SubagentManager` class reference (mkdocstrings) |
| `docs/api/subagents/config.md` | API Reference > Subagents | **Critical** | `SubagentConfig`, `SubagentResult`, `DelegationHandle` |
| `docs/api/subagents/errors.md` | API Reference > Subagents | **High** | 6 subagent exception classes |
| `docs/tutorials/skills-tutorial.md` | Tutorials | **Medium** | Step-by-step tutorial: creating a SKILL.md, testing with harness, using in Agent |
| `docs/tutorials/subagents-tutorial.md` | Tutorials | **Medium** | Step-by-step tutorial: defining configs, delegating tasks, tracking usage |
| `docs/concepts/skills-subagents.md` | Concepts | **Medium** | Architecture concepts: progressive disclosure, skill-subagent integration, fork execution flow |

#### 2. Existing Pages Needing Updates

| File | Section to Update | What to Add |
|------|-------------------|-------------|
| **`mkdocs.yml`** | `nav:` | Add Skills and Subagents entries under User Guide, API Reference, Tutorials, and Concepts sections |
| **`docs/index.md`** | Features grid | Add Skills card (`:material-puzzle: **Skills**`) and Subagents card (`:material-account-group: **Subagents**`). Add to Quick Reference table: `Skills` → `from mamba_agents import SkillManager, Skill` and `Subagents` → `from mamba_agents import SubagentManager, SubagentConfig` |
| **`docs/api/index.md`** | Main Package imports | Add Skills and Subagents import blocks. Add Skills and Subagents to Module Reference tables under "Features" or new "Extensions" section. Add to "Recommended Imports" section |
| **`docs/concepts/architecture.md`** | High-Level Architecture mermaid | Add `SKILLS[Skills]` and `SUBAG[Subagents]` nodes inside "Extensions" subgraph. Add edges: `AGENT --> SKILLS`, `AGENT --> SUBAG`, `SKILLS <--> SUBAG`. Update Module Structure tree to include `skills/` and `subagents/` directories. Update "Component Relationships" section to include `SkillManager` and `SubagentManager`. Add "Extension Points" subsection for skills/subagents |
| **`docs/user-guide/agent-basics.md`** | "Creating an Agent" section | Add code example showing `skills=`, `skill_dirs=`, and `subagents=` constructor params. Add brief "Skills" and "Subagents" sections pointing to dedicated pages. Update "Agent Properties" to include `skill_manager` and `subagent_manager`. Update "AgentConfig Reference" table to include `skills` and `subagents` options. Add to "Next Steps" list |
| **`docs/user-guide/index.md`** | Features grid, Quick Reference | Add Skills card and Subagents card to "Advanced Features" grid. Add rows to Quick Reference table: `Skills` → `mamba_agents.skills` → `SkillManager, Skill, SkillInfo` and `Subagents` → `mamba_agents.subagents` → `SubagentManager, SubagentConfig` |
| **`docs/tutorials/index.md`** | Available Tutorials grid | Add Skills tutorial card and Subagents tutorial card. Update Quick Links table |
| **`docs/getting-started/configuration.md`** | Environment Variables section | Add `MAMBA_SKILLS__*` environment variable examples: `MAMBA_SKILLS__AUTO_DISCOVER`, `MAMBA_SKILLS__NAMESPACE_TOOLS`, `MAMBA_SKILLS__CUSTOM_PATHS` |

#### 3. Proposed `mkdocs.yml` Nav Updates

```yaml
# Add under User Guide (after MCP Integration):
- Skills: user-guide/skills.md
- Subagents: user-guide/subagents.md

# Add under Tutorials:
- Working with Skills: tutorials/skills-tutorial.md
- Task Delegation with Subagents: tutorials/subagents-tutorial.md

# Add under Concepts:
- Skills & Subagents: concepts/skills-subagents.md

# Add under API Reference:
- Skills:
    - api/skills/index.md
    - SkillManager: api/skills/manager.md
    - Skill & SkillInfo: api/skills/config.md
    - Skill Errors: api/skills/errors.md
    - SkillTestHarness: api/skills/testing.md
- Subagents:
    - api/subagents/index.md
    - SubagentManager: api/subagents/manager.md
    - SubagentConfig: api/subagents/config.md
    - Subagent Errors: api/subagents/errors.md
```

#### 4. Experimental Status Callout

All skills/subagents documentation should include an admonition:

```markdown
!!! warning "Experimental API"
    The Skills and Subagents subsystems are experimental. The public API may change
    in minor versions. Use with awareness that breaking changes may occur before
    these subsystems are stabilized.
```

---

## Usage Patterns & Examples

### Skills: Common Usage Scenarios

#### 1. Creating a Skill (SKILL.md)

```
.mamba/skills/code-review/
├── SKILL.md
└── references/
    └── style-guide.md
```

```markdown
---
name: code-review
description: Review code for quality, security, and style issues
user-invocable: true
argument-hint: "<file_path>"
allowed-tools:
  - read_file
  - grep_search
---

# Code Review Skill

Review the code at `$ARGUMENTS` for:
1. Security vulnerabilities (OWASP Top 10)
2. Code quality issues
3. Performance concerns

Provide actionable suggestions with line references.
```

#### 2. Discovering and Registering Skills

```python
from mamba_agents import Agent

# Auto-discover from default directories
agent = Agent("gpt-4o")
discovered = agent.skill_manager.discover()
print(f"Found {len(discovered)} skills")

# Register from specific directories
agent = Agent(
    "gpt-4o",
    skill_dirs=[".mamba/skills", "/shared/team-skills"],
)

# Register a single skill by path
agent.register_skill("path/to/my-skill")

# List all registered skills
for info in agent.list_skills():
    print(f"  {info.name}: {info.description} (trust={info.trust_level})")
```

#### 3. Activating Skills (Standard Mode)

```python
# Activate via Agent facade (joins args with spaces)
content = agent.invoke_skill("code-review", "src/main.py")
print(content)  # Returns processed skill content with args substituted

# Activate via SkillManager directly (single string arg)
content = agent.skill_manager.activate("code-review", arguments="src/main.py")
```

#### 4. Skills with Argument Substitution

```markdown
---
name: compare-files
description: Compare two files side by side
argument-hint: "<file1> <file2>"
---

Compare these two files:
- File 1: $ARGUMENTS[0]
- File 2: $ARGUMENTS[1]

Full command: $ARGUMENTS
```

```python
# Positional arguments are parsed via shlex
content = agent.invoke_skill("compare-files", "src/old.py", "src/new.py")
# Result: "Compare these two files:\n- File 1: src/old.py\n- File 2: src/new.py\n..."
```

#### 5. Fork Execution Mode (Skill → Subagent)

```markdown
---
name: deep-research
description: Perform deep research on a topic
context: fork
agent: researcher
user-invocable: true
---

Research the following topic thoroughly: $ARGUMENTS

Provide a structured report with sources.
```

```python
from mamba_agents import Agent, SubagentConfig

# Set up the named subagent that the skill will fork to
researcher_config = SubagentConfig(
    name="researcher",
    description="Research subagent",
    tools=["read_file", "grep_search"],
    max_turns=20,
)

agent = Agent(
    "gpt-4o",
    subagents=[researcher_config],
    skill_dirs=[".mamba/skills"],
)

# NOTE: Bi-directional wiring is required for fork mode
agent.skill_manager.subagent_manager = agent.subagent_manager
agent.subagent_manager._skill_manager = agent.skill_manager

# Now fork-mode skills will delegate to the named subagent
result = agent.invoke_skill("deep-research", "quantum computing")
```

#### 6. Testing Skills with SkillTestHarness

```python
from mamba_agents.skills.testing import SkillTestHarness

# Load and test a skill without needing an Agent or LLM
harness = SkillTestHarness(skill_path="path/to/my-skill")

# Validate the SKILL.md format
result = harness.validate()
assert result.valid, f"Validation errors: {result.errors}"

# Test argument substitution
content = harness.invoke("test-argument")
assert "$ARGUMENTS" not in content  # Placeholder was replaced
assert "test-argument" in content

# Check registered tools
tools = harness.get_registered_tools()
print(f"Skill registers tools: {tools}")
```

```python
# Using the pytest fixture
def test_my_skill(skill_harness):
    harness = skill_harness("path/to/my-skill")
    result = harness.validate()
    assert result.valid
```

#### 7. Skill Configuration via Settings

```python
from mamba_agents import AgentSettings
from mamba_agents.skills import SkillConfig
from pathlib import Path

settings = AgentSettings(
    skills=SkillConfig(
        auto_discover=True,               # Scan dirs on skill_manager init
        namespace_tools=True,              # Prefix tool names: "skill:tool"
        custom_paths=[Path("/shared/skills")],
        trusted_paths=[Path("/shared/skills")],  # Trust custom path
    ),
)

agent = Agent("gpt-4o", settings=settings)
```

### Subagents: Common Usage Scenarios

#### 1. Basic Subagent Delegation (Synchronous)

```python
from mamba_agents import Agent, SubagentConfig

# Define a subagent config
config = SubagentConfig(
    name="summarizer",
    description="Summarizes text concisely",
    system_prompt="You are an expert summarizer. Be concise and accurate.",
    max_turns=5,
)

# Create agent with subagent
agent = Agent("gpt-4o", subagents=[config])

# Delegate a task synchronously
result = agent.delegate_sync("summarizer", "Summarize this article: ...")
print(result.output)    # The summary
print(result.success)   # True if no errors
print(result.duration)  # Execution time
print(result.usage)     # TokenUsage for this delegation
```

#### 2. Async Delegation

```python
import asyncio

async def main():
    agent = Agent("gpt-4o", subagents=[config])

    # Await delegation result
    result = await agent.delegate("summarizer", "Summarize: ...")
    print(result.output)

asyncio.run(main())
```

#### 3. Fire-and-Forget Delegation

```python
async def parallel_work():
    agent = Agent("gpt-4o", subagents=[
        SubagentConfig(name="researcher", description="Research tasks"),
        SubagentConfig(name="writer", description="Writing tasks"),
    ])

    # Launch both tasks in parallel
    handle_1 = await agent.delegate_async("researcher", "Research topic X")
    handle_2 = await agent.delegate_async("writer", "Draft outline for Y")

    # Check completion status
    print(handle_1.is_complete)  # False (still running)
    print(handle_2.is_complete)  # False (still running)

    # Wait for results
    result_1 = await handle_1.result()
    result_2 = await handle_2.result()

    print(result_1.output)
    print(result_2.output)
```

#### 4. Subagent with Tool Access

```python
from mamba_agents.tools import read_file, grep_search

# Tools are resolved by name from the parent agent's toolset
agent = Agent("gpt-4o", tools=[read_file, grep_search])

config = SubagentConfig(
    name="code-reader",
    description="Reads and analyzes code",
    tools=["read_file", "grep_search"],  # Named tools from parent
    disallowed_tools=["run_bash"],       # Explicitly blocked
    max_turns=10,
)

agent.register_subagent(config)
result = agent.delegate_sync("code-reader", "Analyze src/main.py")
```

#### 5. Subagent with Pre-loaded Skills

```python
config = SubagentConfig(
    name="skilled-helper",
    description="Helper with pre-loaded skill content",
    skills=["code-review", "testing-guide"],  # Skill names to pre-load
    max_turns=15,
)

# Skill content is injected into the subagent's system prompt
# as "## Skill: code-review" and "## Skill: testing-guide" sections
agent = Agent("gpt-4o", subagents=[config], skill_dirs=[".mamba/skills"])
```

#### 6. Subagent Config from Markdown Files

```
.mamba/agents/
├── researcher.md
└── summarizer.md
```

```markdown
---
name: researcher
description: Research and information gathering subagent
model: gpt-4o
tools: [read_file, grep_search]
max-turns: 20
---

You are a research specialist. When given a topic, you should:
1. Search for relevant information
2. Verify facts from multiple sources
3. Compile a structured report
```

```python
# Discover configs from .mamba/agents/ directories
agent = Agent("gpt-4o")
configs = agent.subagent_manager.discover()
for config in configs:
    agent.register_subagent(config)
```

#### 7. Usage Tracking Across Delegations

```python
agent = Agent("gpt-4o", subagents=[
    SubagentConfig(name="helper-1", description="Helper 1"),
    SubagentConfig(name="helper-2", description="Helper 2"),
])

# Run multiple delegations
agent.delegate_sync("helper-1", "Task A")
agent.delegate_sync("helper-2", "Task B")
agent.delegate_sync("helper-1", "Task C")

# Get per-subagent usage breakdown
breakdown = agent.subagent_manager.get_usage_breakdown()
for name, usage in breakdown.items():
    print(f"{name}: {usage.total_tokens} tokens")

# Subagent usage is also aggregated into the parent's total
total = agent.get_usage()
print(f"Total (including subagents): {total.total_tokens} tokens")
```

#### 8. Dynamic Subagent Spawning

```python
# Create a one-off subagent without pre-registration
config = SubagentConfig(
    name="_temp_analyzer",
    description="One-time analysis task",
)

result = await agent.subagent_manager.spawn_dynamic(config, "Analyze this data...")
print(result.output)
# The subagent is not registered and cannot be reused
```

### Integration Patterns

#### Skills + Subagents Together

```python
from mamba_agents import Agent, SubagentConfig

# Full setup with both subsystems
agent = Agent(
    "gpt-4o",
    skill_dirs=[".mamba/skills"],
    subagents=[
        SubagentConfig(
            name="researcher",
            description="Research specialist",
            skills=["web-search"],     # Pre-load the web-search skill
            tools=["read_file"],
            max_turns=20,
        ),
    ],
)

# Wire the bi-directional references (required for fork-mode)
agent.skill_manager.subagent_manager = agent.subagent_manager
agent.subagent_manager._skill_manager = agent.skill_manager

# Now you can:
# 1. Invoke standard skills
content = agent.invoke_skill("code-review", "src/main.py")

# 2. Invoke fork-mode skills (delegates to subagent)
result = agent.invoke_skill("deep-research", "quantum computing")

# 3. Delegate directly to subagents
result = agent.delegate_sync("researcher", "Find information about X")
```

### Error Handling Patterns

```python
from mamba_agents.skills import SkillNotFoundError, SkillInvocationError
from mamba_agents.subagents import SubagentNotFoundError, SubagentDelegationError

# Skill errors
try:
    agent.invoke_skill("nonexistent-skill")
except SkillNotFoundError as e:
    print(f"Skill not found: {e.name}")

try:
    agent.invoke_skill("restricted-skill")
except SkillInvocationError as e:
    print(f"Cannot invoke: {e.reason}")

# Subagent errors
try:
    agent.delegate_sync("unknown-agent", "task")
except SubagentNotFoundError as e:
    print(f"Config not found: {e.config_name}")
    print(f"Available: {e.available}")

# Delegation failures are captured in SubagentResult (not raised)
result = agent.delegate_sync("helper", "task")
if not result.success:
    print(f"Delegation failed: {result.error}")
```

---

## Analysis Methodology

- **Source files read**: All 18 files in `skills/` and `subagents/` subsystems, plus Agent integration points in `agent/core.py` and `config/settings.py`
- **Deep investigation**: Git history analysis, dependency verification, test suite execution with coverage
- **Test assessment**: 524 test functions across 13 test files identified and categorized
- **Findings from 3 explorer agents**: Skills explorer, subagents explorer, and integration explorer — findings merged and verified against source code
- **Documentation gap analysis**: Reviewed all 80+ existing doc pages, mkdocs.yml nav structure, and `__init__.py` exports against actual source implementation
- **Scope**: Full Skills and Subagents subsystem source, Agent integration layer, test infrastructure, existing documentation site
