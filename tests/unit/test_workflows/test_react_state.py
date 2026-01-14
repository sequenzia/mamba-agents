"""Tests for ReActState and ScratchpadEntry."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic_agent.workflows import ReActConfig, ReActState, ScratchpadEntry


class TestScratchpadEntry:
    """Tests for ScratchpadEntry dataclass."""

    def test_create_thought_entry(self) -> None:
        """Test creating a thought entry."""
        entry = ScratchpadEntry(
            entry_type="thought",
            content="I should read the file first.",
        )

        assert entry.entry_type == "thought"
        assert entry.content == "I should read the file first."
        assert entry.token_count == 0
        assert entry.metadata == {}
        assert isinstance(entry.timestamp, datetime)

    def test_create_action_entry(self) -> None:
        """Test creating an action entry."""
        entry = ScratchpadEntry(
            entry_type="action",
            content="read_file(path='main.py')",
            token_count=10,
            metadata={"tool_name": "read_file"},
        )

        assert entry.entry_type == "action"
        assert entry.content == "read_file(path='main.py')"
        assert entry.token_count == 10
        assert entry.metadata == {"tool_name": "read_file"}

    def test_create_observation_entry(self) -> None:
        """Test creating an observation entry."""
        entry = ScratchpadEntry(
            entry_type="observation",
            content="File contents: def main(): ...",
            metadata={"is_error": False},
        )

        assert entry.entry_type == "observation"
        assert entry.content == "File contents: def main(): ..."
        assert entry.metadata == {"is_error": False}


class TestReActState:
    """Tests for ReActState dataclass."""

    def test_create_initial_state(self) -> None:
        """Test creating initial state."""
        state = ReActState(task="Find the bug in main.py")

        assert state.task == "Find the bug in main.py"
        assert state.scratchpad == []
        assert state.current_thought is None
        assert state.current_action is None
        assert state.current_observation is None
        assert state.is_terminated is False
        assert state.termination_reason is None
        assert state.final_answer is None
        assert state.iteration_token_counts == []
        assert state.total_tokens_used == 0
        assert state.compaction_count == 0
        assert state.consecutive_thought_count == 0

    def test_add_thought(self) -> None:
        """Test adding a thought."""
        state = ReActState(task="Test task")

        state.add_thought("I should analyze the code.", token_count=10)

        assert len(state.scratchpad) == 1
        assert state.scratchpad[0].entry_type == "thought"
        assert state.scratchpad[0].content == "I should analyze the code."
        assert state.scratchpad[0].token_count == 10
        assert state.current_thought == "I should analyze the code."
        assert state.consecutive_thought_count == 1

    def test_add_thought_increments_consecutive_count(self) -> None:
        """Test that consecutive thoughts increment the counter."""
        state = ReActState(task="Test task")

        state.add_thought("First thought")
        assert state.consecutive_thought_count == 1

        state.add_thought("Second thought")
        assert state.consecutive_thought_count == 2

        state.add_thought("Third thought")
        assert state.consecutive_thought_count == 3

    def test_add_action(self) -> None:
        """Test adding an action."""
        state = ReActState(task="Test task")

        state.add_action(
            "read_file(path='main.py')",
            token_count=5,
            metadata={"tool_name": "read_file", "tool_args": {"path": "main.py"}},
        )

        assert len(state.scratchpad) == 1
        assert state.scratchpad[0].entry_type == "action"
        assert state.scratchpad[0].content == "read_file(path='main.py')"
        assert state.current_action == "read_file(path='main.py')"
        assert state.scratchpad[0].metadata == {
            "tool_name": "read_file",
            "tool_args": {"path": "main.py"},
        }

    def test_add_action_resets_consecutive_count(self) -> None:
        """Test that adding an action resets consecutive thought count."""
        state = ReActState(task="Test task")

        state.add_thought("First thought")
        state.add_thought("Second thought")
        assert state.consecutive_thought_count == 2

        state.add_action("some_tool()")
        assert state.consecutive_thought_count == 0

    def test_add_observation(self) -> None:
        """Test adding an observation."""
        state = ReActState(task="Test task")

        state.add_observation(
            "File contents here",
            token_count=20,
            metadata={"tool_name": "read_file", "is_error": False},
        )

        assert len(state.scratchpad) == 1
        assert state.scratchpad[0].entry_type == "observation"
        assert state.scratchpad[0].content == "File contents here"
        assert state.current_observation == "File contents here"

    def test_get_scratchpad_text_empty(self) -> None:
        """Test scratchpad text with empty scratchpad."""
        state = ReActState(task="Test task")
        config = ReActConfig()

        assert state.get_scratchpad_text(config) == ""

    def test_get_scratchpad_text_formatted(self) -> None:
        """Test scratchpad text formatting."""
        state = ReActState(task="Test task")
        config = ReActConfig(
            reasoning_prefix="Think: ",
            action_prefix="Do: ",
            observation_prefix="See: ",
        )

        state.add_thought("I need to read the file")
        state.add_action("read_file('main.py')")
        state.add_observation("def main(): pass")

        text = state.get_scratchpad_text(config)
        lines = text.split("\n")

        assert lines[0] == "Think: I need to read the file"
        assert lines[1] == "Do: read_file('main.py')"
        assert lines[2] == "See: def main(): pass"

    def test_get_scratchpad_text_with_default_prefixes(self) -> None:
        """Test scratchpad text with default prefixes."""
        state = ReActState(task="Test task")
        config = ReActConfig()

        state.add_thought("Analyzing the code")
        state.add_action("grep_search(pattern='error')")
        state.add_observation("Found 3 matches")

        text = state.get_scratchpad_text(config)

        assert "Thought: Analyzing the code" in text
        assert "Action: grep_search(pattern='error')" in text
        assert "Observation: Found 3 matches" in text

    def test_get_thoughts(self) -> None:
        """Test getting all thoughts."""
        state = ReActState(task="Test task")

        state.add_thought("First thought")
        state.add_action("some_action()")
        state.add_thought("Second thought")
        state.add_observation("Some observation")

        thoughts = state.get_thoughts()
        assert thoughts == ["First thought", "Second thought"]

    def test_get_actions(self) -> None:
        """Test getting all actions."""
        state = ReActState(task="Test task")

        state.add_thought("First thought")
        state.add_action("action1()")
        state.add_observation("obs1")
        state.add_action("action2()")

        actions = state.get_actions()
        assert actions == ["action1()", "action2()"]

    def test_get_observations(self) -> None:
        """Test getting all observations."""
        state = ReActState(task="Test task")

        state.add_action("action1()")
        state.add_observation("Result 1")
        state.add_action("action2()")
        state.add_observation("Result 2")

        observations = state.get_observations()
        assert observations == ["Result 1", "Result 2"]

    def test_full_react_cycle(self) -> None:
        """Test a full Thought-Action-Observation cycle."""
        state = ReActState(task="Find the bug")
        config = ReActConfig()

        # First iteration
        state.add_thought("I'll start by reading the main file")
        state.add_action(
            "read_file(path='main.py')",
            metadata={"tool_name": "read_file"},
        )
        state.add_observation("def main():\n    print(undefined_var)")

        # Second iteration
        state.add_thought("I found the bug - undefined_var is not defined")
        state.add_action(
            "final_answer(answer='undefined_var is not defined')",
            metadata={"tool_name": "final_answer"},
        )

        assert len(state.scratchpad) == 5
        assert state.get_thoughts() == [
            "I'll start by reading the main file",
            "I found the bug - undefined_var is not defined",
        ]
        assert len(state.get_actions()) == 2
        assert len(state.get_observations()) == 1

        # Verify scratchpad text
        text = state.get_scratchpad_text(config)
        assert "Thought:" in text
        assert "Action:" in text
        assert "Observation:" in text
