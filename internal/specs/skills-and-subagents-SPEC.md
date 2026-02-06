# Skills and Subagents PRD

**Version**: 1.0
**Author**: Stephen Sequenzia
**Date**: 2026-02-05
**Status**: Draft
**Spec Type**: New feature
**Spec Depth**: Full technical documentation
**Description**: Skills and Subagents — two critical components for modularity, reusability, and hierarchical task delegation in the mamba-agents framework.

---

## 1. Executive Summary

Mamba Agents currently operates as a single-agent framework with no built-in mechanisms for modular capability composition or hierarchical task delegation. This PRD specifies two new subsystems — **Skills** and **Subagents** — that transform mamba-agents into a fully modular agent framework. Skills follow the [Agent Skills](https://agentskills.io) open standard with mamba-specific extensions, while Subagents enable isolated, configurable child agents that handle delegated tasks independently.

## 2. Problem Statement

### 2.1 The Problem

Mamba Agents lacks two foundational capabilities that modern agent frameworks require:

1. **No modularity**: All agent logic lives in a single Agent instance. There is no way to package, share, or reuse specialized capabilities across agents or projects.
2. **No reusability**: Developers must re-implement common behaviors (code review, web search, data analysis) for every agent they build.
3. **No task delegation**: Agents cannot break complex tasks into subtasks handled by specialized child agents with their own context windows, tool access, and model configurations.

These limitations force developers into monolithic agent designs that are difficult to maintain, test, and scale.

### 2.2 Current State

- **Tools** can be registered with agents (`tools=[...]`), but they are simple functions with no packaging, discovery, or metadata.
- **MCP integration** provides external tool servers, but these are runtime services, not portable capability packages.
- **Workflows** (ReAct) orchestrate multi-step execution but within a single agent context — no delegation to child agents.
- **PromptManager** handles templates but has no concept of packaged instructions or progressive loading.

### 2.3 Impact Analysis

Without Skills and Subagents:
- Developers cannot build modular, composable agent systems
- Enterprise teams cannot standardize agent capabilities across projects
- The framework cannot compete with Claude Code, LangChain, or CrewAI which all support multi-agent patterns
- Complex tasks requiring different models or tool sets must be handled by a single, over-provisioned agent

### 2.4 Business Value

- **Competitive parity**: Skills and Subagents bring mamba-agents in line with industry-leading agent frameworks
- **Ecosystem growth**: The Agent Skills open standard enables a portable skill ecosystem shared across tools (Claude Code, Cursor, Gemini CLI, etc.)
- **Developer productivity**: Reusable skills and delegated subagents reduce boilerplate and enable faster agent development
- **Enterprise adoption**: Modular capabilities with validation and trust levels address enterprise security and governance requirements

## 3. Goals & Success Metrics

### 3.1 Primary Goals

1. Implement a Skills system that follows the Agent Skills open standard (agentskills.io) with mamba-specific extensions
2. Implement a Subagent system that enables isolated, configurable child agents for task delegation
3. Establish the bi-directional relationship where skills load into subagents AND skills can delegate to subagents

### 3.2 Success Metrics

| Metric | Current Baseline | Target | Measurement Method |
|--------|------------------|--------|-------------------|
| Skill loading from files | Not supported | Functional with progressive disclosure | Unit + integration tests |
| Subagent delegation | Not supported | Sync + async delegation working | Unit + integration tests |
| Test coverage (skills/) | N/A | >= 80% | pytest --cov |
| Test coverage (subagents/) | N/A | >= 80% | pytest --cov |
| API compatibility with Agent Skills spec | N/A | Full compliance with spec validation | skills-ref validate |

### 3.3 Non-Goals

- **Agent teams / parallel coordination**: Multi-agent teams with shared task lists and inter-agent messaging (future release)
- **Persistent cross-session memory**: Cross-conversation learning for subagents (future release)
- **Skill marketplace**: Publishing, discovering, or installing skills from a central registry (future release)
- **Skill authoring tools**: CLI commands or wizards for creating new skills (future release)

## 4. User Research

### 4.1 Target Users

#### Primary Persona: AI Application Developer
- **Role/Description**: Software engineer building production AI applications with mamba-agents
- **Goals**: Build modular, maintainable agents that compose specialized capabilities; delegate complex tasks to purpose-built child agents
- **Pain Points**: Forced to put all logic in one agent; can't reuse agent behaviors across projects; no way to use different models for different subtasks
- **Context**: Building AI-powered applications, chatbots, automation tools
- **Technical Proficiency**: High — comfortable with Python, pydantic, async programming

#### Secondary Persona: AI Researcher
- **Role/Description**: Researcher experimenting with multi-agent architectures
- **Goals**: Prototype hierarchical agent systems; test different delegation strategies; compare single-agent vs multi-agent approaches
- **Pain Points**: Must build delegation infrastructure from scratch; can't easily isolate agent contexts for experiments

#### Tertiary Persona: Enterprise Team Lead
- **Role/Description**: Technical lead standardizing agent capabilities across an organization
- **Goals**: Create reusable skill packages that all teams can use; enforce consistent tool access and security policies across agents
- **Pain Points**: No way to share agent capabilities across projects; can't enforce governance on what agents can do

### 4.2 User Journey Map

```
[Developer needs modular agent] --> [Creates SKILL.md] --> [Agent discovers & loads skill] --> [Skill tools available] --> [Agent uses skill capabilities]
                                         |
                                         v
[Developer needs task delegation] --> [Defines SubagentConfig] --> [Parent spawns subagent] --> [Subagent executes in isolation] --> [Result returned to parent]
```

### 4.3 User Workflows

#### Workflow 1: Skill Registration (File-based)

```
Developer creates skills/web-search/SKILL.md
    --> Agent discovers skill on startup (metadata only)
    --> User/model triggers skill activation
    --> Full SKILL.md body loaded into context
    --> Skill's tools registered with agent
    --> Skill's references loaded on-demand
```

#### Workflow 2: Skill Registration (Programmatic)

```
Developer creates Skill instance in Python
    --> Calls agent.register_skill(skill) or SkillManager.register(skill)
    --> Skill metadata indexed
    --> Skill tools available immediately
```

#### Workflow 3: Subagent Delegation (Sync)

```
Parent agent encounters complex subtask
    --> Spawns subagent with SubagentConfig (model, tools, system_prompt)
    --> Subagent runs in isolated context
    --> Subagent returns AgentResult
    --> Parent processes result, continues main task
    --> Subagent usage aggregated to parent's tracker
```

#### Workflow 4: Subagent Delegation (Async)

```
Parent agent needs parallel research
    --> Spawns multiple subagents asynchronously
    --> Continues own work while subagents execute
    --> Collects results as subagents complete
    --> Synthesizes findings from all subagents
```

## 5. Functional Requirements

### 5.1 Feature: Skill Loader & Parser

**Priority**: P0 (Critical)
**Complexity**: Medium

#### User Stories

**US-001**: As a developer, I want to create a `SKILL.md` file with YAML frontmatter and markdown instructions so that my agent can discover and load specialized capabilities.

**Acceptance Criteria**:
- [ ] Parse SKILL.md files with YAML frontmatter (name, description required)
- [ ] Support all Agent Skills spec fields: name, description, license, compatibility, metadata, allowed-tools
- [ ] Support mamba extensions: model, context, disable-model-invocation, user-invocable, hooks, argument-hint
- [ ] Validate frontmatter against schema (name format: lowercase alphanumeric + hyphens, max 64 chars)
- [ ] Load markdown body as skill instructions
- [ ] Detect and index optional directories: scripts/, references/, assets/

**Technical Notes**:
- Use `yaml` (PyYAML) for frontmatter parsing — already available via pydantic
- Validate name field matches parent directory name (per spec)
- Store parsed skill as `SkillInfo` dataclass with metadata fields

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Missing frontmatter | SKILL.md without `---` markers | Raise `SkillParseError` with clear message |
| Missing required fields | Frontmatter without `name` | Raise `SkillValidationError` listing missing fields |
| Invalid name format | `name: My-SKILL` (uppercase) | Raise `SkillValidationError` with format requirements |
| Name mismatch | Dir `foo/` but `name: bar` | Raise `SkillValidationError` noting mismatch |
| Empty body | Frontmatter only, no instructions | Accept (skill is metadata-only, valid per spec) |
| Large body (>5000 tokens) | Very long SKILL.md | Accept but log warning about recommended size |

**Error Handling**:
| Error Condition | Error Type | Description |
|-----------------|------------|-------------|
| File not found | `SkillNotFoundError` | Skill path does not exist |
| Invalid YAML | `SkillParseError` | Frontmatter YAML syntax error |
| Schema violation | `SkillValidationError` | Frontmatter fields fail validation |
| IO error | `SkillLoadError` | Permission denied or disk error |

---

### 5.2 Feature: Skill Discovery & Registry

**Priority**: P0 (Critical)
**Complexity**: High

#### User Stories

**US-002**: As a developer, I want my agent to automatically discover skills from configured directories so that I don't need to manually register each skill.

**US-003**: As a developer, I want to register skills programmatically via Python so that I can create skills dynamically at runtime.

**Acceptance Criteria**:
- [ ] Auto-discover skills from three-level directory hierarchy:
  - Project: `.mamba/skills/` (relative to working directory)
  - User: `~/.mamba/skills/` (user home)
  - Custom: Additional configurable search paths
- [ ] Priority order: project > user > custom (higher priority wins on name conflict)
- [ ] Progressive disclosure loading: metadata at startup, body on activation, references on demand
- [ ] Programmatic registration: `SkillManager.register(skill)` accepts `Skill` instances
- [ ] Skill deregistration: `SkillManager.deregister(name)` removes a skill
- [ ] List all skills: `SkillManager.list()` returns all registered skill metadata
- [ ] Get skill by name: `SkillManager.get(name)` returns full skill or None
- [ ] Name conflict detection: raise `SkillConflictError` when same-priority skills share a name
- [ ] Tool namespace prefixing: skill tools prefixed with `{skill_name}.{tool_name}` (configurable)

**Technical Notes**:
- Follow `ToolRegistry` pattern for the registry implementation
- Follow `MCPClientManager` pattern for lifecycle management
- Use `Path.glob("*/SKILL.md")` for directory scanning
- Metadata loading should be synchronous (fast); body loading can be lazy
- Thread-safe registry for concurrent access

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Empty skills directory | `.mamba/skills/` exists but empty | No error, empty registry |
| Duplicate names across scopes | Project and user both have `web-search` | Project wins (higher priority), log info |
| Duplicate names same scope | Two `web-search/` in project dir | Raise `SkillConflictError` |
| Skill dir without SKILL.md | `skills/broken/` (no SKILL.md) | Skip directory, log warning |
| Circular references | SKILL.md references itself | Detect and raise `SkillLoadError` |

---

### 5.3 Feature: Skill Invocation & Arguments

**Priority**: P0 (Critical)
**Complexity**: Medium

#### User Stories

**US-004**: As a developer, I want to control when skills are invoked (by the model, by the user, or programmatically) so that I can manage skill activation.

**US-005**: As a developer, I want to pass arguments to skills with `$ARGUMENTS` substitution so that skills can receive dynamic input.

**Acceptance Criteria**:
- [ ] Invocation control via frontmatter flags:
  - `disable-model-invocation: true` — only user/code can invoke
  - `user-invocable: false` — only model/code can invoke
  - Default: both model and user can invoke
- [ ] Argument substitution:
  - `$ARGUMENTS` replaced with full argument string
  - `$ARGUMENTS[N]` or `$N` for positional access (0-indexed)
  - If no `$ARGUMENTS` in content, arguments appended as `ARGUMENTS: <value>`
- [ ] Skill activation lifecycle:
  1. Check invocation permissions
  2. Load full SKILL.md body (if not already loaded)
  3. Perform argument substitution
  4. Register skill's allowed-tools with agent
  5. Return processed skill content
- [ ] Skill deactivation: restore previous tool state when skill completes

**Technical Notes**:
- Argument parsing: split on whitespace, preserve quoted strings
- Substitution should handle missing positional args gracefully (empty string)
- Tool registration during activation must be reversible

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| No arguments passed | Skill with `$ARGUMENTS` placeholder | Replace with empty string |
| More args than placeholders | `/skill arg1 arg2 arg3` but only `$0` used | Extra args available via `$ARGUMENTS` |
| Fewer args than placeholders | `$0 $1 $2` but only 1 arg passed | `$1` and `$2` become empty strings |
| Argument with special chars | `$ARGUMENTS` = `"hello world"` | Preserve quoted content as single argument |

---

### 5.4 Feature: Skill Validation & Trust

**Priority**: P1 (High)
**Complexity**: Medium

#### User Stories

**US-006**: As an enterprise team lead, I want skills to be validated against the schema and assigned trust levels so that untrusted skills cannot access sensitive capabilities.

**Acceptance Criteria**:
- [ ] Frontmatter validation against Agent Skills spec + mamba extensions schema
- [ ] Trust level configuration: `trusted` or `untrusted` (default: `trusted` for project skills, `untrusted` for custom paths)
- [ ] Untrusted skills:
  - Cannot use `allowed-tools` to grant tool access beyond what the agent already permits
  - Cannot use `hooks` to register lifecycle hooks
  - Cannot use `context: fork` to spawn subagents
  - Tools are sandboxed (no filesystem access unless explicitly granted)
- [ ] Validation report: `SkillManager.validate(skill_path)` returns validation results
- [ ] Configurable trust per directory: `SkillConfig.trusted_paths` list

**Technical Notes**:
- Validation should use pydantic model parsing for schema enforcement
- Trust levels should be checked at skill activation time, not at discovery
- Consider using the `skills-ref` reference library for spec compliance validation

---

### 5.5 Feature: Skill Testing Utilities

**Priority**: P2 (Medium)
**Complexity**: Low

#### User Stories

**US-007**: As a skill author, I want a `SkillTestHarness` utility so that I can test my skills in isolation without setting up a full Agent instance.

**Acceptance Criteria**:
- [ ] `SkillTestHarness` class that:
  - Loads a skill from a directory or programmatic definition
  - Validates frontmatter and body
  - Simulates invocation with test arguments
  - Verifies tool registrations
  - Returns structured test results
- [ ] Integration with pytest via fixtures: `@pytest.fixture def skill_harness()`
- [ ] Support for testing skill content after argument substitution

**Technical Notes**:
- Follow the `TestModel` pattern from pydantic-ai for deterministic testing
- Harness should not require a real LLM model

---

### 5.6 Feature: Subagent Configuration

**Priority**: P0 (Critical)
**Complexity**: Medium

#### User Stories

**US-008**: As a developer, I want to define subagents via both markdown files and Python code so that I can choose the approach that fits my workflow.

**Acceptance Criteria**:
- [ ] Markdown-based definition:
  - `.mamba/agents/{name}.md` files with YAML frontmatter
  - Frontmatter fields: name, description, tools, disallowed-tools, model, permission-mode, skills
  - Markdown body becomes the subagent's system prompt
- [ ] Programmatic definition:
  - `SubagentConfig` pydantic model with all configuration fields
  - `SubagentManager.register(config)` for pre-registration
- [ ] Configuration fields:
  - `name: str` — unique identifier (required)
  - `description: str` — when to delegate to this subagent (required)
  - `model: str | None` — model override (None = inherit from parent)
  - `tools: list[str | Callable] | None` — explicit tool allowlist (None = no tools)
  - `disallowed_tools: list[str] | None` — tools to deny
  - `system_prompt: str | TemplateConfig | None` — custom system prompt
  - `skills: list[str] | None` — skills to pre-load at startup
  - `max_turns: int` — maximum conversation turns (default: 50)
  - `config: AgentConfig | None` — full agent config override
- [ ] Discovery from `.mamba/agents/` directory (project-level)
- [ ] Discovery from `~/.mamba/agents/` directory (user-level)

**Technical Notes**:
- Follow MCP's config pattern (`MCPServerConfig` → `MCPClientManager`)
- Markdown parsing reuses skill loader's frontmatter parser
- Pre-loaded skills inject full skill content into subagent's system prompt

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Missing name | Config without name field | Raise `SubagentConfigError` |
| Invalid model | `model: "nonexistent-model"` | Error surfaces at delegation time, not config time |
| Empty tools list | `tools: []` | Subagent has no tool access (valid, read-only subagent) |
| Skill not found | `skills: ["missing-skill"]` | Raise `SkillNotFoundError` at subagent startup |

---

### 5.7 Feature: Subagent Manager & Spawning

**Priority**: P0 (Critical)
**Complexity**: High

#### User Stories

**US-009**: As a developer, I want to spawn subagents both from pre-configured definitions and dynamically at runtime so that I can handle both planned and ad-hoc delegation patterns.

**Acceptance Criteria**:
- [ ] `SubagentManager` class that:
  - Stores pre-configured `SubagentConfig` definitions
  - Spawns subagent Agent instances from configs
  - Tracks active subagents and their status
  - Enforces no-nesting rule (subagents cannot spawn sub-subagents)
- [ ] Pre-configured spawning: `manager.spawn("config-name", task="...")` creates subagent from registered config
- [ ] Dynamic spawning: `manager.spawn_dynamic(config=SubagentConfig(...), task="...")` creates ad-hoc subagent
- [ ] Subagent lifecycle:
  - Created: config validated, Agent instance initialized
  - Running: executing delegated task
  - Completed: result available
  - Failed: error captured
- [ ] Context isolation (configurable):
  - Default: fresh context (subagent gets only task + system prompt)
  - Optional: inject parent messages via `context_messages: list[dict]`
  - Optional: inject specific context string via `context: str`
- [ ] Model selection: subagent uses its configured model, or inherits parent's model
- [ ] Tool restriction: only tools in the allowlist are available to the subagent

**Technical Notes**:
- Each subagent is a full `Agent` instance with its own `ContextManager`, `UsageTracker`, etc.
- Use `Agent(model, config=AgentConfig(...), tools=[...])` for subagent creation
- No-nesting enforced by setting a flag on subagent's `AgentConfig` (e.g., `_is_subagent: bool`)
- Subagent Agent instances should be garbage-collected after result is returned (no persistent state)

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Spawn from unknown config | `spawn("nonexistent")` | Raise `SubagentNotFoundError` |
| Nesting attempt | Subagent tries to spawn sub-subagent | Raise `SubagentNestingError` |
| Parent context injection | `context_messages=[...]` | Messages injected as subagent's initial history |
| Empty task | `spawn("config", task="")` | Raise `SubagentError` — task is required |
| Concurrent spawns | Multiple `spawn()` calls | Each gets independent Agent instance |

---

### 5.8 Feature: Subagent Delegation (Sync & Async)

**Priority**: P0 (Critical)
**Complexity**: High

#### User Stories

**US-010**: As a developer, I want to delegate tasks to subagents synchronously (wait for result) and asynchronously (continue working) so that I can choose the right pattern for each use case.

**Acceptance Criteria**:
- [ ] Synchronous delegation:
  - `result = await manager.delegate(config_name, task)` — waits for completion
  - `result = manager.delegate_sync(config_name, task)` — sync wrapper
  - Returns `SubagentResult` with output, usage, and metadata
- [ ] Asynchronous delegation:
  - `handle = await manager.delegate_async(config_name, task)` — returns immediately
  - `result = await handle.result()` — wait for completion
  - `handle.is_complete` — check status without blocking
  - `handle.cancel()` — cancel running subagent
- [ ] `SubagentResult` includes:
  - `output: str` — subagent's final response
  - `agent_result: AgentResult` — full pydantic-ai result wrapper
  - `usage: TokenUsage` — token usage for this delegation
  - `duration: float` — execution time in seconds
  - `subagent_name: str` — which subagent handled it
  - `success: bool` — whether delegation completed successfully
  - `error: str | None` — error message if failed
- [ ] Token tracking:
  - Subagent usage tracked separately in `SubagentResult.usage`
  - Aggregated to parent's `UsageTracker` automatically
  - Parent can query `usage_tracker.get_subagent_usage()` for breakdown

**Technical Notes**:
- Sync delegation wraps `agent.run_sync(task)` on the subagent
- Async delegation wraps `agent.run(task)` with `asyncio.Task`
- Use `asyncio.create_task()` for background execution
- Token aggregation requires extending `UsageTracker.record_usage()` to accept source tags

**Edge Cases**:
| Scenario | Input | Expected Behavior |
|----------|-------|-------------------|
| Subagent timeout | Task runs longer than `max_turns` | Return `SubagentResult(success=False, error="Max turns exceeded")` |
| Model API error | Subagent's model fails | Capture error, return failed `SubagentResult` |
| Cancel after completion | `handle.cancel()` on finished task | No-op, result already available |
| Parent context injection | `delegate(..., context_messages=[...])` | Pass messages as subagent's initial history |

---

### 5.9 Feature: Skills ↔ Subagents Integration

**Priority**: P1 (High)
**Complexity**: Medium

#### User Stories

**US-011**: As a developer, I want subagents to be pre-loaded with specific skills so that they have domain expertise from startup.

**US-012**: As a developer, I want skills to delegate part of their work to subagents via `context: fork` so that heavy processing runs in an isolated context.

**Acceptance Criteria**:
- [ ] Skill pre-loading into subagents:
  - `SubagentConfig.skills: list[str]` specifies skill names to pre-load
  - Full skill content (SKILL.md body) injected into subagent's system prompt at startup
  - Skill's tools registered with the subagent
  - Skills resolved from the parent's `SkillManager`
- [ ] Skill-to-subagent delegation:
  - `context: fork` in SKILL.md frontmatter triggers subagent execution
  - `agent` frontmatter field specifies which subagent config to use
  - Skill content becomes the subagent's task prompt
  - Result returned to the invoking context

**Technical Notes**:
- Skill pre-loading appends skill content to system prompt (similar to Claude Code)
- `context: fork` creates a temporary, anonymous subagent for the skill's execution
- The `agent` field maps to registered `SubagentConfig` names, or defaults to a general-purpose config

---

### 5.10 Feature: Agent Facade Integration

**Priority**: P0 (Critical)
**Complexity**: Medium

#### User Stories

**US-013**: As a developer, I want Skills and Subagents accessible through the Agent class's facade API so that the interface remains simple and consistent.

**Acceptance Criteria**:
- [ ] Agent constructor accepts new parameters:
  - `skills: list[Skill | str | Path] | None` — skills to register (Skill instances, names, or paths)
  - `skill_dirs: list[str | Path] | None` — additional directories to scan for skills
  - `subagents: list[SubagentConfig] | None` — pre-configured subagent definitions
- [ ] Agent facade methods for skills:
  - `agent.register_skill(skill)` — register a skill
  - `agent.get_skill(name)` — get a skill by name
  - `agent.list_skills()` — list all registered skills
  - `agent.invoke_skill(name, *args)` — activate and invoke a skill
- [ ] Agent facade methods for subagents:
  - `agent.delegate(config_name, task, **kwargs)` — sync delegation
  - `agent.delegate_async(config_name, task, **kwargs)` — async delegation
  - `agent.register_subagent(config)` — register a subagent config
  - `agent.list_subagents()` — list registered subagent configs
- [ ] Agent properties:
  - `agent.skill_manager` — access to SkillManager instance
  - `agent.subagent_manager` — access to SubagentManager instance

**Technical Notes**:
- Follow existing facade patterns (e.g., `agent.context_manager`, `agent.usage_tracker`)
- Skills and subagents should be optional — Agent works fine without them
- Lazy initialization: managers created on first access, not in constructor

---

## 6. Non-Functional Requirements

### 6.1 Performance Requirements

| Metric | Requirement | Measurement Method |
|--------|-------------|-------------------|
| Skill directory scan | < 100ms for 50 skills | Unit test with benchmark |
| Skill metadata loading | < 1ms per skill | Unit test with benchmark |
| Skill body loading | < 10ms per skill | Unit test with benchmark |
| Subagent spawn time | < 50ms (excluding LLM call) | Unit test with benchmark |
| Memory overhead per skill (metadata only) | < 1KB | Memory profiling |

### 6.2 Security Requirements

#### Skill Validation
- All SKILL.md files validated against schema before activation
- Frontmatter fields type-checked and constraint-validated
- Invalid skills rejected with clear error messages

#### Trust Levels
| Trust Level | Capabilities | Default For |
|-------------|-------------|-------------|
| Trusted | Full access: allowed-tools, hooks, context:fork, all frontmatter extensions | Project skills (`.mamba/skills/`) |
| Untrusted | Limited: no hooks, no context:fork, allowed-tools restricted to agent's existing tools | Custom path skills |

#### Subagent Isolation
- Subagents run in isolated context windows by default
- Tool access restricted to explicit allowlist
- No access to parent's internal state (context manager, usage tracker)
- Subagents cannot spawn sub-subagents (enforced)

### 6.3 Scalability Requirements

- Support 100+ registered skills without performance degradation (metadata only in memory)
- Support 10+ concurrent subagent delegations (async)
- Progressive disclosure ensures context window usage scales with active skills, not total skills

### 6.4 Compatibility Requirements

- Agent Skills spec compliance: validate with `skills-ref validate`
- Backward compatible: existing Agent usage without skills/subagents unchanged
- pydantic-ai compatibility: work with pydantic-ai >= 0.0.49
- Python 3.12+ required (matches existing requirement)

## 7. Technical Architecture

### 7.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Agent (Facade)                                 │
│                                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   Context    │  │    Usage     │  │    Token     │  │   Prompt    │  │
│  │   Manager   │  │   Tracker    │  │   Counter    │  │   Manager   │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  └─────────────┘  │
│                                                                          │
│  ┌─────────────────────────────┐  ┌────────────────────────────────┐    │
│  │      Skill Manager          │  │      Subagent Manager          │    │
│  │  ┌───────┐  ┌───────────┐  │  │  ┌───────────┐  ┌──────────┐  │    │
│  │  │Loader │  │ Registry  │  │  │  │ Configs   │  │ Spawner  │  │    │
│  │  └───────┘  └───────────┘  │  │  └───────────┘  └──────────┘  │    │
│  │  ┌───────┐  ┌───────────┐  │  │  ┌───────────┐  ┌──────────┐  │    │
│  │  │Parser │  │ Validator │  │  │  │ Tracker   │  │Delegator │  │    │
│  │  └───────┘  └───────────┘  │  │  └───────────┘  └──────────┘  │    │
│  └─────────────────────────────┘  └────────────────────────────────┘    │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    pydantic-ai Agent (wrapped)                      │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
            │  Subagent 1 │ │  Subagent 2 │ │  Subagent N │
            │  (Agent)    │ │  (Agent)    │ │  (Agent)    │
            │  - model    │ │  - model    │ │  - model    │
            │  - tools    │ │  - tools    │ │  - tools    │
            │  - context  │ │  - context  │ │  - context  │
            │  - skills   │ │  - skills   │ │  - skills   │
            └─────────────┘ └─────────────┘ └─────────────┘
```

### 7.2 Tech Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| Configuration | pydantic / pydantic-settings | Matches existing config patterns |
| Frontmatter parsing | PyYAML (via pydantic) | Already a dependency |
| Markdown parsing | Standard string processing | No heavy library needed for body extraction |
| Async execution | asyncio | Already used throughout codebase |
| File discovery | pathlib.Path.glob | Standard library, already used |
| Testing | pytest + TestModel | Matches existing test infrastructure |

### 7.3 Data Models

#### SkillInfo

```python
@dataclass
class SkillInfo:
    """Metadata about a discovered skill (loaded eagerly)."""
    name: str                          # Skill identifier (validated)
    description: str                   # What the skill does
    path: Path                         # Directory containing SKILL.md
    scope: SkillScope                  # project | user | custom
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, str] | None = None
    allowed_tools: list[str] | None = None
    model: str | None = None
    context: str | None = None         # "fork" or None
    agent: str | None = None           # Subagent config name for fork
    disable_model_invocation: bool = False
    user_invocable: bool = True
    argument_hint: str | None = None
    hooks: dict | None = None
    trust_level: TrustLevel = TrustLevel.TRUSTED
