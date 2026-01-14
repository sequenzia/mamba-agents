# Building a Code Assistant

In this tutorial, you'll build a coding assistant that can read files, search code, run commands, and help with development tasks.

## What You'll Build

A code assistant that can:

- Read and analyze source code files
- Search for patterns across the codebase
- Run shell commands
- Maintain context across conversations

## Prerequisites

- Python 3.12+
- Pydantic Agent installed
- OpenAI API key (or local model)

## Step 1: Project Setup

Create a new file `code_assistant.py`:

```python
import asyncio
from pydantic_agent import Agent, AgentConfig, AgentSettings
from pydantic_agent.tools import (
    read_file,
    write_file,
    list_directory,
    glob_search,
    grep_search,
    run_bash,
)
```

## Step 2: Configure the Agent

```python
# Load settings (uses env vars, .env, config files)
settings = AgentSettings()

# Create agent with coding tools
agent = Agent(
    "gpt-4o",
    settings=settings,
    tools=[
        read_file,
        write_file,
        list_directory,
        glob_search,
        grep_search,
        run_bash,
    ],
    config=AgentConfig(
        system_prompt="""You are a helpful coding assistant. You can:
- Read and analyze code files
- Search for patterns in the codebase
- Run shell commands
- Help with debugging and code review

When analyzing code:
1. First understand the file structure
2. Read relevant files
3. Provide clear explanations

Be concise but thorough. Use code blocks for code snippets.""",
    ),
)
```

## Step 3: Create the Chat Loop

```python
async def chat():
    """Interactive chat loop."""
    print("Code Assistant ready! Type 'quit' to exit.\n")

    while True:
        # Get user input
        user_input = input("You: ").strip()

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        # Run the agent
        try:
            result = await agent.run(user_input)
            print(f"\nAssistant: {result.output}\n")

            # Show usage stats
            usage = agent.get_usage()
            print(f"[Tokens: {usage.total_tokens}, Cost: ${agent.get_cost():.4f}]\n")

        except Exception as e:
            print(f"\nError: {e}\n")
```

## Step 4: Add the Main Entry Point

```python
async def main():
    """Main entry point."""
    print("=" * 50)
    print("Code Assistant")
    print("=" * 50)
    print()

    await chat()

    # Print final usage summary
    print("\nSession Summary:")
    usage = agent.get_usage()
    print(f"  Total tokens: {usage.total_tokens}")
    print(f"  Total requests: {usage.request_count}")
    print(f"  Total cost: ${agent.get_cost():.4f}")


if __name__ == "__main__":
    asyncio.run(main())
```

## Step 5: Run the Assistant

```bash
python code_assistant.py
```

## Example Conversation

```
Code Assistant ready! Type 'quit' to exit.

You: What Python files are in this directory?