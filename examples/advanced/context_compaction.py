#!/usr/bin/env python3
"""Context compaction example.

This example demonstrates:
- Configuring context compaction strategies
- Manual compaction
- Checking context state

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import os

from mamba_agents import Agent, AgentConfig, CompactionConfig


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        print("Please set OPENAI_API_KEY environment variable")
        return

    print("Available compaction strategies:")
    print("  - sliding_window: Remove oldest messages beyond threshold")
    print("  - summarize_older: LLM-based summarization of older messages")
    print("  - selective_pruning: Remove completed tool call/result pairs")
    print("  - importance_scoring: LLM-based scoring, prune lowest importance")
    print("  - hybrid: Combine multiple strategies in sequence")
    print()

    # Configure compaction
    config = AgentConfig(
        context=CompactionConfig(
            strategy="sliding_window",
            trigger_threshold_tokens=1000,  # Low threshold for demo
            target_tokens=500,
            preserve_recent_turns=2,
            preserve_system_prompt=True,
        ),
        auto_compact=True,  # Automatically compact when threshold reached
    )

    agent = Agent("gpt-4o-mini", config=config)

    # Run several turns to build up context
    print("Building up conversation context...")
    agent.run_sync("Tell me about Python.")
    agent.run_sync("What are its main features?")
    agent.run_sync("How is it different from Java?")

    # Check context state
    state = agent.get_context_state()
    print(f"\nContext state:")
    print(f"  Messages: {state.message_count}")
    print(f"  Tokens: {state.token_count}")

    # Check if compaction needed
    if agent.should_compact():
        print("\nCompaction threshold reached!")
    else:
        print("\nContext within threshold.")

    # Disable auto-compact and manage manually
    print("\n--- Manual Compaction Example ---\n")

    config2 = AgentConfig(
        context=CompactionConfig(
            strategy="sliding_window",
            trigger_threshold_tokens=1000,
            target_tokens=500,
        ),
        auto_compact=False,  # Disable auto-compaction
    )

    agent2 = Agent("gpt-4o-mini", config=config2)

    # Build context
    for i in range(5):
        agent2.run_sync(f"Message {i}: Tell me something interesting.")

    state = agent2.get_context_state()
    print(f"Before compaction: {state.message_count} messages, {state.token_count} tokens")

    # Manual compaction (if needed)
    if agent2.should_compact():
        import asyncio

        result = asyncio.run(agent2.compact())
        print(f"Compacted: removed {result.removed_count} messages")

        state = agent2.get_context_state()
        print(f"After compaction: {state.message_count} messages, {state.token_count} tokens")


if __name__ == "__main__":
    main()
