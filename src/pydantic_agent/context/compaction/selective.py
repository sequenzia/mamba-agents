"""Selective pruning compaction strategy."""

from __future__ import annotations

from typing import Any

from pydantic_agent.context.compaction.base import CompactionResult, CompactionStrategy


class SelectivePruningStrategy(CompactionStrategy):
    """Remove completed tool call/result pairs.

    This strategy identifies tool calls that have been completed
    (have corresponding results) and removes both the call and
    result, keeping only a summary of what was done.
    """

    @property
    def name(self) -> str:
        return "selective_pruning"

    async def compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int = 0,
    ) -> CompactionResult:
        """Compact by removing completed tool call pairs.

        Args:
            messages: Messages to compact.
            target_tokens: Target token count.
            preserve_recent: Number of recent messages to preserve.

        Returns:
            CompactionResult with compacted messages.
        """
        tokens_before = self._count_tokens(messages)

        if tokens_before <= target_tokens:
            return CompactionResult(
                messages=messages,
                removed_count=0,
                tokens_before=tokens_before,
                tokens_after=tokens_before,
                strategy=self.name,
            )

        # Identify tool call/result pairs
        tool_call_pairs = self._find_tool_call_pairs(messages)

        # Separate messages to preserve
        if preserve_recent > 0:
            preserved_indices = set(range(len(messages) - preserve_recent, len(messages)))
        else:
            preserved_indices = set()

        # Remove oldest pairs first until under target
        result_messages = messages.copy()
        removed_count = 0

        for call_idx, result_idx in tool_call_pairs:
            if self._count_tokens(result_messages) <= target_tokens:
                break

            # Don't remove preserved messages
            if call_idx in preserved_indices or result_idx in preserved_indices:
                continue

            # Create summary of what was done
            call_msg = messages[call_idx]
            tool_calls = call_msg.get("tool_calls", [])

            if tool_calls:
                tool_names = [
                    tc.get("function", {}).get("name", "unknown")
                    for tc in tool_calls
                    if isinstance(tc, dict)
                ]
                summary = f"[Tool calls executed: {', '.join(tool_names)}]"

                # Replace with summary
                for tc_idx, msg in enumerate(result_messages):
                    if msg.get("role") == "assistant" and msg.get("tool_calls") == tool_calls:
                        result_messages[tc_idx] = {
                            "role": "system",
                            "content": summary,
                        }
                        removed_count += 1
                        break

                # Remove corresponding tool results
                result_messages = [
                    m
                    for m in result_messages
                    if not (
                        m.get("role") == "tool"
                        and m.get("tool_call_id")
                        in [tc.get("id") for tc in tool_calls if isinstance(tc, dict)]
                    )
                ]

        tokens_after = self._count_tokens(result_messages)

        return CompactionResult(
            messages=result_messages,
            removed_count=removed_count,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            strategy=self.name,
        )

    def _find_tool_call_pairs(
        self, messages: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        """Find indices of tool call and result pairs.

        Args:
            messages: Messages to search.

        Returns:
            List of (call_index, result_index) tuples.
        """
        pairs: list[tuple[int, int]] = []
        tool_call_indices: dict[str, int] = {}

        for i, msg in enumerate(messages):
            # Track tool calls
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg.get("tool_calls", []):
                    if isinstance(tc, dict) and tc.get("id"):
                        tool_call_indices[tc["id"]] = i

            # Match with results
            if msg.get("role") == "tool" and msg.get("tool_call_id"):
                call_id = msg["tool_call_id"]
                if call_id in tool_call_indices:
                    pairs.append((tool_call_indices[call_id], i))

        return pairs
