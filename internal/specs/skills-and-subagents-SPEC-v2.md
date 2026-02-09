# Skills and Subagents v2 PRD

**Version**: 1.0
**Author**: Stephen Sequenzia
**Date**: 2026-02-08
**Status**: Draft
**Spec Type**: New feature
**Spec Depth**: Full technical documentation
**Description**: Address 6 known fragility points in the skills and subagents subsystems, stabilizing the experimental APIs for future release.

---

## 1. Executive Summary

The skills and subagents subsystems (implemented in v1 per the original Skills and Subagents PRD) have 6 documented fragility points that prevent the experimental APIs from being stabilized. This PRD specifies targeted fixes for each fragility point: wiring skills into `agent.run()` via a pydantic-ai tool, replacing the fragile async workaround in fork mode, fixing lazy property side effects, decoupling UsageTracker mutation, removing the circular initialization dependency, and adding cleanup to ReActWorkflow's tool mutation. Breaking API changes are acceptable since both subsystems are marked experimental.

## 2. Problem Statement

### 2.1 The Problem

The v1 skills and subagents implementation (~26k lines across 107 files) is functionally complete but contains 6 fragility points documented in CLAUDE.md that create maintenance risk, potential runtime failures, and architectural debt:

1. **Skills cannot be invoked by the model during `agent.run()`** — The `InvocationSource.MODEL` enum exists but has no code path. Skills live in a separate `SkillManager` registry unknown to pydantic-ai. Users must manually create wrapper tools.
2. **Async/sync impedance mismatch in fork mode** — `activate_with_fork()` uses `ThreadPoolExecutor + asyncio.run()` to bridge sync/async, which can deadlock in async contexts (e.g., FastAPI).
3. **Lazy property side effects** — Accessing `agent.skill_manager` or `agent.subagent_manager` **creates** the manager on first access. Conditional checks like `if agent.skill_manager:` unexpectedly initialize subsystems.
4. **Direct mutation of UsageTracker internals** — `SubagentManager._aggregate_usage()` writes directly to `parent_agent.usage_tracker._subagent_totals`, coupling to private state.
5. **Circular initialization dependency** — `SkillManager` and `SubagentManager` reference each other via post-construction wiring (`SkillManager.subagent_manager` setter). Wiring order matters and is fragile.
6. **ReActWorkflow permanently mutates injected Agent** — `ReActWorkflow.__init__()` registers a `final_answer` tool on the agent with no cleanup mechanism. Reusing the Agent retains this tool.

### 2.2 Current State

All 6 issues are present in the `skills-and-subagents` branch (commit `95cd260`). The implementation is functional and has extensive test coverage (~10k+ lines of tests), but these fragility points are documented as known issues in CLAUDE.md with specific warnings for developers.

### 2.3 Impact Analysis

Without fixing these issues:
- **Skills cannot be model-invoked** — The primary use case for skills (model-driven capability selection) doesn't work. Users must build manual wrappers.
- **Fork mode is unreliable** — The ThreadPoolExecutor workaround will deadlock in production async environments like FastAPI, ASGI servers, or nested async contexts.
- **Lazy property surprises** — Developers cannot safely check whether managers exist without triggering initialization, leading to unexpected resource allocation.
- **UsageTracker coupling** — Any internal refactoring of UsageTracker will silently break subagent usage aggregation.
- **Circular init brittleness** — Changes to initialization order or adding new cross-references could cause hard-to-debug failures.
- **Agent pollution** — ReActWorkflow users cannot safely reuse Agent instances for other purposes.

### 2.4 Business Value

- **API stabilization**: Resolving these issues is prerequisite to removing the "experimental" label from skills and subagents
- **Production readiness**: Fork mode and model invocation must work reliably in async environments
- **Developer trust**: Eliminating surprising behaviors (lazy init side effects, agent pollution) builds confidence in the framework
- **Maintainability**: Removing internal coupling and circular dependencies reduces future maintenance cost

## 3. Goals & Success Metrics

### 3.1 Primary Goals