```

#### Skill

```python
class Skill(BaseModel):
    """Full skill with loaded content."""
    info: SkillInfo                    # Metadata (always loaded)
    body: str | None = None            # SKILL.md markdown body (lazy loaded)
    is_active: bool = False            # Whether skill is currently activated
    _tools: list[Callable] = []        # Registered tools (private)
```

#### SkillConfig

```python
class SkillConfig(BaseModel):
    """Configuration for the skill subsystem."""
    skills_dirs: list[Path] = Field(
        default_factory=lambda: [Path(".mamba/skills")],
        description="Directories to scan for skills"
    )
    user_skills_dir: Path = Field(
        default=Path("~/.mamba/skills"),
        description="User-level skills directory"
    )
    custom_paths: list[Path] = Field(
        default_factory=list,
        description="Additional search paths"
    )
    auto_discover: bool = Field(
        default=True,
        description="Auto-discover skills on startup"
    )
    namespace_tools: bool = Field(
        default=True,
        description="Prefix skill tools with skill name"
    )
    trusted_paths: list[Path] = Field(
        default_factory=list,
        description="Paths to treat as trusted (in addition to project/user)"
    )
```

#### SubagentConfig

```python
class SubagentConfig(BaseModel):
    """Configuration for a subagent definition."""
    name: str = Field(description="Unique subagent identifier")
    description: str = Field(description="When to delegate to this subagent")
    model: str | None = Field(default=None, description="Model override (None=inherit)")
    tools: list[str | Callable] | None = Field(
        default=None, description="Explicit tool allowlist"
    )
    disallowed_tools: list[str] | None = Field(
        default=None, description="Tools to deny"
    )
    system_prompt: str | TemplateConfig | None = Field(
        default=None, description="Custom system prompt"
    )
    skills: list[str] | None = Field(
        default=None, description="Skills to pre-load"
    )
    max_turns: int = Field(default=50, description="Maximum conversation turns")
    config: AgentConfig | None = Field(
        default=None, description="Full agent config override"
    )
