# Spec Analysis Report: Skills and Subagents PRD

**Analyzed**: 2026-02-05 16:30
**Spec Path**: internal/specs/skills-and-subagents-SPEC.md
**Detected Depth Level**: Full-Tech
**Status**: Initial

---

## Summary

| Category | Critical | Warning | Suggestion | Total |
|----------|----------|---------|------------|-------|
| Inconsistencies | 1 | 2 | 0 | 3 |
| Missing Information | 1 | 3 | 1 | 5 |
| Ambiguities | 0 | 3 | 1 | 4 |
| Structure Issues | 0 | 1 | 0 | 1 |
| **Total** | **2** | **9** | **2** | **13** |

### Overall Assessment

This is a well-structured, comprehensive Full-Tech spec that covers the Skills and Subagents systems thoroughly. The data models, API signatures, and implementation plan are detailed and actionable. The main areas for improvement are: resolving inconsistencies between the functional requirements and the API specifications, defining referenced but undefined types (`ValidationResult`, error hierarchy details), and clarifying overloaded terminology (the `context` field serves different purposes in different locations).

---

## Findings

### Critical

#### FIND-001: Facade Delegation Method Conflicts with Async API Signature

- **Category**: Inconsistencies
- **Location**: Section 5.10 "Agent Facade Integration" (line 519) vs Section 5.8 / Section 7.4
- **Issue**: Section 5.10 defines `agent.delegate(config_name, task, **kwargs)` as "sync delegation" on the Agent facade (line 519). However, Section 5.8 and the SubagentManager API (Section 7.4, line 866) define `delegate()` as an `async` method (`async def delegate(...)`) and provide `delegate_sync()` as the synchronous wrapper. The facade's `delegate()` cannot be both sync and async.
- **Impact**: Developers will encounter confusion about whether `agent.delegate()` is sync or async, leading to runtime errors (missing `await`) or design conflicts during implementation.
- **Recommendation**: Align the Agent facade API with SubagentManager. Either (a) make `agent.delegate()` async and add `agent.delegate_sync()` as the sync wrapper, matching the SubagentManager pattern, or (b) clarify that `agent.delegate()` is a sync convenience that internally calls `delegate_sync()`.
- **Status**: Pending

---

#### FIND-002: ValidationResult Type Referenced but Never Defined

- **Category**: Missing Information
- **Location**: Section 7.4 "SkillManager API" (line 828)
- **Issue**: The `SkillManager.validate()` method returns `ValidationResult`, but this type is never defined anywhere in the spec -- not in the data models (Section 7.3), not in the enums, and not in the directory structure files.
- **Impact**: Implementers will have to invent the `ValidationResult` type without guidance, leading to inconsistency with the rest of the system. This is a core part of the skill validation feature (Section 5.4), which is P1 priority.
- **Recommendation**: Add a `ValidationResult` data model definition to Section 7.3. It should include at minimum: `valid: bool`, `errors: list[str]`, `warnings: list[str]`, and optionally `skill_name: str` and `trust_level: TrustLevel`.
- **Status**: Pending

---

### Warnings

#### FIND-003: Spawn vs Delegate Naming Mismatch Between Requirements and API

- **Category**: Inconsistencies
- **Location**: Section 5.7 (line 391) vs Section 7.4 (line 839)
- **Issue**: Section 5.7 describes spawning methods as `manager.spawn("config-name", task="...")` and `manager.spawn_dynamic(config=..., task="...")`. The API specification in Section 7.4 defines `delegate()` and `delegate_async()` for task execution, and `spawn_dynamic()` for ad-hoc subagents -- but there is no `spawn()` method that accepts a task string. The functional requirements use "spawn" terminology while the API uses "delegate" terminology.
- **Recommendation**: Unify the naming. Either update Section 5.7 to use `delegate()` and `delegate_async()` language, or add a `spawn()` method to the API that maps to `delegate()`.
- **Status**: Pending

---

