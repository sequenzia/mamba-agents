# Skills & Subagents v1 Implementation Analysis — v2 PRD Input

**Analysis Context**: Feature exploration for v2 PRD — identifying known issues, architectural gaps, and recommendations
**Branch Analyzed**: `skills-and-subagents` (7 commits, 19,549 lines added)
**Date**: 2026-02-08
**Method**: Deep synthesis from 3 explorer agents + independent git history, dependency, and source code investigation

---

## Executive Summary

The v1 Skills and Subagents implementation is architecturally sound in its core design — the facade pattern, progressive disclosure loading, and no-nesting enforcement are well-executed. However, the implementation has **critical integration gaps** that prevent the subsystems from functioning as a cohesive whole. The most severe issue is that skills are **not wired into pydantic-ai's tool system**, making them a content-preparation layer rather than an autonomous agent capability. Several config fields are dead code (`max_turns`, `auto_discover`), the bi-directional wiring between subsystems is never established through the Agent facade, and the async bridging pattern is fragile.

The v2 PRD should focus on: (1) completing the integration that v1 declared but didn't wire, (2) removing or implementing dead infrastructure, and (3) hardening the async story.

---

## Issue Catalog

### CRITICAL — Must Fix in v2

#### ISS-001: Skills Not Wired into `agent.run()`

- **Severity**: Critical
- **Files**: `skills/manager.py`, `agent/core.py`
- **Description**: Skills exist in a `SkillManager` registry that pydantic-ai knows nothing about. When `agent.run()` is called, it delegates directly to `pydantic_ai.Agent.run()` without injecting skill tools or skill content. The model **cannot** discover, invoke, or interact with skills autonomously during conversation.
- **Dead infrastructure**: `InvocationSource.MODEL` enum value, `disable_model_invocation` flag on SkillInfo, and `Skill._tools` private attribute all exist but have **no code path that uses them**. `invoke_skill()` always passes `InvocationSource.CODE`.
- **Impact**: Skills are effectively prompt templates, not agent capabilities. Users must manually create pydantic-ai tools that wrap `invoke_skill()` or inject skill content into prompts. The documented workarounds (Pattern 1: prompt injection, Pattern 2: manual tool bridging) confirm this is a known limitation.
- **v2 Recommendation**: Either (a) automatically register skill-backed pydantic-ai tools during `agent.run()` so the model can invoke skills, or (b) explicitly redefine skills as a content-preparation system and remove the dead `MODEL` infrastructure. Option (a) is strongly preferred — it fulfills the original spec intent.

#### ISS-002: Missing Bi-directional Wiring in Agent Facade

- **Severity**: Critical
- **Files**: `agent/core.py` lines ~197-215 (`_init_skill_manager`, `_init_subagent_manager`)
- **Description**: `Agent._init_skill_manager()` creates a `SkillManager` and `Agent._init_subagent_manager()` creates a `SubagentManager`, but they **never wire the cross-references**. The following lines are never executed by the Agent:
  ```python
  skill_manager.subagent_manager = subagent_manager
  subagent_manager._skill_manager = skill_manager
  ```
- **Impact**: Fork-mode skills (`execution_mode: "fork"`) silently fail to delegate to subagents when activated through the Agent facade. Subagent skill pre-loading (injecting skill content into subagent system prompts) also fails. Users must manually wire the managers after initialization.
- **Evidence**: The `SkillManager.subagent_manager` setter property exists specifically for this purpose, and the existing documentation recommends manual wiring as a workaround.
- **v2 Recommendation**: Add automatic cross-wiring in `Agent.__init__()` when both managers are initialized, and also wire lazily when either manager is first accessed and the other already exists.

#### ISS-003: `max_turns` Config Field is Dead Code

