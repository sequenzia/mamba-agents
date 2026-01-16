"""Tests for ReAct termination detection utilities."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock

from mamba_agents.workflows.react.termination import (
    detect_final_answer,
    extract_text_content,
    extract_tool_calls,
    extract_tool_results,
)


# Create named mock classes that match pydantic-ai structure
class TextPart:
    """Mock TextPart to simulate pydantic-ai."""

    def __init__(self, content: str) -> None:
        self.content = content


class ToolCallPart:
    """Mock ToolCallPart to simulate pydantic-ai."""

    def __init__(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_call_id: str = "call_123",
    ) -> None:
        self.tool_name = tool_name
        self.args = args
        self.tool_call_id = tool_call_id


class ToolReturnPart:
    """Mock ToolReturnPart to simulate pydantic-ai."""

    def __init__(
        self,
        tool_name: str,
        content: str,
        tool_call_id: str = "call_123",
    ) -> None:
        self.tool_name = tool_name
        self.content = content
        self.tool_call_id = tool_call_id


class ModelResponse:
    """Mock ModelResponse to simulate pydantic-ai."""

    def __init__(self, parts: list[Any]) -> None:
        self.parts = parts


class ModelRequest:
    """Mock ModelRequest to simulate pydantic-ai."""

    def __init__(self, parts: list[Any]) -> None:
        self.parts = parts


class MockAgentResult:
    """Mock AgentResult for testing."""

    def __init__(self, messages: list[Any]) -> None:
        self._messages = messages

    def new_messages(self) -> list[Any]:
        return self._messages


class TestDetectFinalAnswer:
    """Tests for detect_final_answer function."""

    def test_detect_final_answer_found(self) -> None:
        """Test detecting final_answer tool call."""
        tool_call = ToolCallPart(
            tool_name="final_answer",
            args={"answer": "The bug is in line 42"},
        )
        response = ModelResponse(parts=[tool_call])
        result = MockAgentResult([response])

        is_terminated, answer = detect_final_answer(result)

        assert is_terminated is True
        assert answer == "The bug is in line 42"

    def test_detect_final_answer_not_found(self) -> None:
        """Test when final_answer is not called."""
        tool_call = ToolCallPart(
            tool_name="read_file",
            args={"path": "main.py"},
        )
        response = ModelResponse(parts=[tool_call])
        result = MockAgentResult([response])

        is_terminated, answer = detect_final_answer(result)

        assert is_terminated is False
        assert answer is None

    def test_detect_final_answer_custom_tool_name(self) -> None:
        """Test detecting custom-named final answer tool."""
        tool_call = ToolCallPart(
            tool_name="submit_answer",
            args={"answer": "Custom answer"},
        )
        response = ModelResponse(parts=[tool_call])
        result = MockAgentResult([response])

        is_terminated, answer = detect_final_answer(result, tool_name="submit_answer")

        assert is_terminated is True
        assert answer == "Custom answer"

    def test_detect_final_answer_empty_messages(self) -> None:
        """Test with empty message list."""
        result = MockAgentResult([])

        is_terminated, answer = detect_final_answer(result)

        assert is_terminated is False
        assert answer is None

    def test_detect_final_answer_multiple_tool_calls(self) -> None:
        """Test with multiple tool calls, final_answer last."""
        tool_call1 = ToolCallPart(
            tool_name="read_file",
            args={"path": "main.py"},
        )
        tool_call2 = ToolCallPart(
            tool_name="final_answer",
            args={"answer": "Found the bug"},
        )
        response = ModelResponse(parts=[tool_call1, tool_call2])
        result = MockAgentResult([response])

        is_terminated, answer = detect_final_answer(result)

        assert is_terminated is True
        assert answer == "Found the bug"

    def test_detect_final_answer_args_not_dict(self) -> None:
        """Test when args is not a dict (edge case)."""
        # Create a mock with non-dict args
        tool_call = Mock()
        type(tool_call).__name__ = "ToolCallPart"
        tool_call.tool_name = "final_answer"
        tool_call.args = "plain string answer"

        response = Mock()
        type(response).__name__ = "ModelResponse"
        response.parts = [tool_call]

        result = MockAgentResult([response])

        is_terminated, answer = detect_final_answer(result)

        assert is_terminated is True
        assert answer == "plain string answer"


class TestExtractToolCalls:
    """Tests for extract_tool_calls function."""

    def test_extract_single_tool_call(self) -> None:
        """Test extracting a single tool call."""
        tool_call = ToolCallPart(
            tool_name="read_file",
            args={"path": "main.py"},
            tool_call_id="call_abc",
        )
        response = ModelResponse(parts=[tool_call])
        result = MockAgentResult([response])

        calls = extract_tool_calls(result)

        assert len(calls) == 1
        assert calls[0]["name"] == "read_file"
        assert calls[0]["args"] == {"path": "main.py"}
        assert calls[0]["id"] == "call_abc"

    def test_extract_multiple_tool_calls(self) -> None:
        """Test extracting multiple tool calls."""
        tool_call1 = ToolCallPart(
            tool_name="read_file",
            args={"path": "a.py"},
            tool_call_id="call_1",
        )
        tool_call2 = ToolCallPart(
            tool_name="grep_search",
            args={"pattern": "error"},
            tool_call_id="call_2",
        )
        response = ModelResponse(parts=[tool_call1, tool_call2])
        result = MockAgentResult([response])

        calls = extract_tool_calls(result)

        assert len(calls) == 2
        assert calls[0]["name"] == "read_file"
        assert calls[1]["name"] == "grep_search"

    def test_extract_no_tool_calls(self) -> None:
        """Test with no tool calls (text-only response)."""
        text_part = TextPart(content="I'm thinking...")
        response = ModelResponse(parts=[text_part])
        result = MockAgentResult([response])

        calls = extract_tool_calls(result)

        assert calls == []


class TestExtractToolResults:
    """Tests for extract_tool_results function."""

    def test_extract_single_result(self) -> None:
        """Test extracting a single tool result."""
        tool_return = ToolReturnPart(
            tool_name="read_file",
            content="File contents here",
            tool_call_id="call_abc",
        )
        request = ModelRequest(parts=[tool_return])
        result = MockAgentResult([request])

        results = extract_tool_results(result)

        assert len(results) == 1
        assert results[0]["name"] == "read_file"
        assert results[0]["content"] == "File contents here"
        assert results[0]["tool_call_id"] == "call_abc"

    def test_extract_multiple_results(self) -> None:
        """Test extracting multiple tool results."""
        return1 = ToolReturnPart(
            tool_name="read_file",
            content="Contents A",
            tool_call_id="call_1",
        )
        return2 = ToolReturnPart(
            tool_name="grep_search",
            content="Found 3 matches",
            tool_call_id="call_2",
        )
        request = ModelRequest(parts=[return1, return2])
        result = MockAgentResult([request])

        results = extract_tool_results(result)

        assert len(results) == 2
        assert results[0]["content"] == "Contents A"
        assert results[1]["content"] == "Found 3 matches"


class TestExtractTextContent:
    """Tests for extract_text_content function."""

    def test_extract_single_text(self) -> None:
        """Test extracting single text part."""
        text_part = TextPart(content="I'm analyzing the code.")
        response = ModelResponse(parts=[text_part])
        result = MockAgentResult([response])

        text = extract_text_content(result)

        assert text == "I'm analyzing the code."

    def test_extract_multiple_text_parts(self) -> None:
        """Test extracting multiple text parts."""
        text1 = TextPart(content="First part.")
        text2 = TextPart(content="Second part.")
        response = ModelResponse(parts=[text1, text2])
        result = MockAgentResult([response])

        text = extract_text_content(result)

        assert text == "First part.\nSecond part."

    def test_extract_text_with_tool_calls(self) -> None:
        """Test extracting text when mixed with tool calls."""
        text = TextPart(content="Let me check the file.")
        tool_call = ToolCallPart(tool_name="read_file", args={})
        response = ModelResponse(parts=[text, tool_call])
        result = MockAgentResult([response])

        extracted = extract_text_content(result)

        assert extracted == "Let me check the file."

    def test_extract_no_text(self) -> None:
        """Test when there's no text content."""
        tool_call = ToolCallPart(tool_name="read_file", args={})
        response = ModelResponse(parts=[tool_call])
        result = MockAgentResult([response])

        text = extract_text_content(result)

        assert text == ""
