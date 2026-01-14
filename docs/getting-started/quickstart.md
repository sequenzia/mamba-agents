# Quick Start

This guide will get you running your first agent in under 5 minutes.

## Prerequisites

Before you begin, make sure you have:

1. Python 3.12+ installed
2. Pydantic Agent installed (`uv add pydantic-agent`)
3. An API key for your model provider

## Step 1: Set Up Your API Key

The simplest way to provide your API key is through an environment variable:

=== "OpenAI"

    ```bash
    export OPENAI_API_KEY="sk-..."
    ```

=== "Anthropic"

    ```bash
    export ANTHROPIC_API_KEY="sk-ant-..."
    ```

=== ".env file"

    Create a `.env` file in your project:
    ```
    AGENTS_MODEL_BACKEND__API_KEY=sk-...
    AGENTS_MODEL_BACKEND__MODEL=gpt-4o
    ```

## Step 2: Create Your First Agent

```python
from pydantic_agent import Agent

# Create an agent with a model
agent = Agent("gpt-4o")

# Run the agent synchronously
result = agent.run_sync("What is 2 + 2?")
print(result.output)
```

## Step 3: Add a System Prompt

```python
from pydantic_agent import Agent, AgentConfig

agent = Agent(
    "gpt-4o",
    config=AgentConfig(
        system_prompt="You are a helpful coding assistant. Be concise."
    ),
)

result = agent.run_sync("How do I read a file in Python?")
print(result.output)
```

## Step 4: Use Built-in Tools

Give your agent the ability to interact with the filesystem:

```python
from pydantic_agent import Agent
from pydantic_agent.tools import read_file, list_directory, glob_search

agent = Agent(
    "gpt-4o",
    tools=[read_file, list_directory, glob_search],
)

result = agent.run_sync("What Python files are in the current directory?")
print(result.output)
```

## Step 5: Track Usage and Cost

```python
from pydantic_agent import Agent

agent = Agent("gpt-4o")

# Run a few queries
agent.run_sync("Hello!")
agent.run_sync("Tell me about Python")
agent.run_sync("What are decorators?")

# Check aggregate usage
usage = agent.get_usage()
print(f"Total tokens: {usage.total_tokens}")
print(f"Requests: {usage.request_count}")

# Check estimated cost
cost = agent.get_cost()
print(f"Estimated cost: ${cost:.4f}")
```

## Step 6: Multi-turn Conversations

Context is maintained automatically across runs:

```python
from pydantic_agent import Agent

agent = Agent("gpt-4o")

# First turn
agent.run_sync("My name is Alice")

# Second turn - agent remembers the context
result = agent.run_sync("What's my name?")
print(result.output)  # "Your name is Alice"

# Check context state
state = agent.get_context_state()
print(f"Messages in context: {state.message_count}")
print(f"Tokens used: {state.token_count}")
```

## Step 7: Using Settings

For more control, use the settings system:

```python
from pydantic_agent import Agent, AgentSettings

# Load settings from env vars, .env files, and config.toml
settings = AgentSettings()

# Create agent with settings
agent = Agent(settings=settings)

# Or override the model while using other settings
agent = Agent("gpt-4o-mini", settings=settings)
```

## Complete Example

Here's a complete example bringing it all together:

```python
import asyncio
from pydantic_agent import Agent, AgentConfig, AgentSettings
from pydantic_agent.tools import read_file, run_bash

async def main():
    # Load settings
    settings = AgentSettings()

    # Create agent with tools and custom system prompt
    agent = Agent(
        "gpt-4o",
        settings=settings,
        tools=[read_file, run_bash],
        config=AgentConfig(
            system_prompt="You are a helpful DevOps assistant.",
        ),
    )

    # Run queries
    result = await agent.run("What's the current directory listing?")
    print(result.output)

    # Print usage summary
    usage = agent.get_usage()
    print(f"\nUsage Summary:")
    print(f"  Tokens: {usage.total_tokens}")
    print(f"  Cost: ${agent.get_cost():.4f}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

- [Configuration](configuration.md) - Learn about all configuration options
- [Agent Basics](../user-guide/agent-basics.md) - Deep dive into the Agent API
- [Working with Tools](../user-guide/tools.md) - Learn about built-in tools
- [Workflows](../user-guide/workflows.md) - Multi-step orchestration with ReAct
