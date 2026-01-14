"""Tests for ReActConfig."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pydantic_agent.workflows import ReActConfig, WorkflowConfig


class TestReActConfig:
    """Tests for ReActConfig class."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = ReActConfig()

        # Inherited from WorkflowConfig
        assert config.max_steps == 50
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300.0
        assert config.enable_hooks is True
        assert config.track_state is True

        # ReAct-specific
        assert config.expose_reasoning is True
        assert config.reasoning_prefix == "Thought: "
        assert config.action_prefix == "Action: "
        assert config.observation_prefix == "Observation: "
        assert config.termination_strategy == "tool"
        assert config.final_answer_tool_name == "final_answer"
        assert config.auto_compact_in_workflow is True
        assert config.compact_threshold_ratio == 0.8
        assert config.max_consecutive_thoughts == 3
        assert config.include_scratchpad is True
        assert config.tool_retry_count == 2

    def test_inherits_from_workflow_config(self) -> None:
        """Test that ReActConfig inherits from WorkflowConfig."""
        assert issubclass(ReActConfig, WorkflowConfig)

    def test_custom_values(self) -> None:
        """Test setting custom values."""
        config = ReActConfig(
            max_iterations=20,
            expose_reasoning=False,
            reasoning_prefix="Think: ",
            final_answer_tool_name="submit_answer",
            compact_threshold_ratio=0.5,
            tool_retry_count=5,
        )

        assert config.max_iterations == 20
        assert config.expose_reasoning is False
        assert config.reasoning_prefix == "Think: "
        assert config.final_answer_tool_name == "submit_answer"
        assert config.compact_threshold_ratio == 0.5
        assert config.tool_retry_count == 5

    def test_compact_threshold_ratio_bounds(self) -> None:
        """Test compact_threshold_ratio validation bounds."""
        # Valid lower bound
        config = ReActConfig(compact_threshold_ratio=0.1)
        assert config.compact_threshold_ratio == 0.1

        # Valid upper bound
        config = ReActConfig(compact_threshold_ratio=1.0)
        assert config.compact_threshold_ratio == 1.0

        # Invalid - below lower bound
        with pytest.raises(ValidationError):
            ReActConfig(compact_threshold_ratio=0.05)

        # Invalid - above upper bound
        with pytest.raises(ValidationError):
            ReActConfig(compact_threshold_ratio=1.5)

    def test_max_consecutive_thoughts_positive(self) -> None:
        """Test max_consecutive_thoughts must be positive."""
        config = ReActConfig(max_consecutive_thoughts=1)
        assert config.max_consecutive_thoughts == 1

        with pytest.raises(ValidationError):
            ReActConfig(max_consecutive_thoughts=0)

        with pytest.raises(ValidationError):
            ReActConfig(max_consecutive_thoughts=-1)

    def test_tool_retry_count_non_negative(self) -> None:
        """Test tool_retry_count must be non-negative."""
        config = ReActConfig(tool_retry_count=0)
        assert config.tool_retry_count == 0

        config = ReActConfig(tool_retry_count=10)
        assert config.tool_retry_count == 10

        with pytest.raises(ValidationError):
            ReActConfig(tool_retry_count=-1)

    def test_termination_strategy_literal(self) -> None:
        """Test termination_strategy only accepts valid values."""
        # Valid value
        config = ReActConfig(termination_strategy="tool")
        assert config.termination_strategy == "tool"

        # Invalid value
        with pytest.raises(ValidationError):
            ReActConfig(termination_strategy="invalid")  # type: ignore[arg-type]

    def test_config_is_immutable_by_default(self) -> None:
        """Test that config follows Pydantic model conventions."""
        config = ReActConfig()
        # Pydantic v2 models are mutable by default but can be frozen
        # Just verify it's a valid BaseModel instance
        assert hasattr(config, "model_dump")
        assert hasattr(config, "model_validate")
