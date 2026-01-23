#!/usr/bin/env python3
"""Basic agent usage example.

This example demonstrates:
- Creating an agent with a model string
- Running synchronous and async queries
- Accessing results and usage information

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import asyncio
import os

from mamba_agents import Agent, AgentSettings


def main():
    """Synchronous agent example."""
    # Ensure API key is set
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Method 1: Simple model string (uses OPENAI_API_KEY from env)
    agent = Agent("gpt-4o-mini")

    # Synchronous execution
    result = agent.run_sync("What is 2 + 2?")
    print(f"Answer: {result.output}")

    # Check token usage
    usage = agent.get_usage()
    print(f"Tokens used: {usage.total_tokens}")
    print(f"Estimated cost: ${agent.get_cost():.6f}")


async def async_main():
    """Async agent example."""
    # Method 2: Using AgentSettings (loads from env, .env, config files)
    settings = AgentSettings()
    agent = Agent("gpt-4o-mini", settings=settings)

    # Async execution
    result = await agent.run("Explain Python in one sentence.")
    print(f"Answer: {result.output}")


if __name__ == "__main__":
    print("--- Synchronous Example ---\n")
    main()
    print("\n--- Async Example ---\n")
    asyncio.run(async_main())
