"""Tests for PromptTemplate class."""

import pytest

from mamba_agents.prompts.errors import TemplateRenderError
from mamba_agents.prompts.template import PromptTemplate


class TestPromptTemplate:
    """Tests for PromptTemplate."""

    def test_basic_render(self) -> None:
        """Test basic template rendering."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name }}!",
        )

        result = template.render(name="World")
        assert result == "Hello, World!"

    def test_render_without_variables(self) -> None:
        """Test rendering template without required variables."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Static content",
        )

        result = template.render()
        assert result == "Static content"

    def test_render_with_default_filter(self) -> None:
        """Test rendering with Jinja2 default filter."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name | default('Anonymous') }}!",
        )

        # With variable
        assert template.render(name="Alice") == "Hello, Alice!"

        # Without variable (uses default)
        assert template.render() == "Hello, Anonymous!"

    def test_with_variables(self) -> None:
        """Test creating template with default variables."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name }}! You are {{ role }}.",
        )

        # Create partial with name
        partial = template.with_variables(name="Claude")

        # Render with role only
        result = partial.render(role="helpful")
        assert result == "Hello, Claude! You are helpful."

    def test_with_variables_override(self) -> None:
        """Test that render variables override defaults."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name }}!",
        )

        partial = template.with_variables(name="Default")

        # Override at render time
        result = partial.render(name="Override")
        assert result == "Hello, Override!"

    def test_get_variables(self) -> None:
        """Test extracting variable names from template."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name }}! You are {{ role }}. {{ count }} times.",
        )

        variables = template.get_variables()
        assert variables == {"name", "role", "count"}

    def test_get_variables_empty(self) -> None:
        """Test extracting variables from static template."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="No variables here",
        )

        variables = template.get_variables()
        assert variables == set()

    def test_str_method(self) -> None:
        """Test __str__ method renders template."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Static content",
        )

        assert str(template) == "Static content"

    def test_str_with_defaults(self) -> None:
        """Test __str__ uses default variables."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name | default('World') }}!",
        )

        partial = template.with_variables(name="Claude")
        assert str(partial) == "Hello, Claude!"

    def test_complex_template(self) -> None:
        """Test more complex Jinja2 features."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="""{% for item in items %}
- {{ item }}
{% endfor %}""",
        )

        result = template.render(items=["one", "two", "three"])
        assert "- one" in result
        assert "- two" in result
        assert "- three" in result

    def test_conditional_template(self) -> None:
        """Test conditional logic in templates."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="{% if verbose %}Verbose mode{% else %}Brief{% endif %}",
        )

        assert template.render(verbose=True) == "Verbose mode"
        assert template.render(verbose=False) == "Brief"

    def test_template_caching(self) -> None:
        """Test that compiled template is cached."""
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name }}!",
        )

        # First render compiles
        assert template._compiled is None
        template.render(name="World")
        assert template._compiled is not None

        # Second render uses cached
        compiled = template._compiled
        template.render(name="Again")
        assert template._compiled is compiled

    def test_render_error_missing_variable_strict(self) -> None:
        """Test that missing variables raise errors with strict mode."""
        from jinja2 import StrictUndefined, Template

        # Create a template with strict undefined
        jinja_template = Template(
            "Hello, {{ name }}!",
            undefined=StrictUndefined,
        )
        template = PromptTemplate(
            name="test",
            version="v1",
            source="Hello, {{ name }}!",
            _compiled=jinja_template,
        )

        with pytest.raises(TemplateRenderError):
            template.render()  # Missing required variable
