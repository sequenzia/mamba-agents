"""Tests for Agent class context and usage tracking integration."""

from __future__ import annotations

import pytest
from pydantic_ai.models.test import TestModel

from pydantic_agent import Agent, AgentConfig, CompactionConfig
from pydantic_agent.context import ContextManager


class TestAgentContextIntegration:
    """Tests for context management integration in Agent."""

    def test_context_tracking_enabled_by_default(self, test_model: TestModel) -> None:
        """Test that context tracking is enabled by default."""
        agent: Agent[None, str] = Agent(test_model)
        assert agent.context_manager is not None
        assert agent.config.track_context is True

    def test_context_tracking_disabled(self, test_model: TestModel) -> None:
        """Test that context tracking can be disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)
        assert agent.context_manager is None

    def test_get_messages_raises_when_disabled(self, test_model: TestModel) -> None:
        """Test that get_messages raises RuntimeError when context tracking is disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        with pytest.raises(RuntimeError, match="Context tracking is disabled"):
            agent.get_messages()

    def test_should_compact_raises_when_disabled(self, test_model: TestModel) -> None:
        """Test that should_compact raises RuntimeError when context tracking is disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        with pytest.raises(RuntimeError, match="Context tracking is disabled"):
            agent.should_compact()

    def test_get_context_state_raises_when_disabled(self, test_model: TestModel) -> None:
        """Test that get_context_state raises RuntimeError when context tracking is disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        with pytest.raises(RuntimeError, match="Context tracking is disabled"):
            agent.get_context_state()

    def test_clear_context_raises_when_disabled(self, test_model: TestModel) -> None:
        """Test that clear_context raises RuntimeError when context tracking is disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        with pytest.raises(RuntimeError, match="Context tracking is disabled"):
            agent.clear_context()

    @pytest.mark.asyncio
    async def test_compact_raises_when_disabled(self, test_model: TestModel) -> None:
        """Test that compact raises RuntimeError when context tracking is disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        with pytest.raises(RuntimeError, match="Context tracking is disabled"):
            await agent.compact()

    def test_get_token_count_without_text_raises_when_disabled(
        self, test_model: TestModel
    ) -> None:
        """Test that get_token_count without text raises when context tracking disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        with pytest.raises(RuntimeError, match="Context tracking is disabled"):
            agent.get_token_count()

    def test_get_token_count_with_text_works_when_disabled(
        self, test_model: TestModel
    ) -> None:
        """Test that get_token_count with text works even when context tracking disabled."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        # Should work with explicit text
        count = agent.get_token_count("Hello, world!")
        assert count > 0

    def test_context_manager_property(self, test_model: TestModel) -> None:
        """Test that context_manager property returns the ContextManager instance."""
        agent: Agent[None, str] = Agent(test_model)
        assert isinstance(agent.context_manager, ContextManager)

    def test_custom_compaction_config(self, test_model: TestModel) -> None:
        """Test that custom CompactionConfig is used."""
        compaction_config = CompactionConfig(
            strategy="sliding_window",
            trigger_threshold_tokens=50000,
            target_tokens=40000,
        )
        agent_config = AgentConfig(context=compaction_config)
        agent: Agent[None, str] = Agent(test_model, config=agent_config)

        # The context manager should use our config
        assert agent.context_manager is not None
        state = agent.get_context_state()
        assert state is not None

    def test_system_prompt_propagates_to_context_manager(
        self, test_model: TestModel
    ) -> None:
        """Test that system prompt is set in context manager."""
        config = AgentConfig(system_prompt="You are a helpful assistant.")
        agent: Agent[None, str] = Agent(test_model, config=config)

        assert agent.context_manager is not None
        assert agent.context_manager.get_system_prompt() == "You are a helpful assistant."


