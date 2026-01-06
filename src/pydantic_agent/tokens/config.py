"""Token management configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenizerConfig(BaseModel):
    """Configuration for token counting.

    Attributes:
        encoding: Tiktoken encoding to use.
        model_mapping: Optional model-specific encoding overrides.
        cache_tokenizer: Cache tokenizer instance for performance.
        safety_margin: Safety margin for context window calculations.
    """

    encoding: str = Field(
        default="cl100k_base",
        description="Default tiktoken encoding",
    )
    model_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "llama": "cl100k_base",
            "mistral": "cl100k_base",
            "gpt-4": "cl100k_base",
            "gpt-3.5": "cl100k_base",
        },
        description="Model-specific encoding mappings",
    )
    cache_tokenizer: bool = Field(
        default=True,
        description="Cache tokenizer instance",
    )
    safety_margin: float = Field(
        default=0.05,
        ge=0,
        le=0.5,
        description="Safety margin for context window (0.05 = 5%)",
    )
