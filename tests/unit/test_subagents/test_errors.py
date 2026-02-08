"""Tests for subagent error classes."""

import pickle

from mamba_agents.subagents.errors import (
    SubagentConfigError,
    SubagentDelegationError,
    SubagentError,
    SubagentNestingError,
    SubagentNotFoundError,
    SubagentTimeoutError,
)


class TestSubagentError:
    """Tests for base SubagentError."""

    def test_is_exception(self) -> None:
        """Test SubagentError is an Exception."""
        error = SubagentError("Test error")
        assert isinstance(error, Exception)

    def test_message_attribute(self) -> None:
        """Test error stores message attribute."""
        error = SubagentError("Custom message")
        assert error.message == "Custom message"

    def test_str(self) -> None:
        """Test str() produces clear output."""
        error = SubagentError("Something went wrong")
        assert str(error) == "Something went wrong"

    def test_repr(self) -> None:
        """Test repr() produces useful debugging info."""
        error = SubagentError("Something went wrong")
        assert repr(error) == "SubagentError('Something went wrong')"

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SubagentError("Pickle test")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.message == error.message

    def test_catches_all_subagent_errors(self) -> None:
        """Test base class catches all subagent-related errors."""
        errors = [
            SubagentError("base"),
            SubagentConfigError("test", "bad config"),
            SubagentNotFoundError("missing"),
            SubagentNestingError("child", "parent"),
            SubagentDelegationError("worker", "do stuff"),
            SubagentTimeoutError("slow", max_turns=10),
        ]
        for error in errors:
            assert isinstance(error, SubagentError)


class TestSubagentConfigError:
    """Tests for SubagentConfigError."""

    def test_inheritance(self) -> None:
        """Test error inherits from SubagentError."""
        error = SubagentConfigError("test-agent", "missing required field 'name'")
        assert isinstance(error, SubagentError)
        assert isinstance(error, Exception)

    def test_contextual_attributes(self) -> None:
        """Test error includes name and detail attributes."""
        error = SubagentConfigError("my-agent", "model field is invalid")
        assert error.name == "my-agent"
        assert error.detail == "model field is invalid"

    def test_message_is_clear(self) -> None:
        """Test error message is clear and actionable."""
        error = SubagentConfigError("my-agent", "tools must be a list")
        message = str(error)
        assert "my-agent" in message
        assert "tools must be a list" in message
        assert "Invalid configuration" in message

    def test_repr(self) -> None:
        """Test repr() produces useful debugging info."""
        error = SubagentConfigError("my-agent", "bad model")
        result = repr(error)
        assert "SubagentConfigError" in result
        assert "my-agent" in result
        assert "bad model" in result

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SubagentConfigError("test", "detail")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == error.name
        assert restored.detail == error.detail


class TestSubagentNotFoundError:
    """Tests for SubagentNotFoundError."""

    def test_inheritance(self) -> None:
        """Test error inherits from SubagentError."""
        error = SubagentNotFoundError("missing-agent")
        assert isinstance(error, SubagentError)
        assert isinstance(error, Exception)

    def test_basic_error(self) -> None:
        """Test error with just config_name."""
        error = SubagentNotFoundError("researcher")
        assert error.config_name == "researcher"
        assert error.available is None
        assert "researcher" in str(error)

    def test_error_with_available_configs(self) -> None:
        """Test error includes available configurations."""
        error = SubagentNotFoundError("researcher", available=["coder", "reviewer"])
        assert error.config_name == "researcher"
        assert error.available == ["coder", "reviewer"]
        message = str(error)
        assert "researcher" in message
        assert "coder" in message
        assert "reviewer" in message

    def test_message_is_clear(self) -> None:
        """Test error message is clear and actionable."""
        error = SubagentNotFoundError("missing-agent")
        assert "not found" in str(error).lower()

    def test_repr(self) -> None:
        """Test repr() produces useful debugging info."""
        error = SubagentNotFoundError("agent-x", available=["agent-a"])
        result = repr(error)
        assert "SubagentNotFoundError" in result
        assert "agent-x" in result
        assert "agent-a" in result

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SubagentNotFoundError("test", available=["a", "b"])
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.config_name == error.config_name
        assert restored.available == error.available

    def test_picklable_without_available(self) -> None:
        """Test error without available list can be pickled."""
        error = SubagentNotFoundError("test")
        restored = pickle.loads(pickle.dumps(error))
        assert restored.config_name == "test"
        assert restored.available is None


class TestSubagentNestingError:
    """Tests for SubagentNestingError."""

    def test_inheritance(self) -> None:
        """Test error inherits from SubagentError."""
        error = SubagentNestingError("child", "parent")
        assert isinstance(error, SubagentError)
        assert isinstance(error, Exception)

    def test_contextual_attributes(self) -> None:
        """Test error includes name and parent_name attributes."""
        error = SubagentNestingError("sub-worker", "main-agent")
        assert error.name == "sub-worker"
        assert error.parent_name == "main-agent"

    def test_message_is_clear(self) -> None:
        """Test error message explains nesting is not allowed."""
        error = SubagentNestingError("sub-worker", "main-agent")
        message = str(error)
        assert "sub-worker" in message
        assert "main-agent" in message
        assert "nesting" in message.lower() or "sub-subagent" in message.lower()

    def test_repr(self) -> None:
        """Test repr() produces useful debugging info."""
        error = SubagentNestingError("child", "parent")
        result = repr(error)
        assert "SubagentNestingError" in result
        assert "child" in result
        assert "parent" in result

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SubagentNestingError("child", "parent")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == error.name
        assert restored.parent_name == error.parent_name


