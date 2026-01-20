"""Importance scoring compaction strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mamba_agents.context.compaction.base import CompactionResult, CompactionStrategy

if TYPE_CHECKING:
    from pydantic_ai import Agent


class ImportanceScoringStrategy(CompactionStrategy):
    """Score messages by importance and prune lowest scored.

    Uses an LLM to score messages by their importance to the
    conversation, then removes the lowest-scored messages.
    """

    def __init__(
        self,
        scoring_agent: Agent[Any, str] | None = None,
    ) -> None:
        """Initialize the importance scoring strategy.

        Args:
            scoring_agent: Agent to use for scoring.
                          If None, uses heuristic scoring.
        """
        self._agent = scoring_agent

    @property
    def name(self) -> str:
        return "importance_scoring"

    async def compact(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        preserve_recent: int = 0,
    ) -> CompactionResult:
        """Compact by removing low-importance messages.

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

        # Score messages
        scores = await self._score_messages(messages)

        # Create list of (index, message, score) for sorting
        indexed = [(i, m, s) for i, (m, s) in enumerate(zip(messages, scores, strict=False))]

        # Separate preserved messages
        if preserve_recent > 0:
            preserve_start = len(messages) - preserve_recent
            preserved = [x for x in indexed if x[0] >= preserve_start]
            removable = [x for x in indexed if x[0] < preserve_start]
        else:
            preserved = []
            removable = indexed.copy()

        # Sort removable by score (lowest first)
        removable.sort(key=lambda x: x[2])

        # Remove lowest scored until under target
        removed_count = 0
        while removable:
            current = [x[1] for x in removable] + [x[1] for x in preserved]
            if self._count_tokens(current) <= target_tokens:
                break

            removable.pop(0)  # Remove lowest scored
            removed_count += 1

        # Reconstruct messages in original order
        remaining = sorted(removable + preserved, key=lambda x: x[0])
        result_messages = [x[1] for x in remaining]
        tokens_after = self._count_tokens(result_messages)

        return CompactionResult(
            messages=result_messages,
            removed_count=removed_count,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
            strategy=self.name,
        )

    async def _score_messages(self, messages: list[dict[str, Any]]) -> list[float]:
        """Score messages by importance.

        Args:
            messages: Messages to score.

        Returns:
            List of scores (0-1, higher = more important).
        """
        if self._agent is None:
            return self._heuristic_scores(messages)

        # Use LLM for scoring (simplified - would need more sophisticated prompt)
        scores = []
        for msg in messages:
            score = await self._llm_score_message(msg)
            scores.append(score)

        return scores

    def _heuristic_scores(self, messages: list[dict[str, Any]]) -> list[float]:
        """Calculate heuristic importance scores.

        Args:
            messages: Messages to score.

        Returns:
            List of scores.
        """
        scores = []
        total = len(messages)

        for i, msg in enumerate(messages):
            # Base score increases with recency
            recency_score = i / total

            # Role-based scoring
            role = msg.get("role", "")
            if role == "system":
                role_score = 1.0  # System messages are important
            elif role == "user":
                role_score = 0.7  # User messages are fairly important
            elif role == "assistant":
                # Tool calls less important once done, otherwise moderate importance
                role_score = 0.5 if msg.get("tool_calls") else 0.6
            elif role == "tool":
                role_score = 0.3  # Tool results least important once processed
            else:
                role_score = 0.5

            # Content length bonus (longer = potentially more important)
            content = msg.get("content", "")
            length_score = min(len(content) / 500, 0.2)  # Cap at 0.2

            # Combine scores
            final_score = (recency_score * 0.5) + (role_score * 0.4) + length_score
            scores.append(final_score)

        return scores

    async def _llm_score_message(self, msg: dict[str, Any]) -> float:
        """Score a single message using LLM.

        Args:
            msg: Message to score.

        Returns:
            Score between 0 and 1.
        """
        if self._agent is None:
            return 0.5

        content = msg.get("content", "")[:200]  # Truncate for scoring
        role = msg.get("role", "unknown")

        prompt = f"""Rate the importance of this {role} message on a scale of 0-10:
"{content}"
Reply with just the number."""

        try:
            result = await self._agent.run(prompt)
            score = float(result.output.strip()) / 10
            return max(0, min(1, score))  # Clamp to 0-1
        except (ValueError, AttributeError):
            return 0.5  # Default on error
