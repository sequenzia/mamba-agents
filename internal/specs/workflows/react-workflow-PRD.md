# Product Requirements Document: ReAct Workflow

## Executive Summary

This PRD defines the requirements for implementing a ReAct (Reasoning and Acting) workflow in the mamba-agents framework. ReAct is an agentic paradigm that synergizes reasoning and acting by having LLMs generate verbal reasoning traces (thoughts) and task-specific actions in an interleaved manner, enabling dynamic reasoning and plan adjustment.

---

## 1. Overview

### 1.1 Background

The ReAct paradigm, introduced by Yao et al. (2023), combines chain-of-thought reasoning with action execution in an iterative loop. Unlike single-shot approaches, ReAct agents decide incrementally: **Observe → Reason → Act → Observe → Reason again**. This creates a continuous thought-action loop ideal for interactive, tool-using agents.

### 1.2 Goals

- Implement a production-ready `ReActWorkflow` class extending the existing `Workflow` base class
- Provide configurable reasoning trace exposure (visible vs internal)
- Support both confidence-based and tool-based termination strategies
- Integrate deeply with context compaction and token tracking systems
- Maintain consistency with existing framework patterns and conventions

### 1.3 Non-Goals

- Multi-agent ReAct (using separate reasoning vs execution agents)
- ReAct variants like Reflexion or Tree of Thoughts (future iterations)
- Custom prompt engineering UI/tooling

---

## 2. User Stories

### 2.1 Core User Stories

| ID | As a... | I want to... | So that... |
|----|---------|--------------|------------|
| US-1 | Developer | Create a ReAct agent with minimal configuration | I can quickly prototype reasoning+acting workflows |
| US-2 | Developer | See the agent's reasoning traces in workflow state | I can debug and understand the agent's decision process |
| US-3 | Developer | Hide reasoning traces from output | I can use ReAct internally without exposing implementation details |
| US-4 | Developer | Configure termination via a "final_answer" tool | The agent explicitly signals task completion |
| US-5 | Developer | Configure termination via confidence threshold | The workflow stops when the agent is confident in its answer |
| US-6 | Developer | Have context automatically compacted mid-workflow | Long-running tasks don't fail due to context limits |
| US-7 | Developer | Access token usage across the entire ReAct loop | I can track costs and optimize prompts |
| US-8 | Developer | Hook into thought/action/observation steps | I can add logging, metrics, or custom behavior |

### 2.2 Example Usage

```python
from mamba_agents import Agent
from mamba_agents.workflows import ReActWorkflow, ReActConfig
from mamba_agents.tools import read_file, run_bash, grep_search

# Create agent with tools
agent = Agent(
    "gpt-4o",
    system_prompt="You are a helpful coding assistant.",
    tools=[read_file, run_bash, grep_search],
)

# Create ReAct workflow
workflow = ReActWorkflow(
    agent=agent,
    config=ReActConfig(
        max_iterations=15,
        expose_reasoning=True,  # Show Thought steps
        termination_strategy="tool",  # Use final_answer tool
    ),
)

# Execute workflow
result = workflow.run_sync("Find and fix the bug in src/utils.py")

# Access results
print(result.output)  # Final answer
print(result.state.steps)  # All Thought/Action/Observation steps
print(workflow.agent.get_cost())  # Total cost across all iterations
```

---

## 3. Technical Requirements

### 3.1 Core Components

#### 3.1.1 ReActConfig

Extends `WorkflowConfig` with ReAct-specific settings:

```python
class ReActConfig(WorkflowConfig):
    """Configuration for ReAct workflow execution."""

    # Reasoning trace visibility
    expose_reasoning: bool = True  # Whether Thought steps appear in WorkflowState
    reasoning_prefix: str = "Thought: "  # Prefix for reasoning in prompts
    action_prefix: str = "Action: "  # Prefix for action in prompts
    observation_prefix: str = "Observation: "  # Prefix for observations

    # Termination strategy
    # NOTE: Only "tool" termination is implemented in MVP.
    # "confidence" and "hybrid" are planned for future implementation.
    termination_strategy: Literal["tool", "confidence", "hybrid"] = "tool"
    confidence_threshold: float = 0.9  # For confidence-based termination (future)
    final_answer_tool_name: str = "final_answer"  # Tool name for tool-based termination

    # Context management
    auto_compact_in_workflow: bool = True  # Trigger compaction mid-loop if needed
    compact_threshold_ratio: float = 0.8  # Compact when at 80% of context limit

    # ReAct loop behavior
    max_consecutive_thoughts: int = 3  # Max thoughts without action before forcing action
    include_scratchpad: bool = True  # Include full reasoning history in each iteration
```

