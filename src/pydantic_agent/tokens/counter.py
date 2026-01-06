"""Token counting using tiktoken."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Any

import tiktoken

if TYPE_CHECKING:
    from pydantic_agent.tokens.config import TokenizerConfig


@lru_cache(maxsize=10)
def _get_encoding(encoding_name: str) -> tiktoken.Encoding:
    """Get a cached tiktoken encoding.

    Args:
        encoding_name: Name of the encoding.

    Returns:
        The tiktoken Encoding instance.
    """
    return tiktoken.get_encoding(encoding_name)


class TokenCounter:
    """Token counting using tiktoken.

    Provides methods for counting tokens in text and message lists.
    Token counts are approximate and may vary from actual model tokenization.
    """

    def __init__(self, config: "TokenizerConfig | None" = None) -> None:
        """Initialize the token counter.

        Args:
            config: Optional tokenizer configuration.
        """
        from pydantic_agent.tokens.config import TokenizerConfig

        self._config = config or TokenizerConfig()
        self._encoding_name = self._config.encoding

        if self._config.cache_tokenizer:
            self._encoding = _get_encoding(self._encoding_name)
        else:
            self._encoding = tiktoken.get_encoding(self._encoding_name)

    def count(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: The text to count tokens in.

        Returns:
            Approximate token count.
        """
        return len(self._encoding.encode(text))

    def count_messages(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in a message list.

        Estimates tokens for a list of chat messages, accounting for
        message structure overhead.

        Args:
            messages: List of message dictionaries with 'role' and 'content'.

        Returns:
            Approximate total token count.
        """
        total = 0

        for message in messages:
            # Add overhead per message (role, separators)
            total += 4  # Approximate overhead per message

            # Count content tokens
            content = message.get("content", "")
            if content:
                total += self.count(content)

            # Count role tokens
            role = message.get("role", "")
            if role:
                total += self.count(role)

            # Count tool call tokens if present
            tool_calls = message.get("tool_calls", [])
            for tool_call in tool_calls:
                if isinstance(tool_call, dict):
                    func = tool_call.get("function", {})
                    name = func.get("name", "")
                    args = func.get("arguments", "")
                    total += self.count(name) + self.count(args) + 10  # Overhead

        # Add final overhead
        total += 3

        return total

    def count_with_margin(self, text: str) -> int:
        """Count tokens with safety margin.

        Args:
            text: The text to count.

        Returns:
            Token count plus safety margin.
        """
        base_count = self.count(text)
        margin = int(base_count * self._config.safety_margin)
        return base_count + margin

    def fits_context(self, text: str, max_tokens: int) -> bool:
        """Check if text fits within a context window.

        Args:
            text: The text to check.
            max_tokens: Maximum token count.

        Returns:
            True if text fits (with safety margin).
        """
        return self.count_with_margin(text) <= max_tokens

    def get_encoding_for_model(self, model: str) -> str:
        """Get the appropriate encoding for a model.

        Args:
            model: Model name or identifier.

        Returns:
            Encoding name to use.
        """
        # Check model mapping
        for prefix, encoding in self._config.model_mapping.items():
            if prefix.lower() in model.lower():
                return encoding

        # Default encoding
        return self._config.encoding
