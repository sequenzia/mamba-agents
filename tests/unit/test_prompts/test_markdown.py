"""Tests for markdown prompt parsing and rendering."""

import pytest

from mamba_agents.prompts.errors import MarkdownParseError, TemplateRenderError
from mamba_agents.prompts.markdown import (
    VARIABLE_PATTERN,
    get_markdown_variables,
    parse_markdown_prompt,
    render_markdown_prompt,
    unescape_braces,
)


class TestParseMarkdownPrompt:
    """Tests for parse_markdown_prompt function."""

    def test_no_frontmatter(self) -> None:
        """Test parsing markdown without frontmatter."""
        source = "Hello, {name}!"
        data = parse_markdown_prompt(source, "test")

        assert data.content == "Hello, {name}!"
        assert data.metadata == {}
        assert data.default_variables == {}

    def test_basic_frontmatter(self) -> None:
        """Test parsing markdown with basic frontmatter."""
        source = """---
description: A test prompt
---
Hello, {name}!"""
        data = parse_markdown_prompt(source, "test")

        assert data.content == "Hello, {name}!"
        assert data.metadata == {"description": "A test prompt"}
        assert data.default_variables == {}

    def test_frontmatter_with_variables(self) -> None:
        """Test parsing markdown with default variables."""
        source = """---
variables:
  name: World
  tone: friendly
---
Hello, {name}! Be {tone}."""
        data = parse_markdown_prompt(source, "test")

        assert data.content == "Hello, {name}! Be {tone}."
        assert data.default_variables == {"name": "World", "tone": "friendly"}

    def test_frontmatter_with_metadata_and_variables(self) -> None:
        """Test parsing markdown with both metadata and variables."""
        source = """---
description: Greeting prompt
author: test
variables:
  name: Claude
---
You are {name}."""
        data = parse_markdown_prompt(source, "test")

        assert data.content == "You are {name}."
        assert data.metadata == {"description": "Greeting prompt", "author": "test"}
        assert data.default_variables == {"name": "Claude"}

    def test_empty_frontmatter(self) -> None:
        """Test parsing markdown with empty frontmatter."""
        source = """---
---
Content here."""
        data = parse_markdown_prompt(source, "test")

        assert data.content == "Content here."
        assert data.metadata == {}
        assert data.default_variables == {}

    def test_frontmatter_with_null_variables(self) -> None:
        """Test parsing markdown with null variables section."""
        source = """---
description: Test
variables:
---
Content."""
        data = parse_markdown_prompt(source, "test")

        assert data.content == "Content."
        assert data.default_variables == {}

    def test_multiline_content(self) -> None:
        """Test parsing markdown with multiline content."""
        source = """---
variables:
  name: Assistant
---
You are {name}.

You should:
- Be helpful
- Be accurate
- Be concise"""
        data = parse_markdown_prompt(source, "test")

        assert "You are {name}." in data.content
        assert "- Be helpful" in data.content
        assert "- Be accurate" in data.content

    def test_invalid_yaml_frontmatter(self) -> None:
        """Test that invalid YAML raises MarkdownParseError."""
        source = """---
invalid: [unclosed
---
Content."""

        with pytest.raises(MarkdownParseError) as exc_info:
            parse_markdown_prompt(source, "test")

        assert "Invalid YAML frontmatter" in str(exc_info.value)
        assert exc_info.value.name == "test"

    def test_non_dict_frontmatter(self) -> None:
        """Test that non-dict frontmatter raises error."""
        source = """---
- item1
- item2
---
Content."""

        with pytest.raises(MarkdownParseError) as exc_info:
            parse_markdown_prompt(source, "test")

        assert "must be a YAML mapping" in str(exc_info.value)

    def test_non_dict_variables(self) -> None:
        """Test that non-dict variables raises error."""
        source = """---
variables:
  - name
  - tone
---
Content."""

        with pytest.raises(MarkdownParseError) as exc_info:
            parse_markdown_prompt(source, "test")

        assert "'variables' must be a mapping" in str(exc_info.value)

    def test_content_with_dashes(self) -> None:
        """Test that content with dashes is not confused with frontmatter."""
        source = "Some content --- with dashes --- in the middle."
        data = parse_markdown_prompt(source, "test")

        assert data.content == source

    def test_strips_content_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped from content."""
        source = """---
variables:
  x: 1
---

Content with surrounding whitespace.

