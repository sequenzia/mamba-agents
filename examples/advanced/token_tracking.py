#!/usr/bin/env python3
"""Token tracking and cost estimation example.

This example demonstrates:
- Tracking token usage across requests
- Estimating costs
- Getting usage history
- Resetting tracking

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

    # Run several queries
    print("Running queries...\n")
    agent.run_sync("What is 2 + 2?")
    agent.run_sync("Explain Python in one sentence.")
    agent.run_sync("What's the capital of France?")

    # Get aggregate usage
    usage = agent.get_usage()
    print("Aggregate Usage:")
    print(f"  Total tokens: {usage.total_tokens}")
    print(f"  Prompt tokens: {usage.prompt_tokens}")
    print(f"  Completion tokens: {usage.completion_tokens}")
    print(f"  Request count: {usage.request_count}")

    # Get cost estimate
    cost = agent.get_cost()
    print(f"\nEstimated cost: ${cost:.6f}")

    # Get detailed breakdown
    breakdown = agent.get_cost_breakdown()
    print("\nCost Breakdown:")
    print(f"  Prompt cost: ${breakdown.prompt_cost:.6f}")
    print(f"  Completion cost: ${breakdown.completion_cost:.6f}")
    print(f"  Total cost: ${breakdown.total_cost:.6f}")

    # Get per-request history
    history = agent.get_usage_history()
    print("\nPer-Request History:")
    for i, record in enumerate(history, 1):
        print(f"  Request {i}: {record.total_tokens} tokens")

    # Count tokens for arbitrary text
    text = "Hello, world! This is a test message."
    count = agent.get_token_count(text)
    print(f"\nToken count for '{text}': {count}")

    # Reset tracking for new session
    print("\nResetting tracking...")
    agent.reset_tracking()

    usage = agent.get_usage()
    print(f"After reset: {usage.total_tokens} tokens, {usage.request_count} requests")


if __name__ == "__main__":
    main()