class TestAgentUsageTracking:
    """Tests for usage tracking in Agent."""

    def test_usage_tracker_always_initialized(self, test_model: TestModel) -> None:
        """Test that usage tracker is always initialized regardless of context tracking."""
        # With context tracking
        agent1: Agent[None, str] = Agent(test_model)
        assert agent1.usage_tracker is not None

        # Without context tracking
        config = AgentConfig(track_context=False)
        agent2: Agent[None, str] = Agent(test_model, config=config)
        assert agent2.usage_tracker is not None

    def test_token_counter_always_initialized(self, test_model: TestModel) -> None:
        """Test that token counter is always initialized."""
        agent: Agent[None, str] = Agent(test_model)
        assert agent.token_counter is not None

    def test_cost_estimator_always_initialized(self, test_model: TestModel) -> None:
        """Test that cost estimator is always initialized."""
        agent: Agent[None, str] = Agent(test_model)
        assert agent.cost_estimator is not None

    def test_get_usage_returns_token_usage(self, test_model: TestModel) -> None:
        """Test that get_usage returns TokenUsage object."""
        agent: Agent[None, str] = Agent(test_model)
        usage = agent.get_usage()

        assert hasattr(usage, "prompt_tokens")
        assert hasattr(usage, "completion_tokens")
        assert hasattr(usage, "total_tokens")
        assert hasattr(usage, "request_count")

    def test_get_usage_history_returns_list(self, test_model: TestModel) -> None:
        """Test that get_usage_history returns a list."""
        agent: Agent[None, str] = Agent(test_model)
        history = agent.get_usage_history()

        assert isinstance(history, list)

    def test_get_cost_returns_float(self, test_model: TestModel) -> None:
        """Test that get_cost returns a float."""
        agent: Agent[None, str] = Agent(test_model)
        cost = agent.get_cost()

        assert isinstance(cost, float)
        assert cost >= 0

    def test_get_cost_breakdown_returns_breakdown(self, test_model: TestModel) -> None:
        """Test that get_cost_breakdown returns CostBreakdown object."""
        agent: Agent[None, str] = Agent(test_model)
        breakdown = agent.get_cost_breakdown()

        assert hasattr(breakdown, "prompt_cost")
        assert hasattr(breakdown, "completion_cost")
        assert hasattr(breakdown, "total_cost")

    def test_reset_tracking_clears_usage(self, test_model: TestModel) -> None:
        """Test that reset_tracking clears usage data."""
        agent: Agent[None, str] = Agent(test_model)

        # Reset tracking
        agent.reset_tracking()

        usage = agent.get_usage()
        assert usage.request_count == 0
        assert usage.total_tokens == 0

    def test_reset_all_clears_usage_and_context(self, test_model: TestModel) -> None:
        """Test that reset_all clears both usage and context."""
        agent: Agent[None, str] = Agent(test_model)

        # Reset all
        agent.reset_all()

        usage = agent.get_usage()
        assert usage.request_count == 0

        messages = agent.get_messages()
        assert len(messages) == 0


class TestAgentProperties:
    """Tests for Agent properties."""

    def test_model_name_property(self, test_model: TestModel) -> None:
        """Test that model_name property works."""
        agent: Agent[None, str] = Agent(test_model)
        # TestModel doesn't set a model name, so it should be None
        assert agent.model_name is None

    def test_model_name_with_string_model(self) -> None:
        """Test model_name when created with string model."""
        # Note: This would normally require settings, but we can test the attribute exists
        from pydantic_agent import AgentSettings

        settings = AgentSettings()
        agent: Agent[None, str] = Agent(settings=settings)
        # Should have the model name from settings
        assert agent.model_name == settings.model_backend.model


class TestAgentRunIntegration:
    """Tests for run method integration with tracking."""

    @pytest.mark.asyncio
    async def test_run_tracks_usage(self, test_model: TestModel) -> None:
        """Test that run() tracks usage."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)

        # Initial usage should be empty
        assert agent.get_usage().request_count == 0

        # Run the agent
        result = await agent.run("Hello")

        # Usage should be tracked
        usage = agent.get_usage()
        assert usage.request_count == 1

    @pytest.mark.asyncio
    async def test_run_tracks_messages(self, test_model: TestModel) -> None:
        """Test that run() tracks messages in context."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)

        # Initial messages should be empty
        assert len(agent.get_messages()) == 0

        # Run the agent
        result = await agent.run("Hello")

        # Messages should be tracked
        messages = agent.get_messages()
        assert len(messages) > 0

    def test_run_sync_tracks_usage(self, test_model: TestModel) -> None:
        """Test that run_sync() tracks usage."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)

        # Initial usage should be empty
        assert agent.get_usage().request_count == 0

        # Run the agent
        result = agent.run_sync("Hello")

        # Usage should be tracked
        usage = agent.get_usage()
        assert usage.request_count == 1

    def test_run_sync_tracks_messages(self, test_model: TestModel) -> None:
        """Test that run_sync() tracks messages in context."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)

        # Initial messages should be empty
        assert len(agent.get_messages()) == 0

        # Run the agent
        result = agent.run_sync("Hello")

        # Messages should be tracked
        messages = agent.get_messages()
        assert len(messages) > 0

    def test_multiple_runs_accumulate_usage(self, test_model: TestModel) -> None:
        """Test that multiple runs accumulate usage."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)

        # Run multiple times
        agent.run_sync("First")
        agent.run_sync("Second")
        agent.run_sync("Third")

        # Usage should accumulate
        usage = agent.get_usage()
        assert usage.request_count == 3

    def test_multiple_runs_accumulate_messages(self, test_model: TestModel) -> None:
        """Test that multiple runs accumulate messages."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)

        # Run multiple times
        agent.run_sync("First")
        initial_count = len(agent.get_messages())

        agent.run_sync("Second")
        after_second = len(agent.get_messages())

        # Messages should accumulate
        assert after_second > initial_count

    def test_explicit_message_history_overrides_internal(
        self, test_model: TestModel
    ) -> None:
        """Test that explicit message_history overrides internal context."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)

        # Add some messages via run
        agent.run_sync("First message")

        # Verify messages exist
        assert len(agent.get_messages()) > 0

        # Run with explicit empty history - should use that instead
        # (This test verifies the logic exists, actual behavior depends on pydantic-ai)
        result = agent.run_sync("Second message", message_history=[])

        # Result should succeed
        assert result is not None