#### FIND-004: SkillManager.register() Signature Inconsistency

- **Category**: Inconsistencies
- **Location**: Section 5.2 (line 211) vs Section 7.4 (line 807)
- **Issue**: Section 5.2 acceptance criteria states `SkillManager.register(skill)` accepts `Skill` instances for programmatic registration. Section 7.4 defines the signature as `register(self, skill: Skill | SkillInfo | Path) -> None`, which accepts three types. The broader signature is likely correct, but the functional requirement understates the capability.
- **Recommendation**: Update Section 5.2 acceptance criteria to mention that `register()` accepts `Skill`, `SkillInfo`, or `Path` instances, matching the API specification.
- **Status**: Pending

---

#### FIND-005: Permission-Mode Field Missing from SubagentConfig Data Model

- **Category**: Missing Information
- **Location**: Section 5.6 (line 343) vs Section 7.3 (line 700)
- **Issue**: Section 5.6 lists `permission-mode` as a frontmatter field for markdown-based subagent definitions (line 343), but the `SubagentConfig` data model in Section 7.3 does not include a `permission_mode` field. Either this field needs to be added to the model or removed from the requirements.
- **Recommendation**: Decide whether `permission-mode` is needed and either add `permission_mode: str | None = None` to `SubagentConfig` or remove it from the Section 5.6 frontmatter field list.
- **Status**: Pending

---

#### FIND-006: Hooks Field Undefined

- **Category**: Missing Information
- **Location**: Section 7.3 "SkillInfo" (line 652)
- **Issue**: `SkillInfo` has a `hooks: dict | None` field, and Section 5.4 states that untrusted skills "Cannot use `hooks` to register lifecycle hooks." However, the spec never defines what hooks are available, what the dict structure looks like, or how hooks are registered and executed.
- **Recommendation**: Either define the hooks system (supported hook names, dict schema, execution model) in the data models or technical architecture section, or explicitly defer hooks to a future release and remove the field from `SkillInfo`.
- **Status**: Pending

---

#### FIND-007: Reference Loading Mechanism Unspecified

- **Category**: Missing Information
- **Location**: Section 5.1 (line 166) and Section 4.3 (line 116)
- **Issue**: Progressive disclosure is described as three tiers: metadata (startup), body (activation), references (on demand). The spec mentions detecting `references/` directories (line 166) and loading references on-demand (line 116), but never specifies how references are loaded, what formats are supported, how they're injected into context, or what API is used to request them.
- **Recommendation**: Add a brief description of the reference loading mechanism. At minimum, specify: what file formats are supported in `references/`, how a skill or model requests a reference, and how reference content is delivered (appended to context, returned as tool output, etc.).
- **Status**: Pending

---

#### FIND-008: Context Field Overloaded with Different Semantics

- **Category**: Ambiguities
- **Location**: Section 7.3 "SkillInfo" (line 647) and Section 5.8 (line 871)
- **Issue**: The name `context` is used with different meanings: in `SkillInfo`, `context: str | None` means `"fork"` or `None` (a mode flag). In `SubagentManager.delegate()`, `context: str | None` is an arbitrary string to inject into the subagent. In `SubagentConfig`, `config: AgentConfig | None` is yet another context-adjacent concept. This overloading will confuse implementers and API users.
- **Recommendation**: Rename the `SkillInfo.context` field to something more specific like `execution_mode: str | None` or `invocation_mode: str | None` to distinguish it from the delegation context injection parameter.
- **Status**: Pending

---

#### FIND-009: Thread Safety Model Unclear

- **Category**: Ambiguities
- **Location**: Section 5.2 "Technical Notes" (line 223)
- **Issue**: The spec requires "Thread-safe registry for concurrent access" but does not specify the concurrency model. Python has the GIL for CPU-bound operations but requires explicit synchronization for asyncio concurrent access. It is unclear whether "thread-safe" means using `threading.Lock`, `asyncio.Lock`, or both.
- **Recommendation**: Specify the concurrency model. Since the codebase is asyncio-first (per the architecture docs), state whether the registry should use `asyncio.Lock` for async safety, `threading.Lock` for thread safety, or both. Note whether the registry needs to support concurrent access from multiple event loops.
- **Status**: Pending