- **Severity**: Critical
- **Files**: `subagents/config.py` (field declaration), `subagents/spawner.py` (never reads it), `subagents/delegation.py` (never applies it)
- **Description**: `SubagentConfig.max_turns` (default: 50) is declared, parsed from markdown files by the loader, and even has a dedicated error class (`SubagentTimeoutError`), but it is **never passed to the spawned Agent or to pydantic-ai's usage limits**. The spawner creates an `Agent` without any turn limitation. The delegation functions catch `UsageLimitExceeded` but only from pydantic-ai's default limits, not from the configured value.
- **Impact**: Users configure `max_turns` expecting subagents to terminate after N turns, but the setting is silently ignored. Subagents can run indefinitely (up to pydantic-ai's own defaults).
- **v2 Recommendation**: Wire `config.max_turns` to pydantic-ai's `usage_limits` parameter in `agent.run()` / `agent.run_sync()` calls within the delegation functions, or set it on the `AgentConfig.max_iterations`.

#### ISS-004: Fragile Async Workaround in Fork Execution

- **Severity**: Critical
- **Files**: `skills/integration.py` lines ~214-233 (`activate_with_fork`)
- **Description**: When `activate_with_fork()` is called inside a running event loop (e.g., FastAPI, Jupyter), it uses `ThreadPoolExecutor` + `asyncio.run()` to bridge the sync/async impedance mismatch. This pattern:
  - Creates a new event loop in a thread (fragile with nested loops)
  - Can deadlock if the inner `asyncio.run()` waits on resources held by the outer loop
  - Uses `concurrent.futures.ThreadPoolExecutor` as a default (no pool size control)
  - Is a known anti-pattern in the Python async ecosystem
- **Impact**: Fork-mode skills will fail or deadlock in async web frameworks (FastAPI, Starlette) or Jupyter notebooks — common deployment targets for agent frameworks.
- **v2 Recommendation**: Replace with proper async-first design. Options: (a) make `activate_with_fork` an async function and propagate async through the call chain, (b) use `anyio.from_thread.run()` for proper sync-to-async bridging, or (c) require fork-mode activation to always be async via `SkillManager.activate_async()`.

---

### HIGH — Should Fix in v2

#### ISS-005: SubagentManager Mutates Parent's Private State

- **Severity**: High
- **Files**: `subagents/manager.py` (`_aggregate_usage` method, ~last 30 lines)
- **Description**: `_aggregate_usage()` directly accesses and mutates `parent_agent.usage_tracker._subagent_totals` — a private dictionary. It also calls `record_raw()` which doesn't accept a `source` parameter, then separately writes to `_subagent_totals` for per-subagent tracking.
- **Impact**: Any refactoring of `UsageTracker` internals (renaming `_subagent_totals`, changing from dict to a different structure) will silently break subagent usage tracking. The `record_usage(source=...)` public API already supports per-source tracking but isn't used.
- **v2 Recommendation**: Replace direct `_subagent_totals` mutation with `record_usage(usage, source=config_name)`. Add `source` parameter to `record_raw()` if raw recording with source tracking is needed.

#### ISS-006: Duplicate Loader Logic in Registry

- **Severity**: High
- **Files**: `skills/registry.py` (`_load_skill_from_path` function), `skills/loader.py`
- **Description**: `registry.py` contains a standalone `_load_skill_from_path()` function that reimplements SKILL.md frontmatter parsing instead of delegating to `loader.py`. The registry uses `content.find("---", 3)` for frontmatter splitting while the loader uses line-by-line iteration — different algorithms for the same task. The registry function even has a comment: "When the full `skills/loader.py` module is available, this function should delegate to it."
- **Impact**: Bug fixes or parsing improvements in `loader.py` won't be reflected in registry-based loading. Two divergent parsers increase maintenance burden and risk inconsistent behavior.
- **v2 Recommendation**: Have `_load_skill_from_path()` delegate to `loader.load_full()` instead of reimplementing the parser.

#### ISS-007: Tool Resolution Reaches into pydantic-ai Private Internals

- **Severity**: High
- **Files**: `subagents/spawner.py` (`_resolve_tools` function, lines ~55-90)
- **Description**: Tool resolution accesses `parent._agent._function_toolset.tools` — a chain of private attributes deep inside pydantic-ai's Agent implementation. This is necessary to resolve string tool names (e.g., `tools=["read_file"]`) against the parent's registered tools.
- **Impact**: Any pydantic-ai refactoring of its internal `_function_toolset` or `_FunctionToolset` class will break subagent tool inheritance. Given pydantic-ai is pre-1.0 (`>=0.0.49`), internal API changes are likely.
- **v2 Recommendation**: Either (a) maintain a parallel tool registry in the mamba-agents `Agent` class (not relying on pydantic-ai internals), or (b) only accept `Callable` tools in `SubagentConfig.tools` (no string resolution), or (c) contribute a public API to pydantic-ai for tool introspection.

#### ISS-008: `auto_discover` Config Field is Dead Code

- **Severity**: High
- **Files**: `skills/config.py` (field declaration), `skills/manager.py` (never checks it)
- **Description**: `SkillConfig.auto_discover` defaults to `True` with description "auto-discover skills on startup", but **nothing in the codebase checks this flag**. Neither `SkillManager.__init__()` nor `Agent._init_skill_manager()` calls `discover()` based on this flag. Users must always call `discover()` explicitly.
- **Impact**: Users set `auto_discover=True` expecting automatic discovery but skills are never found. Silent configuration failure.
- **v2 Recommendation**: Either implement auto-discovery in `SkillManager.__init__()` when `config.auto_discover is True`, or remove the field if explicit discovery is the intended pattern.

#### ISS-009: `allowed_tools` Not Enforced as Runtime Restrictions

- **Severity**: High
- **Files**: `skills/config.py` (field), `skills/invocation.py` (activation doesn't enforce), `skills/validator.py` (only trust check)
- **Description**: `SkillInfo.allowed_tools` is parsed from frontmatter and used for (a) trust level restriction checks on untrusted skills and (b) test harness reporting. However, it is **never used to actually restrict or register tools** during skill activation. The `activate()` function doesn't register `allowed_tools` with the agent, and there's no enforcement that prevents a skill from accessing tools not in its allowlist.
- **Impact**: The `allowed_tools` field creates a false sense of security — skill authors specify tool allowlists that are never enforced at runtime.
- **v2 Recommendation**: Either enforce `allowed_tools` during skill activation (register only listed tools) or rename/redocument the field as informational metadata only.

---

### MEDIUM — Improve in v2

#### ISS-010: Lazy Property Side Effects

- **Severity**: Medium
- **Files**: `agent/core.py` (`skill_manager` and `subagent_manager` properties)
- **Description**: Accessing `agent.skill_manager` or `agent.subagent_manager` **creates** the manager on first access (not just retrieval). This means conditional checks like `if agent.skill_manager:` will unexpectedly initialize the entire subsystem.
- **v2 Recommendation**: Add explicit boolean check properties (`has_skill_manager`, `has_subagent_manager`) or change the lazy properties to not auto-initialize. The CLAUDE.md already documents `agent._skill_manager is not None` as a workaround, but this exposes private state.

#### ISS-011: Pydantic 2.12 Test Collection Compatibility

- **Severity**: Medium
- **Files**: Various test files, `conftest.py`
- **Description**: Some test files fail during pytest collection with `KeyError: 'pydantic.root_model'` under Pydantic 2.12. Affected files include `test_skill_config.py`, `test_skill_loader.py`, `test_skills_subagents_integration.py`, and all 16 tests in `test_subagent_init.py`.
- **v2 Recommendation**: Update test fixtures and conftest for Pydantic 2.12+ compatibility. Pin pydantic version more precisely if needed.

#### ISS-012: Spec Implementation Gaps — Unimplemented Features

- **Severity**: Medium
- **Description**: Several spec features were not implemented:
  - **`scripts/` and `assets/` directories**: Spec Section 5.1 requires "Detect and index optional directories: scripts/, references/, assets/" — only `references/` was implemented
  - **`hooks` field**: Declared in `SkillInfo` and parsed from frontmatter, but marked "Reserved for future lifecycle hooks (not implemented in v1)". No execution logic exists — only a trust restriction check.
  - **`permission-mode` for subagents**: Spec analysis FIND-005 noted this field was in spec frontmatter requirements but not in `SubagentConfig`
- **v2 Recommendation**: Either implement these features or explicitly remove them from the spec. For `hooks`, define the hook system (supported hooks, execution model) or remove the field entirely.

#### ISS-013: `context` vs `execution_mode` Field Naming Duality

- **Severity**: Medium
- **Files**: `skills/loader.py` (`_FIELD_MAP`), `skills/config.py` (`SkillInfo.execution_mode`)
- **Description**: SKILL.md frontmatter uses `context: fork` (per the Agent Skills spec), which the loader maps to `execution_mode` on `SkillInfo`. This renaming is a good design decision (addresses spec analysis FIND-008) but creates confusion: documentation references `context: fork`, while Python code uses `execution_mode="fork"`. Tests mix both naming styles.
- **v2 Recommendation**: Keep the mapping but ensure consistent documentation. Consider also accepting `execution-mode` as an alias in frontmatter for users who read the Python API first.

#### ISS-014: No Subagent Lifecycle Management

- **Severity**: Medium
- **Files**: `subagents/manager.py`, `subagents/delegation.py`
- **Description**: Each delegation call in `SubagentManager.delegate()` and `delegate_sync()` **spawns a new Agent instance**. There is no agent reuse, pooling, or lifecycle management. For repeated delegations to the same config, this means:
  - A new `Agent`, `ContextManager`, `UsageTracker` are created each time
  - No conversation continuity between delegations
  - No warmup or state preservation
- **v2 Recommendation**: Consider adding agent pooling or a `keep_alive` option for repeated delegations. Add an option to carry over conversation history between delegations to the same subagent config.

---

### LOW — Nice to Have

#### ISS-015: SkillConfig in AgentSettings Defaults to None

- **Severity**: Low
- **Files**: `config/settings.py`
- **Description**: `AgentSettings.skills` defaults to `None`. When `SkillManager` receives `None`, it creates its own `SkillConfig()` with defaults. The None-or-config pattern works but adds an unnecessary layer.
- **v2 Recommendation**: Consider defaulting to `SkillConfig()` instead of `None` to simplify the initialization path.

#### ISS-016: SubagentConfig.tools=None Means "No Tools" (Not Inherit)

- **Severity**: Low (By Design)
- **Files**: `subagents/spawner.py` (`_resolve_tools`)
- **Description**: When `config.tools is None`, subagents get zero tools. This is by design but may surprise users who expect tool inheritance from the parent.
- **v2 Recommendation**: Document this clearly. Consider adding a sentinel value like `tools="inherit"` for explicit parent tool inheritance.

---

## Architecture Assessment — What Works Well

### Strengths to Preserve in v2

1. **Facade Pattern**: Both `SkillManager` and `SubagentManager` follow the established `MCPClientManager` pattern, providing clean unified APIs over internal components. This is well-executed and should be preserved.

2. **Progressive Disclosure Loading**: The three-tier loading model (Tier 1: metadata at discovery, Tier 2: body at activation, Tier 3: references on demand) is an excellent performance optimization. Discovery scans only parse YAML frontmatter — body loading is deferred.

3. **No-Nesting Enforcement**: The `_is_subagent` flag on `AgentConfig` prevents unbounded recursion cleanly. The check is in the spawner, making it impossible to bypass. This is a good safety mechanism.

4. **Error Hierarchy Design**: Both subsystems have well-structured exception hierarchies with pickle support, specific error types per failure mode, and helpful error messages with context (e.g., `SubagentNotFoundError` includes the list of available configs).

5. **Circular Reference Detection**: The `detect_circular_skill_subagent()` function traces `skill → agent → pre-loaded skills` chains using DFS with path tracking. This proactively prevents infinite loops in fork-mode activation.

6. **Fault-Tolerant Delegation**: All execution errors during delegation are captured into `SubagentResult(success=False, error=...)` rather than raised. Only unrecoverable `SubagentConfigError` is re-raised. This makes delegation safe to use in production.

7. **Test Harness**: `SkillTestHarness` enables testing skills without an Agent or LLM, which is valuable for skill development workflows.

8. **Field Mapping**: The `_FIELD_MAP` in `loader.py` cleanly translates YAML hyphenated keys to Python underscore attributes, and correctly renames `context` to `execution_mode`.

---

## Spec vs Implementation Gap Analysis

| Spec Requirement | Status | Details |
|-----------------|--------|---------|
| SKILL.md parsing with YAML frontmatter | Implemented | Full parser pipeline in `loader.py` |
| Progressive disclosure (3 tiers) | Implemented | Metadata, body, references all working |
| Three-level directory discovery | Implemented | Project, user, custom with priority |
| Skill registry with async safety | Implemented | `asyncio.Lock` in `SkillRegistry` |
| Argument substitution ($ARGUMENTS, $N) | Implemented | Full substitution with fallback appending |
| Trust levels (trusted/untrusted) | Implemented | Scope-based defaults + configurable trusted_paths |
| Fork execution mode | Partially | Code exists but **not wired through Agent facade** (ISS-002) |
| Skill tools registered with agent | **Not Implemented** | `allowed_tools` parsed but not enforced (ISS-009) |
| Skills available during agent.run() | **Not Implemented** | Skills are content-only, not tools (ISS-001) |
| `scripts/` and `assets/` directories | **Not Implemented** | Only `references/` implemented |
| `hooks` lifecycle system | **Not Implemented** | Field exists, no execution logic |
| `auto_discover` config | **Not Implemented** | Field exists, never checked (ISS-008) |
| SubagentConfig with markdown files | Implemented | Loader parses `.mamba/agents/*.md` |
| Sync/async/fire-and-forget delegation | Implemented | Three patterns working |
| No-nesting enforcement | Implemented | Clean `_is_subagent` flag check |
| `max_turns` enforcement | **Not Implemented** | Field exists, never applied (ISS-003) |
| Usage tracking aggregation | Implemented | But via private state mutation (ISS-005) |
| Context isolation for subagents | Implemented | Each subagent gets fresh subsystems |
| Skill pre-loading into subagents | Partially | Code exists but **not wired through Agent facade** (ISS-002) |
| SkillTestHarness | Implemented | Working with pytest fixture |
| Validation against schema | Implemented | `validate_frontmatter()` + `validate()` |

---

## Recommendations for v2 PRD

### Priority 1 — Complete the Integration Story

1. **Wire skills into agent.run()**: Register skill-backed pydantic-ai tools so the model can invoke skills autonomously. Remove or implement `InvocationSource.MODEL` and `Skill._tools`.

2. **Auto-wire bi-directional references**: When both `SkillManager` and `SubagentManager` exist, automatically establish cross-references in the Agent facade.

3. **Implement `max_turns`**: Pass `SubagentConfig.max_turns` to pydantic-ai's `usage_limits` parameter during delegation.

4. **Implement `auto_discover`**: Call `discover()` during `SkillManager` initialization when `config.auto_discover is True`.

### Priority 2 — Fix Architectural Issues

5. **Replace async workaround**: Replace `ThreadPoolExecutor` + `asyncio.run()` in `activate_with_fork()` with proper async-first design or `anyio` bridging.

6. **Fix usage tracking**: Replace direct `_subagent_totals` mutation with public `record_usage(source=...)` API.

7. **Deduplicate loader**: Have `registry._load_skill_from_path()` delegate to `loader.load_full()`.

8. **Abstract tool resolution**: Stop reaching into pydantic-ai private internals for tool resolution.

### Priority 3 — Clean Up Dead Infrastructure

9. **Decide on `hooks`**: Either implement the hook system (define supported hooks, execution model, callbacks) or remove the field.

10. **Decide on `scripts/` and `assets/`**: Either implement directory detection and loading, or remove from spec.

11. **Decide on `allowed_tools` enforcement**: Either enforce as runtime restrictions during activation, or rename to `recommended_tools` / make informational only.

12. **Add lifecycle management**: Consider agent pooling or reuse for repeated delegations to the same subagent config.

### Priority 4 — Developer Experience

13. **Add `has_skill_manager` / `has_subagent_manager`** boolean properties to avoid lazy-init side effects.

14. **Add `tools="inherit"` sentinel** for explicit parent tool inheritance in `SubagentConfig`.

15. **Standardize field naming**: Document the `context` → `execution_mode` mapping prominently. Consider accepting both names in frontmatter.

16. **Fix Pydantic 2.12 compatibility**: Update test fixtures for newer Pydantic versions.

---

## Open Questions for v2 PRD

1. **Should skills be tools or prompts?** The fundamental architectural question: should skills be registered as pydantic-ai tools (model can invoke autonomously) or remain a content-preparation system (developer controls invocation)? This decision shapes the entire v2 design.

2. **What is the `hooks` lifecycle?** If hooks are to be implemented, what hooks are supported (on_activate, on_deactivate, on_error?), what's the execution model (sync/async?), and how do they interact with trust levels?

3. **Should subagents support conversation continuity?** Currently each delegation creates a fresh agent. Should there be an option to maintain conversation state across delegations to the same config?

4. **How should `allowed_tools` interact with agent.run() integration?** If skills are wired as pydantic-ai tools, should `allowed_tools` restrict which of the agent's existing tools the model can use while the skill is active?

5. **Should `auto_discover` trigger on agent initialization or on first skill_manager access?** The timing affects startup performance vs. developer expectations.

---

## Analysis Methodology

- **Source files read**: All 18 source files in `skills/` and `subagents/`, plus `agent/core.py`, `agent/config.py`, `config/settings.py`, `tokens/tracker.py`
- **Git history**: Analyzed 7 commits on `skills-and-subagents` branch, traced authorship and evolution of key files
- **Spec comparison**: Cross-referenced all 10 functional requirements from v1 spec against implementation
- **Prior analysis**: Reviewed 1,212-line existing analysis report and 13-finding spec analysis
- **Deep investigation**: Traced dead code paths (`max_turns`, `auto_discover`, `InvocationSource.MODEL`), verified with `git grep` across all source and test files
- **Explorer synthesis**: Integrated findings from 3 concurrent explorers covering skills, subagents, and cross-cutting concerns
