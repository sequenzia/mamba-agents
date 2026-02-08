# Execution Context

## Project Patterns
- Output/data types use `@dataclass` (not Pydantic BaseModel). Examples: `AgentResult`, `ContextState`, `CompactionResult`, `UsageRecord`, `TokenUsage`, `CostBreakdown`.
- Configuration types use `pydantic.BaseModel` (e.g., `AgentConfig`, `CompactionConfig`).
- All modules use `from __future__ import annotations` at the top.
- Google-style docstrings on all public classes and methods.
- Dataclass fields with mutable defaults use `field(default_factory=...)`.
- Test files use class-based test organization (`class TestX:`) with `-> None` return annotations.
- Tests import directly from the module being tested, not from top-level `__init__.py`.
- Line length is 100 chars (ruff config).
- Error hierarchies follow prompts/errors.py pattern: standalone `Exception` base class, contextual attributes, Google-style docstrings, `__reduce__` for pickle support.
- Pydantic `field_validator` does NOT run on default values — use `model_validator(mode="after")` for post-init processing of defaults.
- `Callable` import: use `from collections.abc import Callable` (ruff UP035 rule).
- `asyncio_mode = "auto"` in pyproject.toml — no `@pytest.mark.asyncio` decorators needed.

## Key Decisions
- Prior session used dataclasses for `MessageStats`, `ToolCallInfo`, `Turn` -- consistent with project convention for read-only output types.
- `SkillInfo` is a `@dataclass` (output type), `Skill`/`SkillConfig` are Pydantic `BaseModel` (config types).
- `SubagentConfig` is Pydantic `BaseModel`, `SubagentResult`/`DelegationHandle` are `@dataclass`.
- Enums use `(str, Enum)` pattern (not `StrEnum`) for config serialization compatibility.
- `_is_subagent` uses Pydantic `PrivateAttr` — not settable via constructor kwargs, not in `model_dump()`.
- Loader modules follow: `_read_file()` → `_split_*()` → `_parse_*()` → `_validate_*()` → `_map_*()` pattern.
- Validation uses non-throwing pattern — all issues returned as structured `ValidationResult`.
- `parent_agent.override(model=...)` does NOT affect spawned subagents — tests must mock `_spawn` to return pre-configured test agents.
- `UsageTracker.get_total_usage()` returns a mutable `TokenUsage` object — tests must capture scalar values before mutations.
- `_UsageTrackingHandle` extends `DelegationHandle` (dataclass) — must call `super().__init__()` with all required fields.
- Agent constructor: when `config` is passed, top-level `system_prompt` kwarg is ignored (config wins).
- Skills lazy init: store `_pending_skills`/`_pending_skill_dirs` in constructor, `skill_manager` property creates on first access.
- TYPE_CHECKING imports used for skill types in core.py to avoid circular imports; runtime imports are lazy inside methods.
- Coverage command needs `--cov=src/mamba_agents/skills` (path-based) not `--cov=mamba_agents.skills` (module-based).
- MCP __init__.py pattern is reference for package exports (alphabetically sorted __all__, grouped imports).
- `SkillManager.subagent_manager` is a settable property for post-construction wiring to avoid circular initialization.
- `activate_with_fork()` uses lazy imports for all subagent types to prevent circular deps.
- `patch("mamba_agents.skills.integration.activate_with_fork")` needed (not `manager.activate_with_fork`) because import is lazy inside method.

## Known Issues
- No runtime type validation on dataclass fields (by design -- project uses dataclasses for output types, not input validation).
- skills/errors.py task #1 added `__reduce__` for pickle support; subagents/errors.py task #3 also has `__reduce__`. Ensure consistency across both modules.