#### 3.1.2 ReActWorkflow Class

```python
class ReActWorkflow(Workflow[DepsT, str, ReActState]):
    """
    ReAct (Reasoning and Acting) workflow implementation.

    Implements the Thought → Action → Observation loop with configurable
    reasoning exposure and termination strategies.
    """

    def __init__(
        self,
        agent: Agent[DepsT, Any],
        config: ReActConfig | None = None,
        hooks: WorkflowHooks | None = None,
    ): ...

    @property
    def name(self) -> str:
        return "react"

    def _create_initial_state(self, prompt: str) -> WorkflowState[ReActState]: ...

    async def _execute(
        self,
        prompt: str,
        state: WorkflowState[ReActState],
        deps: DepsT | None = None,
    ) -> str: ...

    # Internal methods
    async def _run_iteration(self, state: ReActState, deps: DepsT | None) -> IterationResult: ...
    async def _generate_thought(self, state: ReActState, deps: DepsT | None) -> str: ...
    async def _execute_action(self, action: Action, deps: DepsT | None) -> Observation: ...
    def _check_termination(self, state: ReActState) -> tuple[bool, str | None]: ...
    async def _maybe_compact(self) -> CompactionResult | None: ...
```

#### 3.1.3 ReActState

Custom state context for the ReAct workflow:

```python
@dataclass
class ReActState:
    """Internal state for ReAct workflow execution."""

    # Original task
    task: str

    # Scratchpad - accumulates Thought/Action/Observation traces
    scratchpad: list[ScratchpadEntry]

    # Current iteration info
    current_thought: str | None = None
    current_action: Action | None = None
    current_observation: Observation | None = None

    # Termination tracking
    is_terminated: bool = False
    termination_reason: str | None = None
    final_answer: str | None = None
    confidence_score: float | None = None

    # Token tracking for this workflow
    iteration_token_counts: list[int] = field(default_factory=list)
    total_tokens_used: int = 0
    compaction_count: int = 0

@dataclass
class ScratchpadEntry:
    """Single entry in the ReAct scratchpad."""
    entry_type: Literal["thought", "action", "observation"]
    content: str
    timestamp: datetime
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### 3.1.4 Termination Strategies

**Tool-Based Termination:**
- Register a `final_answer` tool that the agent calls when ready to conclude
- Tool captures the final response and triggers workflow termination

```python
def create_final_answer_tool(state: ReActState) -> Callable:
    """Create the final_answer tool for termination."""
    def final_answer(answer: str) -> str:
        """Submit the final answer to complete the task.

        Args:
            answer: The final answer to the user's task.
        """
        state.final_answer = answer
        state.is_terminated = True
        state.termination_reason = "final_answer_tool"
        return f"Final answer submitted: {answer}"
    return final_answer
```

**Confidence-Based Termination:**
- Parse agent responses for confidence indicators
- Terminate when confidence exceeds threshold
- Fallback to max iterations if confidence never reached

**Hybrid Termination:**
- Support both strategies simultaneously
- Terminate on whichever condition is met first

### 3.2 Integration Requirements

#### 3.2.1 Context Compaction Integration

The ReAct workflow must integrate with the existing context management system:

```python
async def _maybe_compact(self) -> CompactionResult | None:
    """Check if compaction is needed and perform it."""
    if not self.config.auto_compact_in_workflow:
        return None

    context_state = self.agent.get_context_state()
    threshold = self.config.compact_threshold_ratio * self.agent.context_manager.config.trigger_threshold_tokens

    if context_state.token_count >= threshold:
        result = await self.agent.compact()
        self.state.context.compaction_count += 1
        await self._trigger_hook("on_compaction", result)
        return result
    return None
```

#### 3.2.2 Token Tracking Integration

- Track tokens per iteration in `ReActState.iteration_token_counts`
- Aggregate total across all iterations
- Expose via `workflow.get_token_usage()` method
- Include in `WorkflowResult.metadata`

#### 3.2.3 Hooks Integration

Extend `WorkflowHooks` with ReAct-specific callbacks:

```python
class ReActHooks(WorkflowHooks):
    """Extended hooks for ReAct workflow observability."""

    # Existing workflow hooks inherited...

    # ReAct-specific hooks
    on_thought: Callable[[ReActState, str], Awaitable[None] | None] | None = None
    on_action: Callable[[ReActState, Action], Awaitable[None] | None] | None = None
    on_observation: Callable[[ReActState, Observation], Awaitable[None] | None] | None = None
    on_compaction: Callable[[CompactionResult], Awaitable[None] | None] | None = None
