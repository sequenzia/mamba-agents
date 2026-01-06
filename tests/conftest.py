"""Shared test fixtures and configuration for pydantic-agent tests."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

# Block all real model requests globally for safety
models.ALLOW_MODEL_REQUESTS = False


@pytest.fixture
def test_model() -> TestModel:
    """Provide a TestModel for deterministic testing.

    The TestModel allows specifying exact responses for predictable tests.
    """
    return TestModel()


@pytest.fixture
def test_model_with_response() -> type[TestModel]:
    """Factory fixture to create TestModel with specific responses.

    Usage:
        def test_something(test_model_with_response):
            model = test_model_with_response(result="expected output")
            # use model in test
    """
    return TestModel


@pytest.fixture
def tmp_sandbox(tmp_path: Path) -> Path:
    """Create a temporary sandbox directory for filesystem tests.

    Creates a directory structure suitable for testing filesystem operations:
    - sandbox/
      - file1.txt
      - file2.py
      - subdir/
        - nested.txt
    """
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()

    # Create test files
    (sandbox / "file1.txt").write_text("Hello, World!")
    (sandbox / "file2.py").write_text("print('Hello')")

    # Create subdirectory with nested file
    subdir = sandbox / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("Nested content")

    return sandbox


@pytest.fixture
def sample_messages() -> list[dict[str, Any]]:
    """Provide sample message history for context tests."""
    return [
        {"role": "user", "content": "Hello, can you help me?"},
        {"role": "assistant", "content": "Of course! What do you need help with?"},
        {"role": "user", "content": "I need to read a file."},
        {
            "role": "assistant",
            "content": "I'll help you read the file.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {"name": "read_file", "arguments": '{"path": "test.txt"}'},
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "content": "File contents here",
        },
        {"role": "assistant", "content": "The file contains: File contents here"},
    ]


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Set up mock environment variables for configuration tests.

    Returns the dict of set variables for assertions.
    """
    env_vars = {
        "AGENT_MODEL_BACKEND__BASE_URL": "http://test:8080/v1",
        "AGENT_MODEL_BACKEND__MODEL": "test-model",
        "AGENT_MODEL_BACKEND__API_KEY": "test-api-key",
        "AGENT_LOGGING__LEVEL": "DEBUG",
        "AGENT_RETRY__RETRY_LEVEL": "3",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def config_toml_content() -> str:
    """Provide sample TOML configuration content."""
    return """
[model_backend]
base_url = "http://localhost:11434/v1"
model = "llama3.2"
timeout = 30.0

[logging]
level = "INFO"
structured = true

[retry]
retry_level = 2
initial_backoff_seconds = 1.0

[context]
strategy = "sliding_window"
trigger_threshold_tokens = 100000
target_tokens = 80000
"""


@pytest.fixture
def config_toml_file(tmp_path: Path, config_toml_content: str) -> Path:
    """Create a temporary TOML configuration file."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_toml_content)
    return config_file


# Marker for integration tests
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (may require external services)",
    )