```

#### SubagentResult

```python
@dataclass
class SubagentResult:
    """Result from a subagent delegation."""
    output: str                        # Subagent's final response text
    agent_result: AgentResult          # Full pydantic-ai result wrapper
    usage: TokenUsage                  # Token usage for this delegation
    duration: float                    # Execution time in seconds
    subagent_name: str                 # Which subagent handled it
    success: bool                      # Whether delegation completed
    error: str | None = None           # Error message if failed
```

#### DelegationHandle

```python
@dataclass
class DelegationHandle:
    """Handle for tracking async subagent delegation."""
    subagent_name: str
    task: str
    _task: asyncio.Task | None = None

    @property
    def is_complete(self) -> bool: ...
    async def result(self) -> SubagentResult: ...
    def cancel(self) -> None: ...
```

#### Enums

```python
class SkillScope(str, Enum):
    """Skill discovery scope."""
    PROJECT = "project"
    USER = "user"
    CUSTOM = "custom"

class TrustLevel(str, Enum):
    """Skill trust level."""
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
```

#### Entity Relationships

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    Agent     │ 1───* │    Skill     │ *───* │   Subagent   │
│  (parent)    │       │ (registered) │       │  (spawned)   │
└──────────────┘       └──────────────┘       └──────────────┘
       │                      │                      │
       │ has                  │ loaded into          │ is-a
       ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ SkillManager │       │  SkillInfo   │       │    Agent     │
└──────────────┘       │  (metadata)  │       │   (child)    │
       │               └──────────────┘       └──────────────┘
       │ has
       ▼
┌──────────────┐
│  Subagent    │
│  Manager     │
└──────────────┘
```