```

### 3.3 System Prompt Engineering

The ReAct workflow constructs dynamic system prompts:

```python
REACT_SYSTEM_PROMPT_TEMPLATE = """
You are an AI assistant that solves tasks using the ReAct (Reasoning + Acting) approach.

For each step, you MUST follow this exact format:
{reasoning_prefix}<your reasoning about what to do next>
{action_prefix}<tool_name>(<arguments>)

After receiving an observation, reason about it and decide your next action.

When you have enough information to answer the task, use the {final_answer_tool} tool.

Available tools:
{tool_descriptions}

Remember:
- Think step by step
- Use tools to gather information
- Don't guess - verify with tools when possible
- Call {final_answer_tool} when you're confident in your answer
"""
```

---

## 4. API Design

### 4.1 Public API

```python
# Main exports from mamba_agents.workflows
from mamba_agents.workflows import (
    # Existing exports...
    Workflow, WorkflowConfig, WorkflowHooks, WorkflowResult, WorkflowState, WorkflowStep,

    # New ReAct exports
    ReActWorkflow,
    ReActConfig,
    ReActState,
    ReActHooks,
    ScratchpadEntry,
)
```

### 4.2 Workflow Methods

```python
class ReActWorkflow:
    # Core execution
    async def run(self, prompt: str, deps: DepsT | None = None) -> WorkflowResult[str, ReActState]
    def run_sync(self, prompt: str, deps: DepsT | None = None) -> WorkflowResult[str, ReActState]

    # State access
    def get_scratchpad(self) -> list[ScratchpadEntry]
    def get_reasoning_trace(self) -> str  # Formatted scratchpad as string
    def get_actions_taken(self) -> list[Action]

    # Token/cost access (delegates to agent)
    def get_token_usage(self) -> TokenUsage
    def get_cost(self) -> float

    # Properties
    @property
    def agent(self) -> Agent[DepsT, Any]
    @property
    def config(self) -> ReActConfig
    @property
    def hooks(self) -> ReActHooks | None
```

---

## 5. File Structure

```
src/mamba_agents/workflows/
├── __init__.py           # Add ReAct exports
├── base.py               # Existing Workflow ABC
├── config.py             # Add ReActConfig
├── hooks.py              # Add ReActHooks
├── errors.py             # Existing errors
└── react/                # New ReAct module
    ├── __init__.py       # ReAct exports
    ├── workflow.py       # ReActWorkflow implementation
    ├── state.py          # ReActState, ScratchpadEntry
    ├── prompts.py        # System prompt templates
    ├── termination.py    # Termination strategy implementations
    └── tools.py          # final_answer tool factory
```

---

## 6. Testing Requirements

### 6.1 Unit Tests

| Test File | Coverage |
|-----------|----------|
| `test_react_config.py` | ReActConfig validation, defaults, inheritance from WorkflowConfig |
| `test_react_state.py` | ReActState, ScratchpadEntry, state mutations |
| `test_react_workflow.py` | Core workflow execution, iteration logic |
| `test_react_termination.py` | Tool-based, confidence-based, hybrid termination |
| `test_react_integration.py` | Context compaction, token tracking integration |
| `test_react_hooks.py` | Hook triggering for thought/action/observation |

### 6.2 Test Patterns

```python
# Use TestModel for deterministic testing
from pydantic_ai.models.test import TestModel

def test_react_basic_flow():
    """Test basic Thought → Action → Observation → Final Answer flow."""
    model = TestModel()
    model.custom_result_text = "..."  # Control responses

    agent = Agent(model, tools=[...])
    workflow = ReActWorkflow(agent)
    result = workflow.run_sync("Test task")

    assert result.success
    assert len(result.state.context.scratchpad) >= 3  # At least T-A-O