## File Map
- `src/mamba_agents/agent/messages.py` - MessageQuery class, data models, filter/query, analytics, export
- `src/mamba_agents/agent/__init__.py` - Agent module exports
- `src/mamba_agents/__init__.py` - Top-level package exports
- `src/mamba_agents/agent/core.py` - Main Agent class
- `src/mamba_agents/agent/display/` - Display module (Rich, Plain, HTML renderers)
- `pyproject.toml` - Package metadata, dependencies, tool configuration
- `src/mamba_agents/skills/__init__.py` - Skills package init
- `src/mamba_agents/skills/errors.py` - Skill error hierarchy (SkillError base + 5 subclasses)
- `src/mamba_agents/skills/config.py` - Skill enums (SkillScope, TrustLevel), data models (SkillInfo, Skill, SkillConfig, ValidationResult)
- `src/mamba_agents/subagents/__init__.py` - Subagents package init
- `src/mamba_agents/subagents/errors.py` - SubagentError hierarchy (6 classes)
- `src/mamba_agents/subagents/config.py` - SubagentConfig (BaseModel), SubagentResult (dataclass), DelegationHandle (dataclass)
- `tests/unit/test_skill_errors.py` - Skill error tests (35 tests)
- `tests/unit/test_skill_config.py` - Skill data model tests (30 tests)
- `tests/unit/test_subagents/test_errors.py` - Subagent error tests (42 tests)
- `tests/unit/test_subagents/test_config.py` - Subagent data model tests (22 tests)
- `src/mamba_agents/skills/loader.py` - SKILL.md parser (load_metadata, load_full)
- `src/mamba_agents/skills/registry.py` - SkillRegistry class (register/deregister/get/list/has)
- `src/mamba_agents/skills/validator.py` - Skill validation (validate, validate_frontmatter, resolve_trust_level, check_trust_restrictions)
- `src/mamba_agents/subagents/loader.py` - Subagent markdown config loader (load_subagent_config, discover_subagents)
- `src/mamba_agents/agent/config.py` - AgentConfig now has `_is_subagent` PrivateAttr
- `src/mamba_agents/config/settings.py` - AgentSettings now has `skills: SkillConfig | None`
- `src/mamba_agents/tokens/tracker.py` - UsageTracker now has `source` field on UsageRecord, `get_subagent_usage()`
- `tests/unit/test_skill_loader.py` - Skill loader tests (51 tests)
- `tests/unit/test_skill_registry.py` - Skill registry tests (46 tests)
- `tests/unit/test_skill_validator.py` - Skill validator tests (48 tests)
- `tests/unit/test_subagents/test_loader.py` - Subagent loader tests (30 tests)
- `tests/unit/test_config_extensions.py` - Config extension tests (17 tests)
- `tests/unit/test_tracker.py` - UsageTracker subagent tests (15 tests)
- `src/mamba_agents/skills/discovery.py` - scan_directory, discover_skills (three-level priority)
- `src/mamba_agents/skills/invocation.py` - InvocationSource enum, parse_arguments, substitute_arguments, activate, deactivate
- `src/mamba_agents/skills/manager.py` - SkillManager facade (discover, register/deregister, get/list, activate/deactivate, validate, get_tools)
- `src/mamba_agents/skills/testing.py` - SkillTestHarness class + skill_harness pytest fixture
- `src/mamba_agents/subagents/spawner.py` - spawn, _build_system_prompt, _resolve_tools, _enforce_no_nesting
- `src/mamba_agents/subagents/delegation.py` - delegate (async), delegate_sync, delegate_async
- `src/mamba_agents/subagents/manager.py` - SubagentManager facade (register/deregister/list/get, delegate/delegate_sync/delegate_async, spawn_dynamic, get_usage_breakdown)
- `tests/unit/test_skill_discovery.py` - Skill discovery tests (37 tests)
- `tests/unit/test_skill_invocation.py` - Skill invocation tests (79 tests)
- `tests/unit/test_skill_manager.py` - SkillManager tests (55 tests)
- `tests/unit/test_skill_testing.py` - SkillTestHarness tests (39 tests)
- `tests/unit/test_skill_init.py` - Skills package __init__.py export tests (18 tests)
- `tests/unit/test_skills/__init__.py` - Skills test package init
- `tests/unit/test_skills/test_cross_cutting.py` - Cross-cutting integration tests (36 tests)
- `tests/unit/test_subagents/test_spawner.py` - Subagent spawner tests (30 tests)
- `tests/unit/test_subagents/test_delegation.py` - Subagent delegation tests (49 tests)
- `tests/unit/test_subagents/test_manager.py` - SubagentManager tests (52 tests)
- `tests/unit/test_agent_skills.py` - Agent skills facade tests (31 tests)
- `tests/conftest.py` - Now includes sample_skill_dir, sample_skill_info, sample_skill, sample_subagent_config, sample_agent_dir fixtures
- `src/mamba_agents/skills/integration.py` - Skills-subagents integration (fork activation, circular detection)
- `tests/unit/test_subagent_init.py` - Subagent package __init__.py export tests (16 tests)
- `tests/unit/test_subagents/test_nesting.py` - No-nesting enforcement tests (25 tests)
- `tests/unit/test_subagents/test_cross_cutting.py` - Cross-cutting integration tests (21 tests)
- `tests/unit/test_agent_subagents.py` - Agent subagents facade tests (31 tests)
- `tests/unit/test_skills_subagents_integration.py` - Skills-subagents integration tests (38 tests)

## Task History
### Prior Sessions Summary
Previous execution sessions (exec-session-20260202, exec-session-20260203) implemented message querying/analytics (MessageQuery, MessageStats, ToolCallInfo, Turn), display rendering (Rich/Plain/HTML renderers, DisplayPreset, standalone functions, snapshot tests), and __init__.py export updates. All tasks passed successfully.

### Task [1]: Create skill error hierarchy - PASS
- Created `src/mamba_agents/skills/errors.py` with 6 error classes, pickle support via `__reduce__`
- 35 tests passing

### Task [2]: Create skill data models and enums - PASS
- Created `src/mamba_agents/skills/config.py` with SkillScope, TrustLevel enums, SkillInfo dataclass, Skill/SkillConfig BaseModels, ValidationResult dataclass
- 30 tests passing