1. Wire skills into `agent.run()` so the model can invoke skills during execution via a single `invoke_skill` pydantic-ai tool
2. Replace the fragile async workaround in `activate_with_fork()` with a fully async design
3. Replace lazy property side effects with explicit initialization (`agent.init_skills()` / `agent.init_subagents()`)
4. Add a public `record_subagent_usage()` method to UsageTracker, replacing direct private state mutation
5. Remove the bidirectional dependency between SkillManager and SubagentManager, using `integration.py` as mediator
6. Add tool state save/restore to ReActWorkflow so the Agent is not permanently mutated

### 3.2 Success Metrics

| Metric | Current Baseline | Target | Measurement Method |
|--------|------------------|--------|-------------------|
| Skills invocable during agent.run() | Not possible | Functional via invoke_skill tool | Unit + integration tests |
| Fork mode in async context | Deadlock risk | No deadlocks, fully async | Test in nested async context |
| Lazy init side effects | Present (creates managers) | Eliminated (explicit init required) | Unit tests verify no side effects |
| UsageTracker private access | Direct `_subagent_totals` mutation | Public API only | Grep for `_subagent_totals` usage |
| Circular dependency | SkillManager ↔ SubagentManager | Unidirectional via mediator | Import graph analysis |
| Agent tool pollution after ReAct | final_answer tool persists | Tools restored after workflow | Unit test verifying tool cleanup |
| Test coverage (changed modules) | Varies | >= 80% per module | pytest --cov |
| Existing tests preserved | ~10k lines | All passing | pytest full suite |

### 3.3 Non-Goals

- **New features**: This spec does not add new capabilities to skills or subagents
- **Performance optimization**: Performance is not the focus unless it's a side effect of fixing a fragility point
- **API stabilization labeling**: Removing the "experimental" label is a separate decision after these fixes land
- **Additional fragility points**: Only the 6 documented issues are addressed

## 4. User Research

### 4.1 Target Users

#### Primary Persona: AI Application Developer
- **Role/Description**: Software engineer building production AI applications with mamba-agents
- **Goals**: Use skills and subagents reliably in production applications, including async web frameworks
- **Pain Points**: Skills can't be model-invoked; fork mode deadlocks in FastAPI; unexpected initialization behavior
- **Context**: Building AI-powered applications deployed in async environments
- **Technical Proficiency**: High — comfortable with Python, pydantic, async programming

### 4.2 User Workflows Affected

#### Workflow 1: Model-Driven Skill Invocation (Currently Broken)
```
Developer registers skills with Agent
    --> Developer calls agent.run(task)
    --> Model decides to invoke a skill
    --> [BROKEN] No code path exists for model to invoke skills
    --> [FIXED] Model calls invoke_skill tool → SkillManager activates skill → content returned
```

#### Workflow 2: Fork Mode in Async Context (Currently Fragile)
```
Skill with execution_mode: "fork" activated
    --> activate_with_fork() called
    --> [FRAGILE] ThreadPoolExecutor + asyncio.run() → potential deadlock
    --> [FIXED] Fully async delegation, no sync/async bridging
```

#### Workflow 3: Agent Reuse After ReAct (Currently Broken)
```
Developer runs ReActWorkflow with Agent
    --> final_answer tool registered permanently
    --> Developer reuses Agent for other tasks
    --> [BROKEN] final_answer tool still registered, polluting tool list
    --> [FIXED] Tool state restored after workflow completes
```

## 5. Functional Requirements

### 5.1 Fix: Wire Skills into agent.run()

**Priority**: P0 (Critical)
**Complexity**: High

#### User Stories

**US-001**: As a developer, I want the model to be able to invoke skills during `agent.run()` so that skills can be dynamically selected and activated by the LLM.

**Acceptance Criteria**:
- [ ] A single `invoke_skill` pydantic-ai tool is registered with the agent when skills are initialized
- [ ] The `invoke_skill` tool accepts `name: str` and `arguments: str` parameters
- [ ] The tool's description dynamically lists available skills (name + description) so the model knows what's available
- [ ] All active skills are available to the model by default
- [ ] The `disable-model-invocation: true` frontmatter flag prevents a skill from appearing in the tool's available list
- [ ] `InvocationSource.MODEL` is now used when the model invokes a skill via the tool
- [ ] Permission gates respect `InvocationSource.MODEL` (e.g., `user_invocable=false` does NOT block model invocation)
- [ ] The tool returns the activated skill's processed content as a string
- [ ] If the skill uses `execution_mode: "fork"`, the tool delegates to a subagent and returns the result
- [ ] The tool handles errors gracefully (skill not found, validation failures) by returning error messages rather than raising