### 7.4 Python API Specifications

#### SkillManager API

```python
class SkillManager:
    """Manages skill discovery, registration, and lifecycle."""

    def __init__(self, config: SkillConfig | None = None) -> None: ...

    # Discovery
    def discover(self) -> list[SkillInfo]:
        """Scan configured directories for skills. Returns metadata only."""

    # Registration
    def register(self, skill: Skill | SkillInfo | Path) -> None:
        """Register a skill (from instance, info, or path)."""

    def deregister(self, name: str) -> None:
        """Remove a skill from the registry."""

    # Retrieval
    def get(self, name: str) -> Skill | None:
        """Get a skill by name. Loads body if not already loaded."""

    def list(self) -> list[SkillInfo]:
        """List all registered skill metadata."""

    # Activation
    def activate(self, name: str, arguments: str = "") -> str:
        """Activate a skill, perform argument substitution, return processed content."""

    def deactivate(self, name: str) -> None:
        """Deactivate a skill, restore previous tool state."""

    # Validation
    def validate(self, path: Path) -> ValidationResult:
        """Validate a skill against the schema."""

    # Tool integration
    def get_tools(self, name: str) -> list[Callable]:
        """Get tools registered by a specific skill."""

    def get_all_tools(self) -> list[Callable]:
        """Get all tools from all active skills (with namespace prefixes)."""
```

