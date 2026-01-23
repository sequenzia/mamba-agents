#!/usr/bin/env python3
"""Workflow hooks example.

This example demonstrates:
- Using hooks to observe workflow execution
- ReAct-specific hooks for thoughts, actions, observations
- Logging and debugging workflow progress

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import asyncio
import os

from mamba_agents import Agent
from mamba_agents.tools import read_file
from mamba_agents.workflows import ReActConfig, ReActHooks, ReActWorkflow


async def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Define hook callbacks
    def on_workflow_start(state):
        print("[WORKFLOW] Started")

    def on_workflow_complete(result):
        print(f"[WORKFLOW] Completed - Success: {result.success}")

    def on_iteration_start(state, iteration):
        print(f"\n[ITERATION {iteration}] Starting...")

    def on_thought(state, thought):
        # Truncate long thoughts for display
        display = thought[:80] + "..." if len(thought) > 80 else thought
        print(f"  [THOUGHT] {display}")

    def on_action(state, tool_name, tool_args):
        args_str = ", ".join(f"{k}={v!r}" for k, v in (tool_args or {}).items())
        print(f"  [ACTION] {tool_name}({args_str})")

    def on_observation(state, observation, error):
        if error:
            print(f"  [OBSERVATION] Error: {error}")
        else:
            display = str(observation)[:80] + "..." if len(str(observation)) > 80 else observation
            print(f"  [OBSERVATION] {display}")

    # Create hooks with callbacks
    hooks = ReActHooks(
        on_workflow_start=on_workflow_start,
        on_workflow_complete=on_workflow_complete,
        on_iteration_start=on_iteration_start,
        on_thought=on_thought,
        on_action=on_action,
        on_observation=on_observation,
    )

    # Create agent and workflow
    agent = Agent("gpt-4o-mini", tools=[read_file])

    workflow = ReActWorkflow(
        agent=agent,
        config=ReActConfig(max_iterations=5),
        hooks=hooks,
    )

    print("Running workflow with hooks...\n")

    result = await workflow.run("Read the README.md file and summarize it briefly.")

    print(f"\n--- Final Result ---")
    print(f"\n{result.output}")


if __name__ == "__main__":
    asyncio.run(main())
