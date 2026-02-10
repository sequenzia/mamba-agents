# Agent

The main agent class that wraps pydantic-ai with additional features.

## Quick Example

```python
from mamba_agents import Agent, AgentSettings

settings = AgentSettings()
agent = Agent("gpt-4o", settings=settings)

# Run agent
result = await agent.run("Hello!")
print(result.output)

# Check usage
print(agent.get_usage())
print(agent.get_cost())
```

## API Reference

::: mamba_agents.agent.core.Agent
    options:
      show_root_heading: true
      show_source: true
      members:
        - __init__
        - run
        - run_sync
        - run_stream
        - tool
        - tool_plain
        - messages
        - get_token_count
        - get_usage
        - get_usage_history
        - get_cost
        - get_cost_breakdown
        - get_messages
        - should_compact
        - compact
        - get_context_state
        - clear_context
        - reset_tracking
        - reset_all
        - get_system_prompt
        - set_system_prompt
        - skill_manager
        - register_skill
        - get_skill
        - list_skills
        - invoke_skill
        - subagent_manager
        - delegate
        - delegate_sync
        - delegate_async
        - register_subagent
        - list_subagents
        - override
        - from_settings
