"""Tests for the Agent.messages property."""

from __future__ import annotations

from pydantic_ai.models.test import TestModel

from mamba_agents import Agent, AgentConfig
from mamba_agents.agent.messages import MessageQuery


class TestAgentMessagesProperty:
    """Tests that agent.messages returns a MessageQuery instance."""

    def test_returns_message_query_instance(self, test_model: TestModel) -> None:
        """Test that agent.messages returns a MessageQuery instance."""
        agent: Agent[None, str] = Agent(test_model)
        result = agent.messages
        assert isinstance(result, MessageQuery)

    def test_returns_new_instance_each_access(self, test_model: TestModel) -> None:
        """Test that each access creates a fresh MessageQuery (stateless)."""
        agent: Agent[None, str] = Agent(test_model)
        first = agent.messages
        second = agent.messages
        assert first is not second

    def test_uses_agents_token_counter(self, test_model: TestModel) -> None:
        """Test that MessageQuery receives the Agent's configured TokenCounter."""
        agent: Agent[None, str] = Agent(test_model)
        mq = agent.messages
        # The internal _token_counter should be the same object as the agent's
        assert mq._token_counter is agent.token_counter

    def test_get_messages_behavior_unchanged(self, test_model: TestModel) -> None:
        """Test that get_messages() still works normally alongside messages property."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)
        agent.run_sync("Hi there")

        # get_messages should still return a list of dicts
        raw_messages = agent.get_messages()
        assert isinstance(raw_messages, list)
        assert len(raw_messages) > 0

        # messages property should also see the same messages
        mq = agent.messages
        assert mq.all() == raw_messages


class TestAgentMessagesPropertyReflectsState:
    """Tests that agent.messages reflects the current Agent message state."""

    def test_reflects_current_messages_after_run(self, test_model: TestModel) -> None:
        """Test that MessageQuery contains messages after a run."""
        model = TestModel(custom_output_text="World!")
        agent: Agent[None, str] = Agent(model)
        agent.run_sync("Hello")

        mq = agent.messages
        all_msgs = mq.all()
        assert len(all_msgs) > 0

        # Should contain at least a user and assistant message
        roles = [msg.get("role") for msg in all_msgs]
        assert "user" in roles
        assert "assistant" in roles

    def test_reflects_accumulated_messages_after_multiple_runs(self, test_model: TestModel) -> None:
        """Test that messages accumulate across multiple runs."""
        model = TestModel(custom_output_text="Reply")
        agent: Agent[None, str] = Agent(model)

        agent.run_sync("First")
        count_after_first = len(agent.messages.all())

        agent.run_sync("Second")
        count_after_second = len(agent.messages.all())

        assert count_after_second > count_after_first


class TestAgentMessagesPropertyEdgeCases:
    """Tests for edge cases with the messages property."""

    def test_empty_messages_before_any_run(self, test_model: TestModel) -> None:
        """Test that messages property works when no messages exist."""
        agent: Agent[None, str] = Agent(test_model)
        mq = agent.messages
        assert isinstance(mq, MessageQuery)
        assert mq.all() == []

    def test_works_after_clear_context(self, test_model: TestModel) -> None:
        """Test that messages reflects cleared state after clear_context()."""
        model = TestModel(custom_output_text="Hello!")
        agent: Agent[None, str] = Agent(model)
        agent.run_sync("Hello")

        # Verify messages exist
        assert len(agent.messages.all()) > 0

        # Clear context
        agent.clear_context()

        # Messages should now be empty
        mq = agent.messages
        assert isinstance(mq, MessageQuery)
        assert mq.all() == []

    def test_works_with_track_context_disabled(self, test_model: TestModel) -> None:
        """Test that messages property works when track_context=False."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        # Should not raise, should return MessageQuery with empty list
        mq = agent.messages
        assert isinstance(mq, MessageQuery)
        assert mq.all() == []

    def test_token_counter_present_when_context_disabled(self, test_model: TestModel) -> None:
        """Test that MessageQuery still has TokenCounter when context tracking is off."""
        config = AgentConfig(track_context=False)
        agent: Agent[None, str] = Agent(test_model, config=config)

        mq = agent.messages
        # TokenCounter should still be provided
        assert mq._token_counter is agent.token_counter


class TestAgentMessagesPropertyIntegration:
    """Integration tests for the messages property with Agent run lifecycle."""

    def test_messages_property_lifecycle(self, test_model: TestModel) -> None:
        """Test full lifecycle: run -> check messages -> clear -> check empty."""
        model = TestModel(custom_output_text="Response")
        agent: Agent[None, str] = Agent(model)

        # Before any run: empty
        assert len(agent.messages.all()) == 0

        # After first run: messages present
        agent.run_sync("Hello")
        msgs_after_run = agent.messages.all()
        assert len(msgs_after_run) > 0

        # Filter via messages property
        user_msgs = agent.messages.filter(role="user")
        assert len(user_msgs) > 0

        # After clear: empty again
        agent.clear_context()
        assert len(agent.messages.all()) == 0

    def test_messages_stats_work_after_run(self, test_model: TestModel) -> None:
        """Test that analytics methods on MessageQuery work via the property."""
        model = TestModel(custom_output_text="Stats test")
        agent: Agent[None, str] = Agent(model)
        agent.run_sync("Hello")

        stats = agent.messages.stats()
        assert stats.total_messages > 0
        assert stats.total_messages == len(agent.messages.all())

    def test_messages_property_consistent_with_get_messages(self, test_model: TestModel) -> None:
        """Test that messages.all() is consistent with get_messages()."""
        model = TestModel(custom_output_text="Consistency")
        agent: Agent[None, str] = Agent(model)

        agent.run_sync("First")
        agent.run_sync("Second")

        # Both should return the same data
        property_msgs = agent.messages.all()
        method_msgs = agent.get_messages()
        assert property_msgs == method_msgs