#### SubagentManager API

```python
class SubagentManager:
    """Manages subagent configuration, spawning, and delegation."""

    def __init__(
        self,
        parent_agent: Agent,
        configs: list[SubagentConfig] | None = None,
        skill_manager: SkillManager | None = None,
    ) -> None: ...

    # Configuration
    def register(self, config: SubagentConfig) -> None:
        """Register a subagent configuration."""

    def deregister(self, name: str) -> None:
        """Remove a subagent configuration."""

    def list(self) -> list[SubagentConfig]:
        """List registered subagent configurations."""

    def get(self, name: str) -> SubagentConfig | None:
        """Get a subagent configuration by name."""

    # Synchronous delegation
    async def delegate(
        self,
        config_name: str,
        task: str,
        *,
        context_messages: list[dict] | None = None,
        context: str | None = None,
    ) -> SubagentResult:
        """Delegate a task to a subagent and wait for result."""

    def delegate_sync(
        self,
        config_name: str,
        task: str,
        **kwargs,
    ) -> SubagentResult:
        """Synchronous wrapper for delegate()."""

    # Asynchronous delegation
    async def delegate_async(
        self,
        config_name: str,
        task: str,
        *,
        context_messages: list[dict] | None = None,
        context: str | None = None,
    ) -> DelegationHandle:
        """Delegate a task asynchronously, return handle for tracking."""

    # Dynamic spawning
    async def spawn_dynamic(
        self,
        config: SubagentConfig,
        task: str,
        **kwargs,
    ) -> SubagentResult:
        """Spawn an ad-hoc subagent from a runtime config."""

    # Tracking
    def get_active_delegations(self) -> list[DelegationHandle]:
        """List currently active (running) delegations."""

    def get_usage_breakdown(self) -> dict[str, TokenUsage]:
        """Get token usage broken down by subagent name."""
```