---

#### FIND-010: Skill Deactivation Trigger Undefined

- **Category**: Ambiguities
- **Location**: Section 5.3 (line 262)
- **Issue**: The acceptance criteria state "Skill deactivation: restore previous tool state when skill completes." However, skills are not tasks with a defined completion point -- they are capability packages. The spec does not define what triggers deactivation. Is it explicit (`deactivate(name)`), automatic after a conversation turn, or tied to some other lifecycle event?
- **Recommendation**: Clarify the deactivation model. Likely, deactivation is explicit via `SkillManager.deactivate(name)` (which is defined in Section 7.4). Update Section 5.3 to say "Skill deactivation via `deactivate(name)`: restore previous tool state" to make the trigger explicit.
- **Status**: Pending

---

#### FIND-011: skills-ref Tool Not Explained

- **Category**: Ambiguities
- **Location**: Section 3.2 (line 67) and Section 6.4 (line 574) and Section 9.1 (line 994)
- **Issue**: The spec references `skills-ref validate` as a validation tool in three places (success metrics, compatibility requirements, and checkpoint gate) but never explains what `skills-ref` is, where it comes from, whether it's a dependency that needs to be installed, or how it integrates with the validation system.
- **Recommendation**: Add a brief note explaining `skills-ref` -- is it from the Agent Skills GitHub repository? Is it a CLI tool or a Python library? Should it be added to dev dependencies? This context is needed for implementers to set up the validation pipeline.
- **Status**: Pending

---

#### FIND-012: Pydantic BaseModel Private Attribute Incorrect Syntax

- **Category**: Missing Information
- **Location**: Section 7.3 "Skill" data model (line 664)
- **Issue**: The `Skill` class extends `BaseModel` and defines `_tools: list[Callable] = []`. In pydantic v2, private attributes on BaseModel must use `PrivateAttr`: `_tools: list[Callable] = PrivateAttr(default_factory=list)`. The current syntax would be silently ignored or raise a validation error.
- **Recommendation**: Update the `Skill` data model to use `PrivateAttr` for the `_tools` field: `_tools: list[Callable] = PrivateAttr(default_factory=list)`. Also add the import note.
- **Status**: Pending

---

### Suggestions

#### FIND-013: Missing Deployment/Release Plan Section

- **Category**: Structure Issues
- **Location**: Between Section 10 and Section 11
- **Issue**: The Full-Tech checklist expects a deployment plan section covering deployment strategy, rollback procedures, and environment requirements. While this is a library feature (not a service), a release plan noting version bumping, migration path for existing users, and feature flag/experimental API marking would be valuable -- especially since Section 13 mentions marking APIs as "experimental."
- **Recommendation**: Add a brief Section 10.5 or similar covering: (1) How to release (version bump, changelog update), (2) Whether new APIs are marked experimental, (3) Migration notes for existing Agent users (backward compatibility verification).
- **Status**: Pending

---

## Analysis Methodology

This analysis was performed using depth-aware criteria for Full-Tech specs:

- **Sections Checked**: All 15 sections including Executive Summary, Problem Statement, Goals & Success Metrics, User Research, Functional Requirements (10 features), Non-Functional Requirements, Technical Architecture, Scope Definition, Implementation Plan, Testing Strategy, Directory Structure, Dependencies, Risks, Open Questions, and Appendix.
- **Criteria Applied**: Full Technical Documentation Checklist including system architecture, API specifications, data models, performance SLAs, testing strategy, and deployment plan. Cross-depth quality checks for internal consistency, completeness, measurability, and clarity.
- **Out of Scope**: HTTP API endpoint validation (this is a Python library, not a service), database schema checks, deployment infrastructure review.