### Task [3]: Create subagent error hierarchy - PASS
- Created `src/mamba_agents/subagents/errors.py` with 6 error classes, pickle support via `__reduce__`
- 42 tests passing

### Task [12]: Create subagent data models - PASS
- Created `src/mamba_agents/subagents/config.py` with SubagentConfig (BaseModel), SubagentResult/DelegationHandle (dataclasses)
- 22 tests passing

### Task [4]: Implement SKILL.md loader and parser - PASS
- Created `src/mamba_agents/skills/loader.py` with load_metadata() and load_full()
- 51 tests passing

### Task [6]: Implement skill registry - PASS
- Created `src/mamba_agents/skills/registry.py` with register/deregister/get/list/has + async variants
- 46 tests passing

### Task [8]: Implement skill validation and trust levels - PASS
- Created `src/mamba_agents/skills/validator.py` with validate, validate_frontmatter, resolve_trust_level, check_trust_restrictions
- 48 tests passing

### Task [13]: Implement subagent config loader from markdown files - PASS
- Created `src/mamba_agents/subagents/loader.py` with load_subagent_config, discover_subagents
- 30 tests passing

### Task [22]: Extend AgentConfig and AgentSettings - PASS
- Added _is_subagent PrivateAttr to AgentConfig, skills SkillConfig field to AgentSettings
- 17 tests passing

### Task [24]: Extend UsageTracker for subagent token aggregation - PASS
- Added source field to UsageRecord, get_subagent_usage() method
- 15 tests passing

### Task [5]: Implement skill discovery from directories - PASS
- Created `src/mamba_agents/skills/discovery.py` with scan_directory, discover_skills
- 37 tests passing

### Task [7]: Implement skill invocation and argument substitution - PASS
- Created `src/mamba_agents/skills/invocation.py` with InvocationSource, parse_arguments, substitute_arguments, activate, deactivate
- Added SkillInvocationError to errors.py
- 79 tests passing

### Task [14]: Implement subagent spawner - PASS
- Created `src/mamba_agents/subagents/spawner.py` with spawn, _build_system_prompt, _resolve_tools, _enforce_no_nesting
- pydantic-ai tools at `agent._function_toolset.tools` (dict name -> Tool with .function)
- 30 tests passing

### Task [9]: Implement SkillManager facade - PASS
- Created `src/mamba_agents/skills/manager.py` composing all skill subsystem components
- 55 tests passing

### Task [15]: Implement sync and async subagent delegation - PASS
- Created `src/mamba_agents/subagents/delegation.py` with delegate, delegate_sync, delegate_async
- pydantic-ai TestModel uses `custom_output_text` parameter, UsageLimitExceeded for max turns
- 49 tests passing

### Task [10]: Create skills package __init__.py with public exports - PASS
- Updated `src/mamba_agents/skills/__init__.py` with imports and __all__ (13 symbols)
- MCP __init__.py pattern used as reference for package exports
- 18 tests passing

### Task [11]: Add unit tests for skills system (Phase 1) - PASS
- Created `tests/unit/test_skills/test_cross_cutting.py` with 36 cross-cutting integration tests
- Added shared fixtures to `tests/conftest.py` (sample_skill_dir, sample_skill_info, sample_skill)
- Skills coverage at 92.07%, 474 total skills tests

### Task [23]: Implement SkillTestHarness testing utility - PASS
- Created `src/mamba_agents/skills/testing.py` with SkillTestHarness class + skill_harness fixture
- 39 tests passing, full suite 2072+ tests passing

### Task [20]: Add skills parameters and methods to Agent facade - PASS
- Modified `src/mamba_agents/agent/core.py` with skills/skill_dirs params, skill_manager lazy property, facade methods
- 31 tests in test_agent_skills.py

### Task [16]: Implement SubagentManager facade - PASS
- Created `src/mamba_agents/subagents/manager.py` with SubagentManager + _UsageTrackingHandle
- 52 tests passing

### Task [17]: Create subagents package __init__.py with public exports - PASS
- Updated `src/mamba_agents/subagents/__init__.py` with 10 symbols exported
- 16 tests passing

### Task [18]: Add unit tests for subagents system (Phase 2) - PASS
- Created test_nesting.py (25 tests) and test_cross_cutting.py (21 tests)
- Total 271 subagent tests at 96.64% coverage

### Task [21]: Add subagents parameters and methods to Agent facade - PASS
- Modified core.py with subagents param, lazy subagent_manager property, facade methods
- 31 tests, 2284 full suite passing

### Task [19]: Implement Skills-Subagents bi-directional integration - PASS
- Created `src/mamba_agents/skills/integration.py` with activate_with_fork, detect_circular_skill_subagent
- Modified SkillManager with subagent_manager property and fork mode support
- 38 tests, 2322 full suite passing