**Technical Notes**:
- Register the tool via `pydantic_agent.tool()` decorator pattern or `tools` parameter during agent construction
- Tool description should be regenerated when skills are registered/deregistered (or lazily on next call)
- The `invoke_skill` tool is only registered when `agent.init_skills()` is called and skills exist
- Remove the `Skill._tools` private attribute if it serves no purpose after this change
- Consider whether `InvocationSource.MODEL` should trigger `on_invoke` hooks differently than `CODE`

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| No skills registered | Model calls invoke_skill | Tool returns "No skills available" |
| Unknown skill name | `invoke_skill("nonexistent", "")` | Tool returns error message, not exception |
| Skill with disable-model-invocation | Model tries to invoke | Skill excluded from available list; if called directly, returns permission error |
| Fork-mode skill via model | Model invokes fork skill | Async delegation happens, result returned |
| Skill registration after init | `agent.register_skill()` after init_skills | New skill available on next invoke_skill call |

---

### 5.2 Fix: Async Fork Mode

**Priority**: P0 (Critical)
**Complexity**: Medium

#### User Stories

**US-002**: As a developer, I want `activate_with_fork()` to work reliably in async contexts (FastAPI, ASGI servers) without deadlock risk.

**Acceptance Criteria**:
- [ ] `activate_with_fork()` is redesigned as `async def activate_with_fork()`
- [ ] No `ThreadPoolExecutor`, `asyncio.run()`, or sync/async bridging code
- [ ] Fork delegation uses `await subagent_manager.delegate()` (async) or `await subagent_manager.spawn_dynamic()` directly
- [ ] Works correctly inside running event loops (FastAPI, ASGI)
- [ ] Works correctly when called from sync contexts via the agent's existing `run_sync()` pattern
- [ ] Callers of `activate_with_fork()` updated to use `await`
- [ ] Error handling preserved: trust check, circular detection, delegation failure capture

**Technical Notes**:
- The function signature changes from `def activate_with_fork(...)` to `async def activate_with_fork(...)`
- All callers in `skills/invocation.py` and `skills/manager.py` must be updated to await
- The `SkillManager.activate()` method may need to become async (or have an async variant)
- Consider making `Agent.invoke_skill()` async-only since it may trigger fork mode
- `Agent.invoke_skill_sync()` can be a sync wrapper using the existing `run_sync()` pattern

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Nested async context | Fork inside FastAPI endpoint | Runs without deadlock |
| Named subagent config | `agent` field in frontmatter | Delegates to registered config |
| Temporary subagent | No `agent` field | Creates temporary subagent via `spawn_dynamic()` |
| Delegation failure | Subagent errors | Raises `SkillInvocationError` with details |

---

### 5.3 Fix: Explicit Initialization

**Priority**: P1 (High)
**Complexity**: Medium

#### User Stories

**US-003**: As a developer, I want to control when skill and subagent managers are created, without unexpected side effects from property access.

**Acceptance Criteria**:
- [ ] New explicit initialization methods:
  - `agent.init_skills(skills=None, skill_dirs=None)` — creates SkillManager, registers provided skills
  - `agent.init_subagents(subagents=None)` — creates SubagentManager, registers provided configs
- [ ] Accessing `agent.skill_manager` when not initialized raises `AttributeError` or returns `None` (no silent creation)
- [ ] Accessing `agent.subagent_manager` when not initialized raises `AttributeError` or returns `None` (no silent creation)
- [ ] Check properties without triggering init:
  - `agent.has_skill_manager: bool` — True if init_skills() was called
  - `agent.has_subagent_manager: bool` — True if init_subagents() was called
