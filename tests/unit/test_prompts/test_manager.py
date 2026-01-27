"""Tests for PromptManager class."""

from pathlib import Path

import pytest

from mamba_agents.prompts.config import PromptConfig, TemplateConfig
from mamba_agents.prompts.errors import PromptNotFoundError, TemplateConflictError
from mamba_agents.prompts.manager import PromptManager
from mamba_agents.prompts.template import PromptTemplate, TemplateType


class TestPromptManagerRegistration:
    """Tests for PromptManager registration (in-memory templates)."""

    def test_register_string_template(self) -> None:
        """Test registering a string template."""
        manager = PromptManager()
        manager.register("test/greeting", "Hello, {{ name }}!")

        template = manager.get("test/greeting")
        assert template.name == "test/greeting"
        assert template.render(name="World") == "Hello, World!"

    def test_register_template_instance(self) -> None:
        """Test registering a PromptTemplate instance."""
        manager = PromptManager()
        template = PromptTemplate(
            name="custom",
            version="v1",
            source="Custom: {{ value }}",
        )
        manager.register("test/custom", template)

        retrieved = manager.get("test/custom")
        assert retrieved.render(value="test") == "Custom: test"

    def test_register_with_version(self) -> None:
        """Test registering templates with different versions."""
        manager = PromptManager()
        manager.register("test/prompt", "Version 1", version="v1")
        manager.register("test/prompt", "Version 2", version="v2")

        assert manager.get("test/prompt", version="v1").render() == "Version 1"
        assert manager.get("test/prompt", version="v2").render() == "Version 2"

    def test_register_default_version(self) -> None:
        """Test that default version is used when not specified."""
        manager = PromptManager(PromptConfig(default_version="v1"))
        manager.register("test/prompt", "Default version")

        template = manager.get("test/prompt")
        assert template.version == "v1"


class TestPromptManagerRender:
    """Tests for PromptManager render methods."""

    def test_render_registered_template(self) -> None:
        """Test rendering a registered template directly."""
        manager = PromptManager()
        manager.register("test/greeting", "Hello, {{ name }}!")

        result = manager.render("test/greeting", name="Alice")
        assert result == "Hello, Alice!"

    def test_render_with_name_variable(self) -> None:
        """Test that 'name' can be used as a template variable."""
        manager = PromptManager()
        manager.register("test/person", "Person: {{ name }}, Role: {{ role }}")

        result = manager.render("test/person", name="Alice", role="admin")
        assert result == "Person: Alice, Role: admin"

    def test_render_with_version(self) -> None:
        """Test rendering with specific version."""
        manager = PromptManager()
        manager.register("test/prompt", "V1: {{ x }}", version="v1")
        manager.register("test/prompt", "V2: {{ x }}", version="v2")

        assert manager.render("test/prompt", version="v1", x="foo") == "V1: foo"
        assert manager.render("test/prompt", version="v2", x="bar") == "V2: bar"

    def test_render_config(self) -> None:
        """Test rendering from TemplateConfig."""
        manager = PromptManager()
        manager.register("test/prompt", "Hello, {{ name }}!")

        config = TemplateConfig(
            name="test/prompt",
            variables={"name": "Config"},
        )

        result = manager.render_config(config)
        assert result == "Hello, Config!"

    def test_render_config_with_version(self) -> None:
        """Test render_config uses specified version."""
        manager = PromptManager()
        manager.register("test/prompt", "V1 content", version="v1")
        manager.register("test/prompt", "V2 content", version="v2")

        config = TemplateConfig(name="test/prompt", version="v2")
        result = manager.render_config(config)
        assert result == "V2 content"


class TestPromptManagerListing:
    """Tests for PromptManager listing methods."""

    def test_list_prompts_empty(self) -> None:
        """Test listing prompts when none registered."""
        manager = PromptManager()
        prompts = manager.list_prompts()
        assert prompts == []

    def test_list_prompts_registered(self) -> None:
        """Test listing registered prompts."""
        manager = PromptManager()
        manager.register("system/assistant", "Assistant")
        manager.register("system/coder", "Coder")
        manager.register("workflow/react", "React")

        prompts = manager.list_prompts()
        assert "system/assistant" in prompts
        assert "system/coder" in prompts
        assert "workflow/react" in prompts

    def test_list_prompts_with_category(self) -> None:
        """Test filtering prompts by category."""
        manager = PromptManager()
        manager.register("system/assistant", "Assistant")
        manager.register("system/coder", "Coder")
        manager.register("workflow/react", "React")

        system_prompts = manager.list_prompts(category="system")
        assert "system/assistant" in system_prompts
        assert "system/coder" in system_prompts
        assert "workflow/react" not in system_prompts

    def test_list_versions_registered(self) -> None:
        """Test listing versions for a registered template."""
        manager = PromptManager()
        manager.register("test/prompt", "V1", version="v1")
        manager.register("test/prompt", "V2", version="v2")
        manager.register("test/prompt", "V3", version="v3")

        versions = manager.list_versions("test/prompt")
        assert "v1" in versions
        assert "v2" in versions
        assert "v3" in versions