### 7.5 Integration Points

| System | Type | Purpose |
|--------|------|---------|
| Agent (core.py) | Internal | Facade methods, constructor params, property access |
| ToolRegistry | Internal | Skill tools registered via existing tool system |
| MCPClientManager | Internal | Skills may reference MCP servers as toolsets |
| UsageTracker | Internal | Subagent token usage aggregated to parent |
| ContextManager | Internal | Context injection for non-isolated subagents |
| AgentSettings | Internal | Nested SkillConfig and SubagentConfig |
| PromptManager | Internal | Skill system prompts via TemplateConfig |

### 7.6 Technical Constraints

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| pydantic-ai pre-1.0 API | Message types, Model API may change | Pin `>=0.0.49`, add defensive type checks |
| No subagent nesting | Limits complex multi-tier delegation | Use workflows for orchestration beyond 1 level |
| Context window limits | Many pre-loaded skills consume tokens | Progressive disclosure + lazy loading |
| Circular import risk | skills/ → agent/, subagents/ → agent/ | Lazy imports, TYPE_CHECKING guards |

## 8. Scope Definition

### 8.1 In Scope

- SKILL.md loader and parser (Agent Skills spec compliant)
- Skill discovery from project, user, and custom directories
- Skill registry with programmatic and file-based registration
- Skill invocation control and argument substitution
- Skill validation and trust levels
- Skill tool namespace prefixing
- SkillTestHarness testing utility
- Subagent configuration (markdown and Python)
- Subagent manager with pre-configured and dynamic spawning
- Synchronous and asynchronous delegation
- Per-subagent and aggregated token tracking
- Context isolation (configurable)
- Skill pre-loading into subagents
- Skill-to-subagent delegation via `context: fork`
- Agent facade integration (constructor params, methods, properties)
- Error hierarchy (SkillError, SubagentError families)
- Unit and integration tests

### 8.2 Out of Scope

- **Agent teams / parallel coordination**: Multi-agent teams with shared task lists and inter-agent messaging. This is a higher-order pattern that can be built on top of subagents in a future release.
- **Persistent cross-session memory**: Cross-conversation learning for subagents (e.g., saving findings to disk). Deferred until core subagent patterns are stable.
- **Skill marketplace**: Publishing, discovering, or installing skills from a central registry. Requires infrastructure beyond the framework itself.
- **Skill authoring CLI**: Commands for scaffolding new skills (e.g., `mamba skill create`). Nice-to-have but not essential for v1.
- **Dynamic context injection (`!`command``)**: Shell command preprocessing in skill content. Complex feature, can be added later.
- **Subagent hooks**: Lifecycle hooks scoped to subagent execution (SubagentStart, SubagentStop). Can be added when the hook system is more mature.

### 8.3 Future Considerations

- Agent teams with shared task lists and inter-agent messaging
- Persistent memory scopes (user, project, local) for subagents
- Skill marketplace integration
- Skill versioning and dependency resolution
- Dynamic context injection in skill content
- Subagent lifecycle hooks
- Skill authoring CLI tools
- Remote subagent execution (different processes/machines)

## 9. Implementation Plan

### 9.1 Phase 1: Skills System (Foundation)

**Completion Criteria**: Skills can be loaded from files, registered programmatically, discovered from directories, validated, and their metadata queried.

