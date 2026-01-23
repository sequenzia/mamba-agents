#!/usr/bin/env python3
"""Multi-turn conversation example.

This example demonstrates:
- Context is maintained automatically across runs
- Accessing conversation state
- Clearing context for new conversations

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import os

from mamba_agents import Agent


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    agent = Agent("gpt-4o-mini")

    # First turn - introduce information
    print("Turn 1: Introducing information...")
    agent.run_sync("My name is Alice and I'm working on a Python project.")

    # Second turn - agent remembers context
    print("Turn 2: Testing memory...")
    result = agent.run_sync("What's my name and what am I working on?")
    print(f"Response: {result.output}")

    # Check context state
    state = agent.get_context_state()
    print(f"\nContext: {state.message_count} messages, {state.token_count} tokens")

    # Get all messages in the conversation
    messages = agent.get_messages()
    print(f"Messages tracked: {len(messages)}")

    # Clear context for fresh conversation
    agent.clear_context()
    print("\nContext cleared. Starting fresh conversation...")

    result = agent.run_sync("What's my name?")
    print(f"Response after clear: {result.output}")


if __name__ == "__main__":
    main()