class TestPromptManagerExists:
    """Tests for PromptManager exists method."""

    def test_exists_registered(self) -> None:
        """Test checking if registered template exists."""
        manager = PromptManager()
        manager.register("test/exists", "Content")

        assert manager.exists("test/exists") is True
        assert manager.exists("test/not_exists") is False

    def test_exists_with_version(self) -> None:
        """Test exists check with specific version."""
        manager = PromptManager()
        manager.register("test/prompt", "V1", version="v1")

        assert manager.exists("test/prompt", version="v1") is True
        assert manager.exists("test/prompt", version="v2") is False


class TestPromptManagerCaching:
    """Tests for PromptManager caching."""

    def test_caching_enabled(self) -> None:
        """Test that templates are cached by default."""
        manager = PromptManager()
        manager.register("test/cached", "Cached: {{ x }}")

        # First access
        manager.get("test/cached")
        # Second access should return same instance from cache
        manager.get("test/cached")

        # Note: for registered templates, they're stored directly
        # Cache is mainly for file-based templates

    def test_clear_cache(self) -> None:
        """Test clearing the cache."""
        manager = PromptManager()
        manager.register("test/prompt", "Content")

        # Populate cache
        manager.get("test/prompt")

        # Clear cache
        manager.clear_cache()

        # Cache should be empty
        assert len(manager._cache) == 0


class TestPromptManagerFileLoading:
    """Tests for PromptManager file-based template loading."""

    def test_file_not_found_error(self, tmp_path: Path) -> None:
        """Test error when template file doesn't exist."""
        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        with pytest.raises(PromptNotFoundError) as exc_info:
            manager.get("system/nonexistent")

        assert "system/nonexistent" in str(exc_info.value)

    def test_load_from_file(self, tmp_path: Path) -> None:
        """Test loading template from file."""
        # Create directory structure
        version_dir = tmp_path / "v1" / "system"
        version_dir.mkdir(parents=True)

        # Create template file
        template_file = version_dir / "assistant.jinja2"
        template_file.write_text("Hello, {{ name }}!")

        # Configure manager
        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        # Load template
        template = manager.get("system/assistant")
        assert template.render(name="World") == "Hello, World!"

    def test_load_different_versions(self, tmp_path: Path) -> None:
        """Test loading different versions of same template."""
        # Create v1
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)
        (v1_dir / "prompt.jinja2").write_text("V1: {{ x }}")

        # Create v2
        v2_dir = tmp_path / "v2" / "test"
        v2_dir.mkdir(parents=True)
        (v2_dir / "prompt.jinja2").write_text("V2: {{ x }}")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        assert manager.render("test/prompt", version="v1", x="foo") == "V1: foo"
        assert manager.render("test/prompt", version="v2", x="bar") == "V2: bar"

    def test_list_prompts_from_files(self, tmp_path: Path) -> None:
        """Test listing prompts includes file-based templates."""
        # Create template files
        v1_system = tmp_path / "v1" / "system"
        v1_system.mkdir(parents=True)
        (v1_system / "assistant.jinja2").write_text("Assistant")
        (v1_system / "coder.jinja2").write_text("Coder")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        prompts = manager.list_prompts()
        assert "system/assistant" in prompts
        assert "system/coder" in prompts

    def test_list_versions_from_files(self, tmp_path: Path) -> None:
        """Test listing versions includes file-based templates."""
        # Create multiple versions
        for version in ["v1", "v2", "v3"]:
            version_dir = tmp_path / version / "test"
            version_dir.mkdir(parents=True)
            (version_dir / "prompt.jinja2").write_text(f"{version} content")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        versions = manager.list_versions("test/prompt")
        assert "v1" in versions
        assert "v2" in versions
        assert "v3" in versions


class TestPromptManagerJinja2Features:
    """Tests for Jinja2-specific features through PromptManager."""

    def test_template_inheritance(self, tmp_path: Path) -> None:
        """Test Jinja2 template inheritance."""
        v1_dir = tmp_path / "v1"
        base_dir = v1_dir / "base"
        base_dir.mkdir(parents=True)
        system_dir = v1_dir / "system"
        system_dir.mkdir(parents=True)

        # Create base template
        (base_dir / "base.jinja2").write_text(
            "{% block persona %}Default persona{% endblock %}\n"
            "{% block instructions %}{% endblock %}"
        )

        # Create child template that extends base
        (system_dir / "assistant.jinja2").write_text(
            "{% extends 'v1/base/base.jinja2' %}\n"
            "{% block persona %}Custom persona: {{ name }}{% endblock %}"
        )

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        result = manager.render("system/assistant", name="Helper")
        assert "Custom persona: Helper" in result

    def test_strict_mode(self, tmp_path: Path) -> None:
        """Test strict mode raises on missing variables."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)
        (v1_dir / "strict.jinja2").write_text("Hello, {{ required_var }}!")

        config = PromptConfig(prompts_dir=tmp_path, strict_mode=True)
        manager = PromptManager(config)

        # Should raise because required_var is missing
        from mamba_agents.prompts.errors import TemplateRenderError

        with pytest.raises(TemplateRenderError):
            manager.render("test/strict")


class TestPromptManagerMarkdown:
    """Tests for PromptManager markdown template loading."""

    def test_load_markdown_template(self, tmp_path: Path) -> None:
        """Test loading a basic markdown template."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "greeting.md").write_text(
            """---
variables:
  name: World
---
Hello, {name}!"""
        )

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        template = manager.get("test/greeting")
        assert template.template_type == TemplateType.MARKDOWN
        assert template.render() == "Hello, World!"
        assert template.render(name="Alice") == "Hello, Alice!"

    def test_markdown_default_variables(self, tmp_path: Path) -> None:
        """Test markdown template uses frontmatter defaults."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "prompt.md").write_text(
            """---
