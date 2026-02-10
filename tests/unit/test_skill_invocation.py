"""Tests for skill invocation, argument substitution, and activation lifecycle."""

from __future__ import annotations

from pathlib import Path

import pytest

from mamba_agents.skills.config import Skill, SkillInfo, SkillScope
from mamba_agents.skills.errors import SkillInvocationError
from mamba_agents.skills.invocation import (
    InvocationSource,
    activate,
    check_invocation_permission,
    deactivate,
    parse_arguments,
    substitute_arguments,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_info(
    name: str = "test-skill",
    description: str = "A test skill",
    path: Path | None = None,
    disable_model_invocation: bool = False,
    user_invocable: bool = True,
    allowed_tools: list[str] | None = None,
) -> SkillInfo:
    """Create a minimal SkillInfo for testing."""
    return SkillInfo(
        name=name,
        description=description,
        path=path or Path("/skills/test-skill"),
        scope=SkillScope.PROJECT,
        disable_model_invocation=disable_model_invocation,
        user_invocable=user_invocable,
        allowed_tools=allowed_tools,
    )


def _make_skill(
    name: str = "test-skill",
    body: str | None = None,
    disable_model_invocation: bool = False,
    user_invocable: bool = True,
    allowed_tools: list[str] | None = None,
    path: Path | None = None,
) -> Skill:
    """Create a minimal Skill for testing."""
    return Skill(
        info=_make_info(
            name=name,
            path=path,
            disable_model_invocation=disable_model_invocation,
            user_invocable=user_invocable,
            allowed_tools=allowed_tools,
        ),
        body=body,
    )


# ---------------------------------------------------------------------------
# InvocationSource enum
# ---------------------------------------------------------------------------


class TestInvocationSource:
    """Tests for the InvocationSource enum."""

    def test_model_value(self) -> None:
        assert InvocationSource.MODEL.value == "model"

    def test_user_value(self) -> None:
        assert InvocationSource.USER.value == "user"

    def test_code_value(self) -> None:
        assert InvocationSource.CODE.value == "code"

    def test_is_str_enum(self) -> None:
        assert isinstance(InvocationSource.MODEL, str)

    def test_from_string(self) -> None:
        assert InvocationSource("model") == InvocationSource.MODEL
        assert InvocationSource("user") == InvocationSource.USER
        assert InvocationSource("code") == InvocationSource.CODE


# ---------------------------------------------------------------------------
# parse_arguments
# ---------------------------------------------------------------------------


class TestParseArguments:
    """Tests for argument parsing with whitespace, quotes, and special chars."""

    def test_empty_string(self) -> None:
        assert parse_arguments("") == []

    def test_whitespace_only(self) -> None:
        assert parse_arguments("   ") == []

    def test_single_arg(self) -> None:
        assert parse_arguments("hello") == ["hello"]

    def test_multiple_args_whitespace(self) -> None:
        assert parse_arguments("hello world foo") == ["hello", "world", "foo"]

    def test_double_quoted_string(self) -> None:
        assert parse_arguments('"hello world" foo') == ["hello world", "foo"]

    def test_single_quoted_string(self) -> None:
        assert parse_arguments("'hello world' foo") == ["hello world", "foo"]

    def test_mixed_quotes(self) -> None:
        result = parse_arguments("""'single' "double" plain""")
        assert result == ["single", "double", "plain"]

    def test_special_chars_in_quotes(self) -> None:
        result = parse_arguments('"hello!@#$%" normal')
        assert result == ["hello!@#$%", "normal"]

    def test_extra_whitespace_between_args(self) -> None:
        assert parse_arguments("hello    world") == ["hello", "world"]

    def test_leading_trailing_whitespace(self) -> None:
        assert parse_arguments("  hello world  ") == ["hello", "world"]

    def test_tab_separated(self) -> None:
        assert parse_arguments("hello\tworld") == ["hello", "world"]

    def test_path_argument(self) -> None:
        result = parse_arguments("/path/to/file.txt")
        assert result == ["/path/to/file.txt"]

    def test_quoted_path_with_spaces(self) -> None:
        result = parse_arguments('"/path/to/my file.txt" arg2')
        assert result == ["/path/to/my file.txt", "arg2"]

    def test_escaped_quote_in_double_quotes(self) -> None:
        result = parse_arguments(r'"hello \"world\"" foo')
        assert result == ['hello "world"', "foo"]

    def test_empty_quoted_string(self) -> None:
        result = parse_arguments('"" foo')
        assert result == ["", "foo"]


# ---------------------------------------------------------------------------
# substitute_arguments — $ARGUMENTS full replacement
# ---------------------------------------------------------------------------


class TestSubstituteArgumentsFull:
    """Tests for $ARGUMENTS full argument string replacement."""

    def test_arguments_replaced_with_full_string(self) -> None:
        content = "Process: $ARGUMENTS"
        result = substitute_arguments(content, "hello world")
        assert result == "Process: hello world"

    def test_arguments_multiple_occurrences(self) -> None:
        content = "First: $ARGUMENTS\nSecond: $ARGUMENTS"
        result = substitute_arguments(content, "test data")
        assert result == "First: test data\nSecond: test data"

    def test_arguments_empty_string_when_no_args(self) -> None:
        content = "Process: $ARGUMENTS"
        result = substitute_arguments(content, "")
        assert result == "Process: "

    def test_arguments_whitespace_only_when_no_args(self) -> None:
        content = "Process: $ARGUMENTS"
        result = substitute_arguments(content, "   ")
        assert result == "Process:    "

    def test_arguments_preserves_surrounding_text(self) -> None:
        content = "Before $ARGUMENTS after"
        result = substitute_arguments(content, "value")
        assert result == "Before value after"

    def test_arguments_in_multiline_content(self) -> None:
        content = "# Header\n\nUse $ARGUMENTS here.\n\nDone."
        result = substitute_arguments(content, "my-file.txt")
        assert result == "# Header\n\nUse my-file.txt here.\n\nDone."


# ---------------------------------------------------------------------------
# substitute_arguments — $N positional replacement
# ---------------------------------------------------------------------------


class TestSubstituteArgumentsPositional:
    """Tests for $N positional argument replacement (0-indexed)."""

    def test_dollar_zero(self) -> None:
        content = "File: $0"
        result = substitute_arguments(content, "file.txt")
        assert result == "File: file.txt"

    def test_dollar_zero_and_one(self) -> None:
        content = "Source: $0 Dest: $1"
        result = substitute_arguments(content, "src.txt dest.txt")
        assert result == "Source: src.txt Dest: dest.txt"

    def test_missing_positional_becomes_empty(self) -> None:
        content = "A: $0 B: $1 C: $2"
        result = substitute_arguments(content, "only-one")
        assert result == "A: only-one B:  C: "

    def test_positional_with_quoted_args(self) -> None:
        content = "Name: $0 Path: $1"
        result = substitute_arguments(content, '"hello world" /path/to/file')
        assert result == "Name: hello world Path: /path/to/file"

    def test_dollar_n_at_end_of_line(self) -> None:
        content = "Value: $0\nNext line"
        result = substitute_arguments(content, "test")
        assert result == "Value: test\nNext line"

    def test_dollar_n_at_end_of_content(self) -> None:
        content = "Value: $0"
        result = substitute_arguments(content, "test")
        assert result == "Value: test"

    def test_higher_positional_index(self) -> None:
        content = "Third: $2"
        result = substitute_arguments(content, "a b c d")
        assert result == "Third: c"


# ---------------------------------------------------------------------------
# substitute_arguments — $ARGUMENTS[N] indexed replacement
# ---------------------------------------------------------------------------


class TestSubstituteArgumentsIndexed:
    """Tests for $ARGUMENTS[N] indexed syntax."""

    def test_arguments_index_zero(self) -> None:
        content = "File: $ARGUMENTS[0]"
        result = substitute_arguments(content, "file.txt")
        assert result == "File: file.txt"

    def test_arguments_index_multiple(self) -> None:
        content = "Source: $ARGUMENTS[0] Dest: $ARGUMENTS[1]"
        result = substitute_arguments(content, "src.txt dest.txt")
        assert result == "Source: src.txt Dest: dest.txt"

    def test_arguments_index_missing(self) -> None:
        content = "A: $ARGUMENTS[0] B: $ARGUMENTS[1]"
        result = substitute_arguments(content, "only-one")
        assert result == "A: only-one B: "

    def test_arguments_index_with_full_arguments(self) -> None:
        """Both $ARGUMENTS and $ARGUMENTS[N] in same content."""
        content = "All: $ARGUMENTS\nFirst: $ARGUMENTS[0]"
        result = substitute_arguments(content, "hello world")
        assert result == "All: hello world\nFirst: hello"

    def test_arguments_index_high_number(self) -> None:
        content = "Tenth: $ARGUMENTS[9]"
        result = substitute_arguments(content, "a b c d e f g h i j")
        assert result == "Tenth: j"


# ---------------------------------------------------------------------------
# substitute_arguments — no placeholder → append
# ---------------------------------------------------------------------------


class TestSubstituteArgumentsAppend:
    """Tests for append behavior when no placeholders are present."""

    def test_no_placeholder_appends_arguments(self) -> None:
        content = "# My Skill\n\nDo something."
        result = substitute_arguments(content, "hello world")
        assert "ARGUMENTS: hello world" in result

    def test_no_placeholder_empty_args_no_append(self) -> None:
        content = "# My Skill\n\nDo something."
        result = substitute_arguments(content, "")
        assert "ARGUMENTS:" not in result
        assert result == content

    def test_no_placeholder_whitespace_args_no_append(self) -> None:
        content = "# My Skill\n\nDo something."
        result = substitute_arguments(content, "   ")
        assert "ARGUMENTS:" not in result

    def test_append_preserves_content(self) -> None:
        content = "# My Skill\n\nDo something."
        result = substitute_arguments(content, "value")
        assert result.startswith("# My Skill\n\nDo something.")
        assert result.endswith("ARGUMENTS: value\n")

    def test_append_format(self) -> None:
        content = "Content here"
        result = substitute_arguments(content, "arg1 arg2")
        # Should have double newline before ARGUMENTS:
        assert "\n\nARGUMENTS: arg1 arg2\n" in result


# ---------------------------------------------------------------------------
# substitute_arguments — mixed and edge cases
# ---------------------------------------------------------------------------


class TestSubstituteArgumentsMixed:
    """Tests for mixed placeholder usage and edge cases."""

    def test_all_placeholder_types(self) -> None:
        content = "Full: $ARGUMENTS\nFirst: $ARGUMENTS[0]\nSecond: $1"
        result = substitute_arguments(content, "hello world")
        assert "Full: hello world" in result
        assert "First: hello" in result
        assert "Second: world" in result

    def test_more_args_than_placeholders(self) -> None:
        """Extra args are available via $ARGUMENTS even when $0 is used."""
        content = "First: $0\nAll: $ARGUMENTS"
        result = substitute_arguments(content, "a b c")
        assert "First: a" in result
        assert "All: a b c" in result

    def test_dollar_sign_not_followed_by_digit_preserved(self) -> None:
        content = "Price: $100 and $VARIABLE"
        result = substitute_arguments(content, "test")
        # $100 has digits after $ but no word boundary match for single digit
        # $VARIABLE should not be affected
        assert "$VARIABLE" in result

    def test_empty_body_with_arguments(self) -> None:
        result = substitute_arguments("", "hello")
        assert "ARGUMENTS: hello" in result


# ---------------------------------------------------------------------------
# check_invocation_permission
# ---------------------------------------------------------------------------


class TestCheckInvocationPermission:
    """Tests for invocation permission checks."""

    def test_default_allows_model(self) -> None:
        info = _make_info()
        assert check_invocation_permission(info, InvocationSource.MODEL) is True

    def test_default_allows_user(self) -> None:
        info = _make_info()
        assert check_invocation_permission(info, InvocationSource.USER) is True

    def test_default_allows_code(self) -> None:
        info = _make_info()
        assert check_invocation_permission(info, InvocationSource.CODE) is True

    def test_disable_model_invocation_blocks_model(self) -> None:
        info = _make_info(disable_model_invocation=True)
        assert check_invocation_permission(info, InvocationSource.MODEL) is False

    def test_disable_model_invocation_allows_user(self) -> None:
        info = _make_info(disable_model_invocation=True)
        assert check_invocation_permission(info, InvocationSource.USER) is True

    def test_disable_model_invocation_allows_code(self) -> None:
        info = _make_info(disable_model_invocation=True)
        assert check_invocation_permission(info, InvocationSource.CODE) is True

    def test_user_invocable_false_blocks_user(self) -> None:
        info = _make_info(user_invocable=False)
        assert check_invocation_permission(info, InvocationSource.USER) is False

    def test_user_invocable_false_allows_model(self) -> None:
        info = _make_info(user_invocable=False)
        assert check_invocation_permission(info, InvocationSource.MODEL) is True

    def test_user_invocable_false_allows_code(self) -> None:
        info = _make_info(user_invocable=False)
        assert check_invocation_permission(info, InvocationSource.CODE) is True

    def test_both_restrictions_blocks_model_and_user(self) -> None:
        info = _make_info(disable_model_invocation=True, user_invocable=False)
        assert check_invocation_permission(info, InvocationSource.MODEL) is False
        assert check_invocation_permission(info, InvocationSource.USER) is False

    def test_both_restrictions_allows_code(self) -> None:
        info = _make_info(disable_model_invocation=True, user_invocable=False)
        assert check_invocation_permission(info, InvocationSource.CODE) is True


# ---------------------------------------------------------------------------
# activate — lifecycle
# ---------------------------------------------------------------------------


class TestActivate:
    """Tests for the full activation lifecycle."""

    def test_basic_activation_returns_body(self) -> None:
        skill = _make_skill(body="# My Skill\n\nDo something.")
        result = activate(skill)
        assert "# My Skill" in result
        assert "Do something." in result

    def test_activation_with_arguments(self) -> None:
        skill = _make_skill(body="Process: $ARGUMENTS")
        result = activate(skill, "hello world")
        assert result == "Process: hello world"

    def test_activation_marks_skill_active(self) -> None:
        skill = _make_skill(body="content")
        assert skill.is_active is False
        activate(skill)
        assert skill.is_active is True

    def test_activation_with_positional_args(self) -> None:
        skill = _make_skill(body="Source: $0 Dest: $1")
        result = activate(skill, "src.txt dest.txt")
        assert result == "Source: src.txt Dest: dest.txt"

    def test_activation_no_body_returns_empty(self) -> None:
        skill = _make_skill(body=None, path=Path("/nonexistent"))
        result = activate(skill)
        assert result == ""

    def test_activation_permission_denied_model(self) -> None:
        skill = _make_skill(
            body="content",
            disable_model_invocation=True,
        )
        with pytest.raises(SkillInvocationError, match="model invocation is disabled"):
            activate(skill, source=InvocationSource.MODEL)

    def test_activation_permission_denied_user(self) -> None:
        skill = _make_skill(
            body="content",
            user_invocable=False,
        )
        with pytest.raises(SkillInvocationError, match="user invocation is disabled"):
            activate(skill, source=InvocationSource.USER)

    def test_activation_code_always_allowed(self) -> None:
        skill = _make_skill(
            body="content",
            disable_model_invocation=True,
            user_invocable=False,
        )
        result = activate(skill, source=InvocationSource.CODE)
        assert result == "content"

    def test_activation_lazy_loads_body(self, tmp_path: Path) -> None:
        """Activation loads the body from disk if not already loaded."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: test-skill\ndescription: A skill\n---\n\n# Loaded Body\n\nContent here."
        )

        skill = _make_skill(body=None, path=skill_dir)
        result = activate(skill, "my-arg")
        assert "# Loaded Body" in result
        assert "Content here." in result

    def test_activation_substitutes_on_lazy_loaded_body(self, tmp_path: Path) -> None:
        """Arguments are substituted on the lazily loaded body."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: test-skill\ndescription: A skill\n---\n\nProcess: $ARGUMENTS"
        )

        skill = _make_skill(body=None, path=skill_dir)
        result = activate(skill, "hello world")
        assert "Process: hello world" in result

    def test_activation_no_args_no_append_with_placeholder(self) -> None:
        skill = _make_skill(body="Use: $ARGUMENTS here")
        result = activate(skill, "")
        assert result == "Use:  here"
        assert "ARGUMENTS:" not in result

    def test_activation_no_placeholder_appends(self) -> None:
        skill = _make_skill(body="# Skill\n\nDo work.")
        result = activate(skill, "some-arg")
        assert "ARGUMENTS: some-arg" in result