- [ ] Agent constructor auto-calls `init_skills()` if `skills` or `skill_dirs` params are provided
- [ ] Agent constructor auto-calls `init_subagents()` if `subagents` param is provided
- [ ] Remove `_pending_skills`, `_pending_skill_dirs` deferred initialization pattern
- [ ] Calling `init_skills()` or `init_subagents()` multiple times is safe (idempotent or raises clear error)

**Technical Notes**:
- Breaking change: code that accessed `agent.skill_manager` without prior initialization will now fail
- Add deprecation/migration note in docstrings
- The `_is_subagent` flag should prevent initialization of skill/subagent managers in subagent instances

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Access before init | `agent.skill_manager` without init | Raises `AttributeError` with helpful message |
| Double init | `agent.init_skills()` called twice | Idempotent (no-op if already initialized) |
| Init in subagent | Subagent tries `init_skills()` | Raises error (subagents can't have sub-skills) |
| Constructor with params | `Agent(skills=[...])` | Auto-calls `init_skills(skills=[...])` |

---

### 5.4 Fix: UsageTracker Public API

**Priority**: P1 (High)
**Complexity**: Low

#### User Stories

**US-004**: As a developer, I want SubagentManager to aggregate usage through a public UsageTracker API so that internal refactoring of UsageTracker doesn't break subagent tracking.

**Acceptance Criteria**:
- [ ] New public method: `UsageTracker.record_subagent_usage(name: str, usage: TokenUsage) -> None`
- [ ] Method handles creating the per-subagent tracking entry if it doesn't exist
- [ ] Method aggregates usage to both per-subagent breakdown and overall totals
- [ ] `SubagentManager._aggregate_usage()` refactored to use the public method exclusively
- [ ] No direct access to `_subagent_totals` from outside `UsageTracker`
- [ ] Existing `get_subagent_usage()` method continues to work unchanged
- [ ] `_UsageTrackingHandle` updated to use the public method

**Technical Notes**:
- Simple refactoring: extract the existing logic into a public method
- Consider whether `record_subagent_usage` should also update the `record_raw` call that currently happens alongside the `_subagent_totals` mutation
- The `_subagent_totals` attribute can remain private — only access through public methods

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| First usage for a subagent | New subagent name | Entry created automatically |
| Multiple usages same name | Same subagent name repeated | Usage accumulated |
| Zero usage | `TokenUsage()` with all zeros | Accepted without error |

---

### 5.5 Fix: Remove Circular Initialization

**Priority**: P1 (High)
**Complexity**: Medium

#### User Stories

**US-005**: As a developer, I want SkillManager and SubagentManager to be independently constructible without post-construction wiring.

**Acceptance Criteria**:
- [ ] Remove `SkillManager.subagent_manager` setter property
- [ ] Remove any direct reference from `SkillManager` to `SubagentManager`
- [ ] Remove any direct reference from `SubagentManager` to `SkillManager`
- [ ] `skills/integration.py` becomes the sole mediator between the two systems
- [ ] Fork-mode skill activation calls `integration.activate_with_fork()` directly, passing both managers as arguments
- [ ] Circular detection calls `integration.detect_circular_skill_subagent()` with explicit parameters
- [ ] `Agent.init_skills()` and `Agent.init_subagents()` can be called in any order
- [ ] The Agent facade handles passing both managers to the integration module when needed

**Technical Notes**:
- The integration module already exists and handles the cross-cutting concern
- Change `activate_with_fork(skill, arguments, subagent_manager)` signature if needed
- The Agent class becomes the composition root that knows about both managers
- `SkillManager.activate()` returns the skill content; fork delegation is handled by the caller (Agent or integration module)

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Skills without subagents | `agent.init_skills()` only | Works fine; fork-mode skills raise clear error |
| Subagents without skills | `agent.init_subagents()` only | Works fine; pre-loaded skills log warning |
| Fork skill, no subagent manager | Activate fork skill | Raises `SkillInvocationError` explaining subagent manager needed |
| Init order: subagents first | `init_subagents()` then `init_skills()` | Both work correctly |

---

### 5.6 Fix: ReActWorkflow Tool Cleanup

**Priority**: P2 (Medium)
**Complexity**: Low

#### User Stories

**US-006**: As a developer, I want to reuse an Agent instance after running a ReActWorkflow without the `final_answer` tool persisting.

**Acceptance Criteria**:
- [ ] `ReActWorkflow` saves the agent's tool state before registering `final_answer`
- [ ] After workflow completion (success or failure), the agent's tool state is restored
- [ ] The `final_answer` tool is no longer present on the agent after workflow runs
- [ ] Tool state restoration happens in a `finally` block to ensure cleanup on errors
- [ ] `workflow.run()` and `workflow.run_sync()` both perform cleanup
- [ ] Multiple sequential ReActWorkflow runs on the same agent work correctly

**Technical Notes**:
- Save: snapshot the agent's tool list before `__init__()` or at start of `run()`
- Restore: remove `final_answer` tool (or restore from snapshot) after `run()` completes
- Consider moving tool registration from `__init__()` to `run()` for cleaner lifecycle
- Use context manager pattern or try/finally for guaranteed cleanup

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Workflow error mid-run | Exception during execution | Tools still restored (finally block) |
| Sequential workflows | Run ReAct twice on same agent | Second run works, no duplicate tools |
| Agent already has final_answer | User registered own final_answer | Save/restore preserves user's version |
| Concurrent workflows | Two ReAct workflows on same agent | Not supported; document this limitation |

---

## 6. Non-Functional Requirements

### 6.1 Performance Requirements

| Metric | Requirement | Measurement Method |
|--------|-------------|-------------------|
| invoke_skill tool overhead | < 5ms (excluding LLM call) | Unit test with benchmark |
| Async fork delegation | No blocking operations | Profile in async context |
| Init methods | < 100ms for init_skills with 50 skills | Unit test with benchmark |
| Tool state save/restore | < 1ms | Unit test with benchmark |

### 6.2 Compatibility Requirements

- Breaking API changes are acceptable for skills and subagents (experimental APIs)
- Core Agent API (run, run_sync, etc.) unchanged
- pydantic-ai compatibility: work with pydantic-ai >= 0.0.49
- Python 3.12+ required (matches existing requirement)
- Existing v1 tests must continue to pass (with API-level test updates where signatures changed)

### 6.3 Security Requirements

- Trust levels unchanged: untrusted skills still cannot fork, register hooks, or grant excess tool access
- `invoke_skill` tool respects `disable-model-invocation` flag
- No new security surface area introduced

## 7. Technical Architecture

### 7.1 Changes Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Agent (Facade)                                 │
│                                                                          │
│  init_skills()  ──→  SkillManager (independent)                         │
│  init_subagents() ──→  SubagentManager (independent)                    │
│                                                                          │
│  invoke_skill tool ──→  SkillManager.activate()                         │
│                         ──→ [if fork] integration.activate_with_fork()  │
│                                       ──→ SubagentManager.delegate()    │
│                                                                          │
│  UsageTracker.record_subagent_usage() ←── SubagentManager               │
│                                                                          │
│  ReActWorkflow: save tools → run → restore tools                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Single `invoke_skill` tool (not per-skill tools) | Clean separation of skills vs tools; dynamic; namespace-safe; simple model prompt |
| Fully async fork mode | Eliminates deadlock risk; consistent with framework's async-first design |
| Explicit init methods (not lazy) | Prevents surprising side effects; clear lifecycle; easier debugging |
| Public UsageTracker API | Decouples internal state; standard encapsulation practice |
| Integration module as mediator | Single responsibility; both managers independently testable |
| Save/restore tool state | Minimal invasiveness; guaranteed cleanup via finally block |

### 7.3 API Changes

#### New: `invoke_skill` pydantic-ai Tool

```python
# Registered automatically when agent.init_skills() is called

@agent.tool
async def invoke_skill(ctx, name: str, arguments: str = "") -> str:
    """Invoke a registered skill by name.

    Available skills:
    - skill-name-1: Description of skill 1
    - skill-name-2: Description of skill 2

    Args:
        name: The skill name to invoke.
        arguments: Optional arguments to pass to the skill.

    Returns:
        The skill's processed content or execution result.
    """
    ...
```

#### Changed: Agent Initialization

```python
# Before (v1): Lazy initialization with side effects
agent = Agent("gpt-4", skills=[...])
# agent._pending_skills stored, skill_manager created on first access

# After (v2): Explicit initialization
agent = Agent("gpt-4", skills=[...])
# Auto-calls agent.init_skills(skills=[...]) in constructor

# Or manual:
agent = Agent("gpt-4")
agent.init_skills(skills=[...])  # Explicit
agent.init_subagents(subagents=[...])  # Explicit
```

#### Changed: Manager Access

```python
# Before (v1): Access creates manager
if agent.skill_manager:  # CREATES manager!
    ...

# After (v2): Safe checking
if agent.has_skill_manager:  # Just a bool check
    agent.skill_manager.list()  # Access after confirming exists
```

#### New: UsageTracker Method

```python
class UsageTracker:
    def record_subagent_usage(self, name: str, usage: TokenUsage) -> None:
        """Record token usage from a subagent delegation.

        Args:
            name: Subagent config name.
            usage: Token usage to record.
        """
        ...
```

#### Changed: activate_with_fork Signature

```python
# Before (v1): sync with async workaround
def activate_with_fork(
    skill: Skill,
    arguments: str,
    subagent_manager: SubagentManager,
) -> str: ...

# After (v2): fully async
async def activate_with_fork(
    skill: Skill,
    arguments: str,
    subagent_manager: SubagentManager,
) -> str: ...
```

### 7.4 Codebase Context

#### Files to Modify

| File | Change | Fix # |
|------|--------|-------|
| `src/mamba_agents/agent/core.py` | Add init_skills/init_subagents, register invoke_skill tool, remove lazy init | 1, 3, 5 |
| `src/mamba_agents/skills/integration.py` | Make activate_with_fork async, remove ThreadPoolExecutor | 2, 5 |
| `src/mamba_agents/skills/manager.py` | Remove subagent_manager setter, update activate for async | 2, 5 |
| `src/mamba_agents/skills/invocation.py` | Update callers to async where needed | 2 |
| `src/mamba_agents/subagents/manager.py` | Use public UsageTracker API, remove SkillManager reference | 4, 5 |
| `src/mamba_agents/subagents/delegation.py` | Use public UsageTracker API | 4 |
| `src/mamba_agents/tokens/tracker.py` | Add record_subagent_usage method | 4 |
| `src/mamba_agents/workflows/react/workflow.py` | Add tool save/restore around run() | 6 |
| `src/mamba_agents/agent/config.py` | Update AgentConfig if needed for explicit init | 3 |

#### Patterns to Follow

- **Explicit initialization**: Matches pydantic-ai's pattern where toolsets are configured before use
- **Async-first**: All new async code follows the existing `async def` / `run_sync()` pattern
- **Facade delegation**: Agent class delegates to managers, integration module bridges cross-cutting concerns
- **Error encapsulation**: `invoke_skill` tool returns error strings rather than raising, matching pydantic-ai tool patterns

### 7.5 Technical Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| pydantic-ai tool registration API | invoke_skill tool must match pydantic-ai's tool interface | Use `@agent.tool` decorator or `tools` parameter |
| Breaking API changes | Existing code using lazy init will break | Document migration, mark as experimental API change |
| Async propagation | Making fork async requires callers to be async | Follow existing async/sync wrapper pattern |
| Tool state introspection | Need to snapshot/restore pydantic-ai's tool list | Investigate pydantic-ai's tool management API |

## 8. Scope Definition

### 8.1 In Scope

- Wire skills into `agent.run()` via single `invoke_skill` pydantic-ai tool
- Redesign `activate_with_fork()` as fully async
- Replace lazy property initialization with explicit `init_skills()` / `init_subagents()`
- Add `record_subagent_usage()` public method to UsageTracker
- Remove bidirectional dependency between SkillManager and SubagentManager
- Add tool state save/restore to ReActWorkflow
- Update all affected tests
- Add regression tests for each fixed fragility point

### 8.2 Out of Scope

- **New features**: No new capabilities beyond fixing the 6 fragility points
- **Performance optimization**: Not a goal unless directly related to a fix
- **Removing experimental label**: Separate decision after fixes land
- **Additional fragility points**: Only the 6 documented issues
- **Documentation updates beyond CLAUDE.md**: External docs updates deferred

### 8.3 Future Considerations

- Removing "experimental" label after these fixes are validated
- Agent teams / parallel coordination (build on stabilized subagents)
- Skill marketplace integration
- Dynamic tool description updates for invoke_skill (re-generate when skills change)

## 9. Implementation Plan

### 9.1 Phase 1: Foundation Fixes

**Completion Criteria**: UsageTracker public API added, circular initialization removed, explicit init methods in place.

| Deliverable | Description | Technical Tasks | Dependencies |
|-------------|-------------|-----------------|--------------|
| UsageTracker public API | `record_subagent_usage()` method | Add method to `tokens/tracker.py`, update SubagentManager | None |
| Remove circular init | Integration module as sole mediator | Remove setter from SkillManager, update manager signatures | None |
| Explicit initialization | `init_skills()` / `init_subagents()` | Refactor Agent constructor, add has_* properties | Circular init fix |

**Checkpoint Gate**:
- [ ] `UsageTracker.record_subagent_usage()` works with existing tests
- [ ] No direct access to `_subagent_totals` from outside `UsageTracker`
- [ ] SkillManager constructible without SubagentManager reference
- [ ] `agent.has_skill_manager` works without triggering initialization
- [ ] All existing tests passing (with API-level updates)

---

### 9.2 Phase 2: Core Fixes

**Completion Criteria**: Async fork mode working, skills wired into agent.run(), ReActWorkflow cleanup working.

| Deliverable | Description | Technical Tasks | Dependencies |
|-------------|-------------|-----------------|--------------|
| Async fork mode | Fully async `activate_with_fork()` | Rewrite integration.py, update callers | Phase 1 (circular init fix) |
| invoke_skill tool | Wire skills into pydantic-ai | Register tool in init_skills(), implement invoke logic | Phase 1 (explicit init) |
| ReAct cleanup | Tool state save/restore | Add save/restore to workflow.py | None |

**Checkpoint Gate**:
- [ ] Fork mode works in nested async context (test with `asyncio.run()` + inner event loop)
- [ ] Model can invoke skills during `agent.run()` via invoke_skill tool
- [ ] `disable-model-invocation` flag respected
- [ ] ReActWorkflow does not leave `final_answer` tool on agent
- [ ] All existing tests passing

---

### 9.3 Phase 3: Verification

**Completion Criteria**: All regression tests written, coverage targets met, CLAUDE.md updated.

| Deliverable | Description | Technical Tasks | Dependencies |
|-------------|-------------|-----------------|--------------|
| Regression tests | One test per fragility point | 6 targeted regression tests | Phase 1 + 2 |
| Coverage verification | >= 80% per changed module | Run coverage, fill gaps | All above |
| Documentation update | Update CLAUDE.md fragility points section | Remove resolved issues, update API docs | All above |

**Checkpoint Gate**:
- [ ] 6 regression tests passing, each specifically testing a resolved fragility point
- [ ] >= 80% coverage on all changed modules
- [ ] CLAUDE.md updated: resolved fragility points removed or marked as fixed
- [ ] All existing tests still passing
- [ ] No new fragility points introduced

## 10. Testing Strategy

### 10.1 Test Levels

| Level | Scope | Tools | Coverage Target |
|-------|-------|-------|-----------------|
| Unit | Individual classes/functions | pytest, TestModel | >= 80% per module |
| Integration | Cross-module interactions | pytest, TestModel | Critical paths |
| Regression | Each fragility point fix | pytest | 6 specific tests |

### 10.2 Regression Test Scenarios

#### Regression 1: Skills Invocable During agent.run()

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create Agent with skills and TestModel | Agent created |
| 2 | Configure TestModel to call invoke_skill tool | Tool invocation prepared |
| 3 | Call agent.run() | Model invokes invoke_skill, skill activates |
| 4 | Verify skill content in response | Skill's processed body returned |

#### Regression 2: Fork Mode in Async Context

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create skill with execution_mode: "fork" | Skill configured |
| 2 | Activate skill inside running event loop | No deadlock |
| 3 | Verify subagent delegation completes | Result returned |

#### Regression 3: No Lazy Init Side Effects

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create Agent without skills | Agent created |
| 2 | Check `agent.has_skill_manager` | Returns False |
| 3 | Access `agent.skill_manager` | Raises AttributeError (not silently creates) |

#### Regression 4: UsageTracker Public API

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Delegate task to subagent | Subagent runs |
| 2 | Check parent usage tracker | Usage recorded via public API |
| 3 | Verify no private attribute access | Grep test confirms no `_subagent_totals` access |

#### Regression 5: No Circular Initialization

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create SkillManager without SubagentManager | No error |
| 2 | Create SubagentManager without SkillManager | No error |
| 3 | Init skills first, then subagents | Both work |
| 4 | Init subagents first, then skills | Both work |

#### Regression 6: ReAct Tool Cleanup

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Record agent's tool count | N tools |
| 2 | Run ReActWorkflow | Workflow completes |
| 3 | Verify agent's tool count | Still N tools (final_answer removed) |

### 10.3 Existing Test Preservation

- All ~10k lines of existing tests in `tests/unit/test_skill*`, `tests/unit/test_subagent*`, and `tests/integration/test_skills_subagents.py` must continue to pass
- Tests that directly test removed APIs (lazy init behavior, `SkillManager.subagent_manager` setter) should be updated to test the new APIs
- Test file structure should be preserved

## 11. Dependencies

### 11.1 Technical Dependencies

| Dependency | Status | Risk if Delayed |
|------------|--------|-----------------|
| pydantic-ai >= 0.0.49 | Available | Low — already in use |
| pydantic-ai tool registration API | Available | Low — standard feature |
| asyncio | stdlib | None |

### 11.2 No Cross-Team Dependencies

This is a self-contained refactoring within the mamba-agents framework.

## 12. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| pydantic-ai tool API changes | High | Low | Pin version, add defensive checks, test tool registration |
| Async propagation complexity | Medium | Medium | Follow existing async/sync wrapper pattern; limit scope of async changes |
| Existing test breakage | High | Medium | Run full test suite after each phase; update tests incrementally |
| invoke_skill tool confusion | Low | Low | Clear tool description; document that skills != tools |
| Performance regression | Low | Low | Benchmark critical paths before/after |

## 13. Open Questions

| # | Question | Resolution |
|---|----------|------------|
| — | No open questions | All requirements gathered during interview |

## 14. Appendix

### 14.1 Glossary

| Term | Definition |
|------|------------|
| Fragility Point | A documented area of code that is prone to failure, unexpected behavior, or maintenance risk |
| invoke_skill | A pydantic-ai tool registered with the Agent that enables the model to invoke skills during agent.run() |
| Fork Mode | Skill execution mode where the skill body is delegated to a subagent for isolated execution |
| Explicit Initialization | Requiring an explicit method call (init_skills/init_subagents) rather than lazy creation on property access |
| Mediator Pattern | Using an intermediate module (integration.py) to bridge two subsystems without direct cross-references |

### 14.2 References

- [Original Skills and Subagents PRD](../internal/specs/skills-and-subagents-SPEC.md) — v1 specification
- [Agent Skills Specification](https://agentskills.io/specification) — Open standard for portable agent skills
- [CLAUDE.md Known Fragility Points](./CLAUDE.md) — Documentation of the 6 issues being addressed

### 14.3 Agent Recommendations (Accepted)

The following recommendations were suggested based on industry best practices and accepted during the interview:

1. **Architecture — Integration Module as Mediator**: Use `skills/integration.py` as the sole mediator between SkillManager and SubagentManager, eliminating the bidirectional dependency. Both managers become independently constructible and testable.

2. **API Design — Single invoke_skill Tool**: Register a single `invoke_skill(name, arguments)` pydantic-ai tool rather than per-skill tools. Provides clean separation between skills and tools, dynamic availability, namespace safety, and simpler model prompts.

### 14.4 Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Stephen Sequenzia | Initial version |

---

*Document generated by SDD Tools*
