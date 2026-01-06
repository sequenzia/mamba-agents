"""Streaming configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StreamingConfig(BaseModel):
    """Configuration for streaming behavior.

    Controls whether to stream model responses and tool results,
    and the chunk size for streaming.

    Attributes:
        stream_model_responses: Stream LLM token output.
        stream_tool_results: Stream tool execution output.
        chunk_size: Bytes per chunk for tool streaming.
    """

    stream_model_responses: bool = Field(
        default=True,
        description="Stream LLM token output",
    )
    stream_tool_results: bool = Field(
        default=True,
        description="Stream tool execution output",
    )
    chunk_size: int = Field(
        default=1024,
        gt=0,
        description="Bytes per chunk for tool streaming",
    )