"""
        data = parse_markdown_prompt(source, "test")

        assert data.content == "Content with surrounding whitespace."


class TestRenderMarkdownPrompt:
    """Tests for render_markdown_prompt function."""

    def test_basic_substitution(self) -> None:
        """Test basic variable substitution."""
        result = render_markdown_prompt(
            "Hello, {name}!",
            {"name": "World"},
        )
        assert result == "Hello, World!"

    def test_multiple_variables(self) -> None:
        """Test substituting multiple variables."""
        result = render_markdown_prompt(
            "You are {name}, a {role}.",
            {"name": "Claude", "role": "helpful assistant"},
        )
        assert result == "You are Claude, a helpful assistant."

    def test_repeated_variable(self) -> None:
        """Test that same variable can be used multiple times."""
        result = render_markdown_prompt(
            "{name} says hi! Hello, {name}!",
            {"name": "Alice"},
        )
        assert result == "Alice says hi! Hello, Alice!"

    def test_missing_variable_non_strict(self) -> None:
        """Test that missing variables are left unchanged in non-strict mode."""
        result = render_markdown_prompt(
            "Hello, {name}!",
            {},
            strict=False,
        )
        assert result == "Hello, {name}!"

    def test_missing_variable_strict(self) -> None:
        """Test that missing variables raise error in strict mode."""
        with pytest.raises(TemplateRenderError) as exc_info:
            render_markdown_prompt(
                "Hello, {name}!",
                {},
                strict=True,
                name="test",
            )

        assert "Missing required variables" in str(exc_info.value.cause)

    def test_partial_variables_strict(self) -> None:
        """Test strict mode with some but not all variables."""
        with pytest.raises(TemplateRenderError) as exc_info:
            render_markdown_prompt(
                "Hello, {name}! You are {role}.",
                {"name": "Claude"},
                strict=True,
                name="test",
            )

        assert "role" in str(exc_info.value.cause)

    def test_extra_variables_ignored(self) -> None:
        """Test that extra variables are silently ignored."""
        result = render_markdown_prompt(
            "Hello, {name}!",
            {"name": "World", "extra": "ignored"},
        )
        assert result == "Hello, World!"

    def test_escaped_braces_preserved(self) -> None:
        """Test that escaped braces are preserved."""
        result = render_markdown_prompt(
            "Use {{var}} for literal braces, {name}!",
            {"name": "Alice"},
        )
        # Escaped braces should NOT be substituted
        assert result == "Use {{var}} for literal braces, Alice!"

    def test_integer_variable(self) -> None:
        """Test substituting integer values."""
        result = render_markdown_prompt(
            "Count: {count}",
            {"count": 42},
        )
        assert result == "Count: 42"

    def test_none_variable(self) -> None:
        """Test substituting None values."""
        result = render_markdown_prompt(
            "Value: {value}",
            {"value": None},
        )
        assert result == "Value: None"


class TestGetMarkdownVariables:
    """Tests for get_markdown_variables function."""

    def test_no_variables(self) -> None:
        """Test content with no variables."""
        result = get_markdown_variables("No variables here.")
        assert result == set()

    def test_single_variable(self) -> None:
        """Test extracting a single variable."""
        result = get_markdown_variables("Hello, {name}!")
        assert result == {"name"}

    def test_multiple_variables(self) -> None:
        """Test extracting multiple variables."""
        result = get_markdown_variables("Hello, {name}! You are {role}.")
        assert result == {"name", "role"}

    def test_repeated_variable_counted_once(self) -> None:
        """Test that repeated variables are counted once."""
        result = get_markdown_variables("{name} says {name}.")
        assert result == {"name"}

    def test_escaped_braces_not_extracted(self) -> None:
        """Test that escaped braces are not treated as variables."""
        result = get_markdown_variables("Use {{literal}} for escaping, {real}.")
        assert result == {"real"}
        assert "literal" not in result

    def test_underscores_in_names(self) -> None:
        """Test variables with underscores."""
        result = get_markdown_variables("The {assistant_name} is {role_type}.")
        assert result == {"assistant_name", "role_type"}

    def test_numbers_in_names(self) -> None:
        """Test variables with numbers."""
        result = get_markdown_variables("Item {item1} and {value2}.")
        assert result == {"item1", "value2"}

    def test_invalid_variable_names_ignored(self) -> None:
        """Test that invalid variable names are not extracted."""
        # Numbers at start are invalid
        result = get_markdown_variables("Invalid: {1invalid} but {valid} is ok.")
        assert result == {"valid"}


class TestUnescapeBraces:
    """Tests for unescape_braces function."""

    def test_double_open_brace(self) -> None:
        """Test unescaping double open braces."""
        result = unescape_braces("{{var}}")
        assert result == "{var}"

    def test_double_close_brace(self) -> None:
        """Test unescaping double close braces."""
        result = unescape_braces("value}}")
        assert result == "value}"

    def test_both_braces(self) -> None:
        """Test unescaping both types of braces."""
        result = unescape_braces("Use {{name}} for literal.")
        assert result == "Use {name} for literal."

    def test_no_escaped_braces(self) -> None:
        """Test content without escaped braces."""
        result = unescape_braces("No escaping here.")
        assert result == "No escaping here."

    def test_mixed_content(self) -> None:
        """Test mixed escaped and normal content."""
        result = unescape_braces("Hello World, {{literal}} and more.")
        assert result == "Hello World, {literal} and more."


class TestVariablePattern:
    """Tests for the VARIABLE_PATTERN regex."""

    def test_basic_match(self) -> None:
        """Test basic variable matching."""
        match = VARIABLE_PATTERN.search("{name}")
        assert match is not None
        assert match.group(1) == "name"

    def test_no_match_escaped(self) -> None:
        """Test that escaped braces don't match."""
        match = VARIABLE_PATTERN.search("{{escaped}}")
        assert match is None

    def test_no_match_empty(self) -> None:
        """Test that empty braces don't match."""
        match = VARIABLE_PATTERN.search("{}")
        assert match is None

    def test_no_match_number_start(self) -> None:
        """Test that variables starting with numbers don't match."""
        match = VARIABLE_PATTERN.search("{123}")
        assert match is None

    def test_match_underscore_start(self) -> None:
        """Test that variables starting with underscore match."""
        match = VARIABLE_PATTERN.search("{_private}")
        assert match is not None
        assert match.group(1) == "_private"

    def test_findall_multiple(self) -> None:
        """Test finding all variables in a string."""
        matches = VARIABLE_PATTERN.findall("Hello {first} and {second}!")
        assert matches == ["first", "second"]