# ---------------------------------------------------------------------------
# deactivate
# ---------------------------------------------------------------------------


class TestDeactivate:
    """Tests for skill deactivation and state restoration."""

    def test_deactivate_marks_inactive(self) -> None:
        skill = _make_skill(body="content")
        skill.is_active = True
        deactivate(skill)
        assert skill.is_active is False

    def test_deactivate_clears_tools(self) -> None:
        skill = _make_skill(body="content")
        skill.is_active = True
        skill._tools = [lambda: None, lambda: None]
        deactivate(skill)
        assert skill._tools == []

    def test_deactivate_idempotent(self) -> None:
        skill = _make_skill(body="content")
        skill.is_active = False
        deactivate(skill)
        assert skill.is_active is False

    def test_activate_then_deactivate(self) -> None:
        """Full lifecycle: activate, verify active, deactivate, verify inactive."""
        skill = _make_skill(body="content")
        activate(skill)
        assert skill.is_active is True
        deactivate(skill)
        assert skill.is_active is False


# ---------------------------------------------------------------------------
# SkillInvocationError
# ---------------------------------------------------------------------------


class TestSkillInvocationError:
    """Tests for the SkillInvocationError exception."""

    def test_error_message(self) -> None:
        err = SkillInvocationError("my-skill", "model", "model invocation is disabled")
        assert "my-skill" in str(err)
        assert "model" in str(err)
        assert "model invocation is disabled" in str(err)

    def test_error_attributes(self) -> None:
        err = SkillInvocationError("my-skill", "user", "reason here")
        assert err.name == "my-skill"
        assert err.source == "user"
        assert err.reason == "reason here"

    def test_error_repr(self) -> None:
        err = SkillInvocationError("my-skill", "model", "reason")
        r = repr(err)
        assert "SkillInvocationError" in r
        assert "my-skill" in r
        assert "model" in r
        assert "reason" in r

    def test_error_inherits_skill_error(self) -> None:
        from mamba_agents.skills.errors import SkillError

        err = SkillInvocationError("my-skill", "model", "denied")
        assert isinstance(err, SkillError)

    def test_error_pickle_support(self) -> None:
        import pickle

        err = SkillInvocationError("my-skill", "model", "denied")
        restored = pickle.loads(pickle.dumps(err))
        assert restored.name == "my-skill"
        assert restored.source == "model"
        assert restored.reason == "denied"
