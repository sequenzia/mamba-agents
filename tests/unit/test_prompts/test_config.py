"""Tests for prompt configuration classes."""

from pathlib import Path

from mamba_agents.prompts.config import PromptConfig, TemplateConfig


class TestPromptConfig:
    """Tests for PromptConfig."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = PromptConfig()

        assert config.prompts_dir == Path("prompts")
        assert config.default_version == "v1"
        assert config.file_extension == ".jinja2"
        assert config.enable_caching is True
        assert config.strict_mode is False

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = PromptConfig(
            prompts_dir=Path("/custom/prompts"),
            default_version="v2",
            file_extensions=[".txt", ".custom"],
            enable_caching=False,
            strict_mode=True,
        )

        assert config.prompts_dir == Path("/custom/prompts")
        assert config.default_version == "v2"
        assert config.file_extensions == [".txt", ".custom"]
        assert config.file_extension == ".txt"  # Property returns first
        assert config.enable_caching is False
        assert config.strict_mode is True

    def test_string_path_conversion(self) -> None:
        """Test that string paths are converted to Path objects."""
        config = PromptConfig(prompts_dir="my/prompts")
        assert isinstance(config.prompts_dir, Path)
        assert config.prompts_dir == Path("my/prompts")


class TestTemplateConfig:
    """Tests for TemplateConfig."""

    def test_required_name(self) -> None:
        """Test that name is required."""
        config = TemplateConfig(name="system/assistant")
        assert config.name == "system/assistant"

    def test_default_values(self) -> None:
        """Test default values."""
        config = TemplateConfig(name="test")

        assert config.name == "test"
        assert config.version is None
        assert config.variables == {}

    def test_with_variables(self) -> None:
        """Test configuration with variables."""
        config = TemplateConfig(
            name="system/assistant",
            version="v2",
            variables={"name": "Helper", "role": "assistant"},
        )

        assert config.name == "system/assistant"
        assert config.version == "v2"
        assert config.variables == {"name": "Helper", "role": "assistant"}

    def test_model_dump(self) -> None:
        """Test serialization."""
        config = TemplateConfig(
            name="system/assistant",
            variables={"key": "value"},
        )

        data = config.model_dump()
        assert data["name"] == "system/assistant"
        assert data["version"] is None
        assert data["variables"] == {"key": "value"}