| Deliverable | Description | Technical Tasks | Dependencies |
|-------------|-------------|-----------------|--------------|
| Skill data models | `SkillInfo`, `Skill`, `SkillConfig`, enums | Create `skills/config.py`, define pydantic models | None |
| Skill loader/parser | Parse SKILL.md frontmatter + body | Create `skills/loader.py`, YAML parsing, validation | Data models |
| Skill registry | In-memory skill registration and lookup | Create `skills/registry.py`, thread-safe dict | Data models |
| Skill discovery | Auto-scan directories for skills | Create `skills/discovery.py`, directory scanning | Loader, registry |
| Skill validation | Schema validation and trust levels | Create `skills/validator.py`, pydantic validation | Data models |
| Skill errors | Error hierarchy | Create `skills/errors.py` | None |
| Skill invocation | Activation, argument substitution, tool registration | Add to `skills/registry.py` | Loader, registry |
| SkillManager | Top-level manager composing all components | Create `skills/manager.py` | All above |
| Unit tests | Test all skill components | Create `tests/unit/test_skills/` | All above |

**Checkpoint Gate**:
- [ ] `skills-ref validate` passes on test skills
- [ ] Programmatic registration works end-to-end
- [ ] File-based discovery works with project/user/custom paths
- [ ] Progressive disclosure verified (metadata vs body loading)
- [ ] All unit tests passing with >= 80% coverage

---

### 9.2 Phase 2: Subagents System (Core Features)

**Completion Criteria**: Subagents can be configured, spawned (pre-configured and dynamic), and delegated to (sync and async) with isolated contexts and token tracking.

| Deliverable | Description | Technical Tasks | Dependencies |
|-------------|-------------|-----------------|--------------|
| Subagent data models | `SubagentConfig`, `SubagentResult`, `DelegationHandle` | Create `subagents/config.py` | None |
| Subagent spawning | Create Agent instances from configs | Create `subagents/spawner.py` | Data models, Agent |
| Sync delegation | Synchronous task delegation | Create `subagents/delegation.py` | Spawner |
| Async delegation | Asynchronous task delegation with handles | Extend `subagents/delegation.py` | Spawner |
| Token tracking | Per-subagent and aggregated usage | Extend `UsageTracker`, create tracking in delegation | Delegation |
| Context injection | Configurable context isolation/sharing | Add to spawner, use ContextManager | Spawner |
| No-nesting enforcement | Block sub-subagent spawning | Add `_is_subagent` flag to AgentConfig | Spawner |
| SubagentManager | Top-level manager composing all components | Create `subagents/manager.py` | All above |
| File-based config | Load subagent configs from .mamba/agents/ | Create `subagents/loader.py` | Data models |
| Subagent errors | Error hierarchy | Create `subagents/errors.py` | None |
| Unit + integration tests | Test all subagent components | Create `tests/unit/test_subagents/` | All above |

**Checkpoint Gate**:
- [ ] Sync delegation works end-to-end with TestModel
- [ ] Async delegation works with concurrent subagents
- [ ] Token usage correctly aggregated to parent
- [ ] Context isolation verified (subagent has independent history)
- [ ] No-nesting rule enforced
- [ ] All tests passing with >= 80% coverage

---

### 9.3 Phase 3: Integration

**Completion Criteria**: Skills and Subagents are integrated bi-directionally and accessible through the Agent facade.

| Deliverable | Description | Technical Tasks | Dependencies |
|-------------|-------------|-----------------|--------------|
| Skills ↔ Subagents | Skill pre-loading + context:fork delegation | Wire SkillManager into SubagentManager | Phase 1 + 2 |
| Agent facade - skills | Constructor params, methods, properties | Extend `agent/core.py` | Phase 1 |
| Agent facade - subagents | Constructor params, methods, properties | Extend `agent/core.py` | Phase 2 |
| AgentConfig extensions | Skill and subagent config fields | Extend `agent/config.py` | Phase 1 + 2 |
| AgentSettings extensions | Nested SkillConfig and SubagentConfig | Extend `config/settings.py` | Phase 1 + 2 |
| Root exports | Export new public API symbols | Update `__init__.py` files | All above |
| SkillTestHarness | Testing utility for skill authors | Create `skills/testing.py` | Phase 1 |
| Integration tests | End-to-end skill+subagent workflows | Create `tests/integration/` | All above |
| Documentation | Update CLAUDE.md, docstrings | Update docs | All above |

**Checkpoint Gate**:
- [ ] `Agent("gpt-4", skills=[...], subagents=[...])` works
- [ ] Skill pre-loading into subagents verified
- [ ] `context: fork` delegation verified
- [ ] Agent facade methods work consistently
- [ ] All exports importable from `mamba_agents`
- [ ] CLAUDE.md updated with new architecture
- [ ] All tests passing, overall coverage >= 50% (project target)

## 10. Testing Strategy

### 10.1 Test Levels

| Level | Scope | Tools | Coverage Target |
|-------|-------|-------|-----------------|
| Unit | Individual classes/functions | pytest, TestModel | >= 80% per module |
| Integration | Cross-module interactions | pytest, TestModel | Critical paths |

### 10.2 Test Scenarios

#### Critical Path: Skill Loading & Activation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Create SKILL.md with valid frontmatter | File parses without error |
| 2 | Discover skills from directory | Skill metadata appears in registry |
| 3 | Activate skill with arguments | Body loaded, arguments substituted, tools registered |
| 4 | Deactivate skill | Tools deregistered, state restored |

#### Critical Path: Subagent Delegation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Register SubagentConfig | Config stored in manager |
| 2 | Delegate task synchronously | Subagent runs, result returned with output + usage |
| 3 | Check parent usage tracker | Subagent usage aggregated |
| 4 | Delegate task asynchronously | Handle returned immediately, result available later |

#### Critical Path: Skill-Subagent Integration

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Configure subagent with `skills: ["web-search"]` | Skill content injected into system prompt |
| 2 | Delegate to skill-loaded subagent | Subagent has skill knowledge and tools |
| 3 | Activate skill with `context: fork` | Skill content executed in isolated subagent |

### 10.3 Test Fixtures

```python
# tests/conftest.py additions

@pytest.fixture
def sample_skill_dir(tmp_path: Path) -> Path:
    """Create a temporary skill directory with test skills."""
    skill_dir = tmp_path / "skills" / "test-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("""---
name: test-skill
description: A test skill for unit testing
allowed-tools: Read, Grep
---

This is a test skill. Process: $ARGUMENTS
""")
    return tmp_path / "skills"

@pytest.fixture
def sample_subagent_config() -> SubagentConfig:
    """Provide a sample subagent configuration."""
    return SubagentConfig(
        name="test-subagent",
        description="Test subagent for delegation",
        model=None,  # inherit
        tools=["read_file"],
        max_turns=5,
    )
```

