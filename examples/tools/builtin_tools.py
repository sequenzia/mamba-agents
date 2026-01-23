#!/usr/bin/env python3
"""Built-in tools example.

This example demonstrates:
- Using built-in filesystem, glob, and grep tools
- Registering tools with an agent
- Agent using tools to answer questions

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import os
import tempfile
from pathlib import Path

from mamba_agents import Agent
from mamba_agents.tools import glob_search, grep_search, list_directory, read_file


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Create agent with built-in tools
    agent = Agent(
        "gpt-4o-mini",
        tools=[read_file, list_directory, glob_search, grep_search],
    )

    # Create some test files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files
        (Path(tmpdir) / "hello.py").write_text("print('Hello, World!')\n")
        (Path(tmpdir) / "utils.py").write_text("def greet(name):\n    return f'Hello, {name}!'\n")
        (Path(tmpdir) / "README.md").write_text("# My Project\n\nA sample project.\n")

        # Let the agent explore the directory
        print(f"Agent exploring: {tmpdir}\n")

        result = agent.run_sync(f"List all files in {tmpdir} and tell me what each file contains.")
        print(f"Agent response:\n{result.output}")

        # Check usage
        print(f"\nTokens used: {agent.get_usage().total_tokens}")


if __name__ == "__main__":
    main()