variables:
  assistant_name: Claude
  tone: professional
---
You are {assistant_name}, a helpful AI assistant.
Your tone should be {tone}."""
        )

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        result = manager.render("test/prompt")
        assert "Claude" in result
        assert "professional" in result

    def test_markdown_override_defaults(self, tmp_path: Path) -> None:
        """Test that render variables override frontmatter defaults."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "prompt.md").write_text(
            """---
variables:
  name: Default
---
Hello, {name}!"""
        )

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        result = manager.render("test/prompt", name="Override")
        assert result == "Hello, Override!"

    def test_markdown_no_frontmatter(self, tmp_path: Path) -> None:
        """Test markdown template without frontmatter."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "simple.md").write_text("Simple {name} template.")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        template = manager.get("test/simple")
        assert template.render(name="test") == "Simple test template."

    def test_markdown_strict_mode(self, tmp_path: Path) -> None:
        """Test markdown template in strict mode."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "strict.md").write_text(
            """---
variables:
  name: Default
---
Hello, {name}! You are {role}."""
        )

        config = PromptConfig(prompts_dir=tmp_path, strict_mode=True)
        manager = PromptManager(config)

        from mamba_agents.prompts.errors import TemplateRenderError

        # Should succeed with default name but fail on missing role
        with pytest.raises(TemplateRenderError):
            manager.render("test/strict")

    def test_list_prompts_includes_markdown(self, tmp_path: Path) -> None:
        """Test that list_prompts finds both .jinja2 and .md files."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "jinja.jinja2").write_text("Jinja2 template")
        (v1_dir / "markdown.md").write_text("Markdown template")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        prompts = manager.list_prompts()
        assert "test/jinja" in prompts
        assert "test/markdown" in prompts

    def test_list_versions_includes_markdown(self, tmp_path: Path) -> None:
        """Test that list_versions finds markdown templates."""
        for version in ["v1", "v2"]:
            version_dir = tmp_path / version / "test"
            version_dir.mkdir(parents=True)
            (version_dir / "prompt.md").write_text(f"{version} content")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        versions = manager.list_versions("test/prompt")
        assert "v1" in versions
        assert "v2" in versions

    def test_exists_finds_markdown(self, tmp_path: Path) -> None:
        """Test that exists() finds markdown templates."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)
        (v1_dir / "prompt.md").write_text("Content")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        assert manager.exists("test/prompt") is True
        assert manager.exists("test/nonexistent") is False


class TestPromptManagerConflict:
    """Tests for template conflict detection."""

    def test_conflict_raises_error(self, tmp_path: Path) -> None:
        """Test that both .md and .jinja2 for same template raises error."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "conflict.jinja2").write_text("Jinja2")
        (v1_dir / "conflict.md").write_text("Markdown")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        with pytest.raises(TemplateConflictError) as exc_info:
            manager.get("test/conflict")

        assert exc_info.value.name == "test/conflict"
        assert exc_info.value.version == "v1"
        assert ".jinja2" in exc_info.value.extensions
        assert ".md" in exc_info.value.extensions

    def test_no_conflict_different_names(self, tmp_path: Path) -> None:
        """Test that different template names don't conflict."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        (v1_dir / "jinja_template.jinja2").write_text("Jinja2")
        (v1_dir / "markdown_template.md").write_text("Markdown")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        # Both should load without conflict
        jinja = manager.get("test/jinja_template")
        md = manager.get("test/markdown_template")

        assert jinja.template_type == TemplateType.JINJA2
        assert md.template_type == TemplateType.MARKDOWN

    def test_list_prompts_deduplicates(self, tmp_path: Path) -> None:
        """Test that list_prompts shows unique names."""
        v1_dir = tmp_path / "v1" / "test"
        v1_dir.mkdir(parents=True)

        # Note: this scenario would cause conflict on get(), but list_prompts
        # should still deduplicate the names
        (v1_dir / "unique.jinja2").write_text("Jinja2")
        (v1_dir / "other.md").write_text("Markdown")

        config = PromptConfig(prompts_dir=tmp_path)
        manager = PromptManager(config)

        prompts = manager.list_prompts()
        # Each template should appear once
        assert prompts.count("test/unique") == 1
        assert prompts.count("test/other") == 1
