#!/usr/bin/env python3
"""ReAct workflow example.

This example demonstrates:
- Creating a ReAct (Reasoning and Acting) workflow
- Running multi-step reasoning tasks
- Accessing the reasoning trace (scratchpad)

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import asyncio
import os

from mamba_agents import Agent
from mamba_agents.tools import glob_search, grep_search, read_file
from mamba_agents.workflows import ReActConfig, ReActWorkflow


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Create agent with tools
    agent = Agent(
        "gpt-4o-mini",
        tools=[read_file, glob_search, grep_search],
    )

    # Create ReAct workflow
    workflow = ReActWorkflow(
        agent=agent,
        config=ReActConfig(
            max_iterations=10,
            expose_reasoning=True,  # Include thoughts in output
        ),
    )

    print("Running ReAct workflow...\n")
    print("The agent will reason step by step:\n")
    print("  Thought -> Action -> Observation -> ... -> Final Answer\n")

    # Run the workflow
    result = await workflow.run(
        "What Python version is required by this project? "
        "Look for pyproject.toml or setup.py files."
    )

    print(f"Success: {result.success}")
    print(f"Iterations: {result.state.iteration_count}")
    print(f"\nFinal Answer:\n{result.output}")

    # Access the reasoning trace
    print("\n--- Reasoning Trace ---\n")
    for entry in result.state.context.scratchpad:
        print(f"[{entry.entry_type.upper()}] {entry.content[:100]}...")
        print()

    # Check costs
    print(f"Total cost: ${workflow.get_cost():.4f}")


if __name__ == "__main__":
    asyncio.run(main())