## 11. Directory Structure

### 11.1 New Source Files

```
src/mamba_agents/
├── skills/
│   ├── __init__.py           # Public API: SkillManager, Skill, SkillInfo, SkillConfig
│   ├── config.py             # SkillConfig, SkillInfo, Skill, enums
│   ├── loader.py             # SKILL.md parser (frontmatter + body)
│   ├── discovery.py          # Directory scanning and skill discovery
│   ├── registry.py           # In-memory skill registry
│   ├── manager.py            # SkillManager (top-level facade)
│   ├── validator.py          # Schema validation and trust level enforcement
│   ├── invocation.py         # Argument substitution and activation lifecycle
│   ├── testing.py            # SkillTestHarness utility
│   └── errors.py             # SkillError hierarchy
├── subagents/
│   ├── __init__.py           # Public API: SubagentManager, SubagentConfig, SubagentResult
│   ├── config.py             # SubagentConfig, SubagentResult, DelegationHandle
│   ├── loader.py             # Load configs from .mamba/agents/ markdown files
│   ├── spawner.py            # Create Agent instances from configs
│   ├── delegation.py         # Sync and async delegation logic
│   ├── manager.py            # SubagentManager (top-level facade)
│   └── errors.py             # SubagentError hierarchy
```

### 11.2 New Test Files

```
tests/
├── unit/
│   ├── test_skills/
│   │   ├── __init__.py
│   │   ├── test_loader.py        # SKILL.md parsing tests
│   │   ├── test_discovery.py     # Directory scanning tests
│   │   ├── test_registry.py      # Registration and lookup tests
│   │   ├── test_manager.py       # SkillManager integration tests
│   │   ├── test_validator.py     # Validation and trust level tests
│   │   ├── test_invocation.py    # Argument substitution tests
│   │   └── test_config.py        # Config model tests
│   ├── test_subagents/
│   │   ├── __init__.py
│   │   ├── test_config.py        # SubagentConfig model tests
│   │   ├── test_loader.py        # Markdown config loading tests
│   │   ├── test_spawner.py       # Agent creation tests
│   │   ├── test_delegation.py    # Sync and async delegation tests
│   │   ├── test_manager.py       # SubagentManager integration tests
│   │   └── test_nesting.py       # No-nesting enforcement tests
│   ├── test_agent_skills.py      # Agent facade skill methods
│   └── test_agent_subagents.py   # Agent facade subagent methods
```

## 12. Dependencies

### 12.1 Technical Dependencies

| Dependency | Status | Risk if Delayed |
|------------|--------|-----------------|
| pydantic-ai >= 0.0.49 | Available | Low — already in use |
| PyYAML | Available (via pydantic) | None — already a transitive dependency |
| asyncio | stdlib | None |
| pathlib | stdlib | None |

### 12.2 No Cross-Team Dependencies

This is a self-contained feature within the mamba-agents framework. No external team coordination required.

## 13. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| Complexity creep | High | Medium | Strictly follow "thin wrapper" philosophy. Each component should be < 300 lines. Review against YAGNI at each checkpoint. |
| API surface instability | High | Medium | Mark new APIs as "experimental" in v1. Use `__all__` exports to control public surface. Gather feedback before stabilizing. |
| pydantic-ai breaking changes | High | Medium | Pin minimum version, add defensive type checks in message handling, maintain adapter layer for compatibility. |
| Circular imports (skills ↔ agent ↔ subagents) | Medium | Medium | Use lazy imports, `TYPE_CHECKING` guards, and keep module boundaries clean. |
| Context window exhaustion from skills | Medium | Low | Progressive disclosure is mandatory. Enforce SKILL.md size warnings. Metadata-only loading at startup. |
| Tool name conflicts | Medium | Low | Namespace prefixing enabled by default. Clear error messages on conflict detection. |

## 14. Open Questions

| # | Question | Resolution |
|---|----------|------------|
| — | No open questions | All requirements gathered during interview |

## 15. Appendix

### 15.1 Glossary

| Term | Definition |
|------|------------|
| Skill | A packaged set of instructions, tools, and resources that extend an agent's capabilities. Follows the Agent Skills open standard. |
| Subagent | A child Agent instance spawned by a parent agent to handle a delegated task in isolation. |
| SKILL.md | The required entry point file for a skill, containing YAML frontmatter metadata and markdown instructions. |
| Progressive Disclosure | A loading strategy where skill content is loaded in three tiers: metadata (always), body (on activation), references (on demand). |
| Delegation | The act of a parent agent sending a task to a subagent for execution. |
| DelegationHandle | An async handle for tracking background subagent execution. |
| Namespace Prefixing | Prepending skill name to tool names (e.g., `web_search.fetch`) to prevent conflicts. |
| Trust Level | A security classification (trusted/untrusted) that controls what capabilities a skill can access. |
| Context Isolation | Running a subagent with its own independent conversation history, separate from the parent. |

### 15.2 References

- [Agent Skills Specification](https://agentskills.io/specification) — Open standard for portable agent skills
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills) — Reference implementation of skills in Claude Code
- [Claude Code Subagents Documentation](https://code.claude.com/docs/en/sub-agents) — Reference implementation of subagents in Claude Code
- [Claude Plugins Skill Development Guide](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/plugin-dev/skills/skill-development/SKILL.md) — Best practices for skill authoring
- [Agent Skills GitHub Repository](https://github.com/agentskills/agentskills) — Open standard repository with reference library

### 15.3 Agent Recommendations (Accepted)

The following recommendations were suggested based on industry best practices and accepted during the interview:

1. **API Design — Tool Namespace Prefixing**: Skill tools are prefixed with the skill name (e.g., `web_search.fetch_page`) to prevent name conflicts when multiple skills are active. Follows the pattern established by MCP's `tool_prefix`.

2. **Security — Skill Validation & Trust Levels**: Skills are validated against the schema before activation. Trust levels (trusted/untrusted) control what capabilities a skill can access. Untrusted skills cannot register hooks, spawn subagents, or grant tool access beyond the agent's existing permissions.

3. **Architecture — Progressive Disclosure Loading**: Skills use a three-tier loading pattern: metadata (~100 tokens) loaded at startup, full body loaded on activation, reference files loaded on demand. Minimizes context window usage.

4. **Testing — SkillTestHarness**: A utility class for testing skills in isolation without requiring a full Agent instance. Follows the `TestModel` pattern for deterministic testing.

### 15.4 Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-05 | Stephen Sequenzia | Initial version |

---

*Document generated by SDD Tools*