class TestSubagentDelegationError:
    """Tests for SubagentDelegationError."""

    def test_inheritance(self) -> None:
        """Test error inherits from SubagentError."""
        error = SubagentDelegationError("worker", "analyze data")
        assert isinstance(error, SubagentError)
        assert isinstance(error, Exception)

    def test_basic_error(self) -> None:
        """Test error with name and task."""
        error = SubagentDelegationError("worker", "analyze data")
        assert error.name == "worker"
        assert error.task == "analyze data"
        assert error.cause is None
        assert "worker" in str(error)
        assert "analyze data" in str(error)

    def test_error_with_cause(self) -> None:
        """Test error with underlying cause."""
        cause = RuntimeError("Connection failed")
        error = SubagentDelegationError("worker", "fetch results", cause=cause)
        assert error.name == "worker"
        assert error.task == "fetch results"
        assert error.cause is cause
        message = str(error)
        assert "worker" in message
        assert "fetch results" in message
        assert "Connection failed" in message

    def test_message_is_clear(self) -> None:
        """Test error message is clear and actionable."""
        error = SubagentDelegationError("worker", "process data")
        message = str(error)
        assert "failed" in message.lower() or "delegation" in message.lower()

    def test_repr(self) -> None:
        """Test repr() produces useful debugging info."""
        cause = ValueError("bad input")
        error = SubagentDelegationError("worker", "task", cause=cause)
        result = repr(error)
        assert "SubagentDelegationError" in result
        assert "worker" in result
        assert "task" in result

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SubagentDelegationError("worker", "task")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == error.name
        assert restored.task == error.task

    def test_picklable_with_cause(self) -> None:
        """Test error with cause can be pickled."""
        cause = RuntimeError("oops")
        error = SubagentDelegationError("worker", "task", cause=cause)
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert str(restored.cause) == str(cause)


class TestSubagentTimeoutError:
    """Tests for SubagentTimeoutError."""

    def test_inheritance(self) -> None:
        """Test error inherits from SubagentError."""
        error = SubagentTimeoutError("slow-agent", max_turns=10)
        assert isinstance(error, SubagentError)
        assert isinstance(error, Exception)

    def test_basic_error(self) -> None:
        """Test error with name and max_turns."""
        error = SubagentTimeoutError("slow-agent", max_turns=5)
        assert error.name == "slow-agent"
        assert error.max_turns == 5
        assert error.turns_used is None
        message = str(error)
        assert "slow-agent" in message
        assert "5" in message

    def test_error_with_turns_used(self) -> None:
        """Test error includes turns_used when provided."""
        error = SubagentTimeoutError("slow-agent", max_turns=5, turns_used=6)
        assert error.name == "slow-agent"
        assert error.max_turns == 5
        assert error.turns_used == 6
        message = str(error)
        assert "slow-agent" in message
        assert "5" in message
        assert "6" in message

    def test_message_is_clear(self) -> None:
        """Test error message is clear and actionable."""
        error = SubagentTimeoutError("agent", max_turns=10)
        message = str(error)
        assert "exceeded" in message.lower() or "maximum" in message.lower()

    def test_repr(self) -> None:
        """Test repr() produces useful debugging info."""
        error = SubagentTimeoutError("agent", max_turns=10, turns_used=12)
        result = repr(error)
        assert "SubagentTimeoutError" in result
        assert "agent" in result
        assert "10" in result
        assert "12" in result

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SubagentTimeoutError("agent", max_turns=10, turns_used=12)
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == error.name
        assert restored.max_turns == error.max_turns
        assert restored.turns_used == error.turns_used

    def test_picklable_without_turns_used(self) -> None:
        """Test error without turns_used can be pickled."""
        error = SubagentTimeoutError("agent", max_turns=5)
        restored = pickle.loads(pickle.dumps(error))
        assert restored.turns_used is None


class TestInheritanceChain:
    """Tests for the complete inheritance hierarchy."""

    def test_all_errors_are_subagent_errors(self) -> None:
        """Test all errors inherit from SubagentError."""
        assert issubclass(SubagentConfigError, SubagentError)
        assert issubclass(SubagentNotFoundError, SubagentError)
        assert issubclass(SubagentNestingError, SubagentError)
        assert issubclass(SubagentDelegationError, SubagentError)
        assert issubclass(SubagentTimeoutError, SubagentError)

    def test_all_errors_are_exceptions(self) -> None:
        """Test all errors inherit from Exception."""
        error_classes = [
            SubagentError,
            SubagentConfigError,
            SubagentNotFoundError,
            SubagentNestingError,
            SubagentDelegationError,
            SubagentTimeoutError,
        ]
        for cls in error_classes:
            assert issubclass(cls, Exception)

    def test_subagent_error_is_direct_exception_subclass(self) -> None:
        """Test SubagentError directly extends Exception."""
        assert SubagentError.__bases__ == (Exception,)

    def test_catch_all_with_base(self) -> None:
        """Test catching SubagentError catches all subtypes."""
        errors = [
            SubagentConfigError("a", "b"),
            SubagentNotFoundError("a"),
            SubagentNestingError("a", "b"),
            SubagentDelegationError("a", "b"),
            SubagentTimeoutError("a", max_turns=1),
        ]
        for error in errors:
            try:
                raise error
            except SubagentError as caught:
                assert caught is error
            else:
                raise AssertionError(f"Expected {type(error).__name__} to be caught")

    def test_specific_catch_does_not_catch_siblings(self) -> None:
        """Test specific error types do not catch sibling types."""
        try:
            raise SubagentConfigError("a", "b")
        except SubagentNotFoundError:
            raise AssertionError(  # noqa: B904
                "SubagentNotFoundError should not catch SubagentConfigError"
            )
        except SubagentConfigError:
            pass  # Expected
