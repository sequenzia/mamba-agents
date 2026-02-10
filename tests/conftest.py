"""Shared test fixtures and configuration for mamba-agents tests."""

from __future__ import annotations

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
        "MAMBA_MODEL_BACKEND__BASE_URL": "http://test:8080/v1",
        "MAMBA_MODEL_BACKEND__MODEL": "test-model",
        "MAMBA_MODEL_BACKEND__API_KEY": "test-api-key",
        "MAMBA_LOGGING__LEVEL": "DEBUG",
        "MAMBA_RETRY__RETRY_LEVEL": "3",
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


# ---------------------------------------------------------------------------
# Skill test fixtures
# ---------------------------------------------------------------------------

_SAMPLE_SKILL_FRONTMATTER = """\
---
name: {name}
description: A sample skill called {name}
---

# {name}

This is the skill body for {name}.

Process: $ARGUMENTS
"""


@pytest.fixture
def sample_skill_dir(tmp_path: Path) -> Path:
    """Create a temporary skill directory with valid SKILL.md files.

    Structure::

        skills/
            alpha/
                SKILL.md     (valid, with body and $ARGUMENTS placeholder)
            beta/
                SKILL.md     (valid, minimal)
                references/
                    guide.md

    Returns:
        Path to the ``skills/`` parent directory.
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Alpha skill - standard skill with body
    alpha_dir = skills_dir / "alpha"
    alpha_dir.mkdir()
    (alpha_dir / "SKILL.md").write_text(
        _SAMPLE_SKILL_FRONTMATTER.format(name="alpha"),
        encoding="utf-8",
    )

    # Beta skill - with references directory
    beta_dir = skills_dir / "beta"
    beta_dir.mkdir()
    (beta_dir / "SKILL.md").write_text(
        "---\nname: beta\ndescription: A sample skill called beta\n---\n\n"
        "# beta\n\nBeta body content.\n",
        encoding="utf-8",
    )
    refs_dir = beta_dir / "references"
    refs_dir.mkdir()
    (refs_dir / "guide.md").write_text("# Guide\n\nReference content here.\n")

    return skills_dir


@pytest.fixture
def sample_skill_info():
    """Create a minimal SkillInfo fixture with required fields.

    Returns:
        A ``SkillInfo`` dataclass instance with sensible defaults.
    """
    from mamba_agents.skills.config import SkillInfo, SkillScope

    return SkillInfo(
        name="sample-skill",
        description="A sample skill for testing",
        path=Path("/test/skills/sample-skill"),
        scope=SkillScope.PROJECT,
    )


@pytest.fixture
def sample_skill():
    """Create a full Skill fixture with body content.

    Returns:
        A ``Skill`` Pydantic model with info and body populated.
    """
    from mamba_agents.skills.config import Skill, SkillInfo, SkillScope

    info = SkillInfo(
        name="sample-skill",
        description="A sample skill for testing",
        path=Path("/test/skills/sample-skill"),
        scope=SkillScope.PROJECT,
    )
    return Skill(
        info=info,
        body="# Sample Skill\n\nProcess: $ARGUMENTS\n\nDo something useful.",
    )


# ---------------------------------------------------------------------------
# Subagent test fixtures
# ---------------------------------------------------------------------------

_SAMPLE_AGENT_FRONTMATTER = """\
---
name: {name}
description: A sample subagent called {name}
---

You are the {name} subagent. Follow instructions carefully.
"""


@pytest.fixture
def sample_subagent_config():
    """Create a minimal SubagentConfig fixture for testing.

    Returns:
        A ``SubagentConfig`` instance with sensible defaults.
    """
    from mamba_agents.subagents.config import SubagentConfig

    return SubagentConfig(
        name="sample-subagent",
        description="A sample subagent for testing",
    )


@pytest.fixture
def sample_agent_dir(tmp_path: Path) -> Path:
    """Create a temporary agent directory with valid subagent ``.md`` files.

    Structure::

        agents/
            helper.md     (valid, with frontmatter and body)
            researcher.md (valid, minimal)

    Returns:
        Path to the ``agents/`` directory.
    """
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    # Helper agent - with body
    (agents_dir / "helper.md").write_text(
        _SAMPLE_AGENT_FRONTMATTER.format(name="helper"),
        encoding="utf-8",
    )

    # Researcher agent - minimal
    (agents_dir / "researcher.md").write_text(
        "---\nname: researcher\ndescription: A research subagent\n---\n\n"
        "You are a research assistant.\n",
        encoding="utf-8",
    )

    return agents_dir


# Marker for integration tests
def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (may require external services)",
    )