```

### 6.3 Coverage Target

- Maintain 90% test coverage requirement
- All public API methods must have tests
- Edge cases: max iterations, context overflow, tool errors

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | ≥90% | pytest-cov |
| API Consistency | 100% | Matches existing Workflow patterns |
| Documentation | Complete | All public APIs documented |
| Type Safety | Full | ty/mypy passes with no errors |
| Example Notebook | 1+ | Jupyter notebook demonstrating usage |

---

## 8. Implementation Plan

### Phase 1: Core Structure
1. Create `src/mamba_agents/workflows/react/` directory structure
2. Implement `ReActConfig` extending `WorkflowConfig`
3. Implement `ReActState` and `ScratchpadEntry` dataclasses
4. Add module exports to `workflows/__init__.py`

### Phase 2: Workflow Implementation
1. Implement `ReActWorkflow` class skeleton
2. Implement `_create_initial_state()` method
3. Implement `_execute()` with basic Thought-Action-Observation loop
4. Add system prompt construction in `prompts.py`

### Phase 3: Termination Strategies
1. Implement `final_answer` tool factory
2. Implement tool-based termination detection
3. Implement confidence-based termination parsing
4. Implement hybrid termination strategy

### Phase 4: Integration
1. Add context compaction integration (`_maybe_compact()`)
2. Add token tracking across iterations
3. Implement `ReActHooks` with new callbacks
4. Wire up hook triggering in workflow

### Phase 5: Testing & Documentation
1. Write unit tests for all components
2. Write integration tests
3. Add docstrings to all public APIs
4. Create example notebook

---

## 9. Critical Files

| File | Purpose |
|------|---------|
| `src/mamba_agents/workflows/react/workflow.py` | Main ReActWorkflow implementation |
| `src/mamba_agents/workflows/react/config.py` | ReActConfig (or in `workflows/config.py`) |
| `src/mamba_agents/workflows/react/state.py` | ReActState, ScratchpadEntry |
| `src/mamba_agents/workflows/react/termination.py` | Termination strategy classes |
| `src/mamba_agents/workflows/base.py` | Reference for Workflow ABC |
| `src/mamba_agents/agent/core.py` | Reference for Agent integration |
| `tests/unit/test_workflows/test_react_workflow.py` | Main test file |

---

## 10. Verification Plan

### 10.1 Development Verification
```bash
# Run all tests
uv run pytest tests/unit/test_workflows/test_react*.py -v

# Check coverage
uv run pytest tests/unit/test_workflows/test_react*.py --cov=mamba_agents.workflows.react

# Type check
uv run ty check src/mamba_agents/workflows/react/

# Lint
uv run ruff check src/mamba_agents/workflows/react/
```

### 10.2 Integration Verification
```python
# Manual integration test script
from mamba_agents import Agent
from mamba_agents.workflows import ReActWorkflow, ReActConfig
from mamba_agents.tools import read_file

agent = Agent("gpt-4o", tools=[read_file])
workflow = ReActWorkflow(agent, config=ReActConfig(max_iterations=5))

result = workflow.run_sync("What is in the README.md file?")
print(f"Success: {result.success}")
print(f"Steps: {len(result.state.steps)}")
print(f"Answer: {result.output}")
```

---

## 11. Dependencies

- **No new external dependencies required**
- Uses existing pydantic-ai Agent for LLM execution
- Uses existing workflow infrastructure
- Uses existing context/token tracking components

---

## 12. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Prompt engineering complexity | Medium | Provide sensible defaults, allow full customization |
| Token consumption in long loops | High | Integrate with context compaction, set conservative defaults |
| Termination detection failures | Medium | Support multiple strategies, hybrid as fallback |
| Testing with real models | Low | Use TestModel for unit tests, optional integration tests |

---

## 13. Future Work

The following features are planned for future implementation:

### 13.1 Confidence-Based Termination

The MVP implements only tool-based termination (via `final_answer` tool). Future work includes:

- **Confidence parsing**: Parse agent responses for confidence indicators (e.g., structured output with confidence field)
- **Confidence threshold**: Terminate when confidence exceeds `confidence_threshold` (default 0.9)
- **Hybrid termination**: Support both tool-based and confidence-based strategies simultaneously

### 13.2 Additional Enhancements

- **Structured output for thoughts/actions**: Use pydantic models for more reliable parsing
- **Multi-agent ReAct**: Separate reasoning vs execution agents
- **ReAct variants**: Reflexion, Tree of Thoughts integration

---

## References

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) (Yao et al., 2023)
- [IBM: What is a ReAct Agent?](https://www.ibm.com/think/topics/react-agent)
- [Prompt Engineering Guide: ReAct](https://www.promptingguide.ai/techniques/react)
- Existing workflow implementation: `src/mamba_agents/workflows/`
