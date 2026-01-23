#!/usr/bin/env python3
"""Graceful tool error handling example (v0.1.2+).

This example demonstrates:
- Default graceful error handling (exceptions become LLM-visible errors)
- Disabling graceful errors per-tool
- Disabling graceful errors globally via AgentConfig

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import os
from pathlib import Path

from mamba_agents import Agent, AgentConfig


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Example 1: Default graceful errors (enabled)
    # Tool exceptions are converted to error messages for the LLM
    print("--- Example 1: Default Graceful Errors ---\n")

    agent = Agent("gpt-4o-mini")

    @agent.tool_plain
    def read_config(path: str) -> str:
        """Read a configuration file."""
        return Path(path).read_text()

    # When called with a non-existent file, the LLM receives:
    # "FileNotFoundError: [Errno 2] No such file or directory: 'missing.txt'"
    # and can try a different approach instead of crashing
    result = agent.run_sync(
        "Try to read 'nonexistent_config.json'. If it doesn't exist, "
        "tell me that the file was not found."
    )
    print(f"Response: {result.output}\n")

    # Example 2: Per-tool opt-out
    print("--- Example 2: Per-Tool Opt-Out ---\n")

    agent2 = Agent("gpt-4o-mini")

    @agent2.tool_plain(graceful_errors=False)
    def critical_operation(data: str) -> str:
        """Critical tool where exceptions should propagate immediately."""
        if not data:
            raise ValueError("Data required")
        return f"Processed: {data}"

    print("Tool with graceful_errors=False will raise exceptions immediately.")
    print("Use this for tools where failure should stop the agent.\n")

    # Example 3: Global disable via AgentConfig
    print("--- Example 3: Global Disable ---\n")

    config = AgentConfig(graceful_tool_errors=False)
    strict_agent = Agent("gpt-4o-mini", config=config)

    @strict_agent.tool_plain
    def any_tool(x: str) -> str:
        """All tools on this agent propagate exceptions."""
        return x.upper()

    print("Agent with graceful_tool_errors=False in config:")
    print("All tools will propagate exceptions instead of converting to errors.\n")


if __name__ == "__main__":
    main()
