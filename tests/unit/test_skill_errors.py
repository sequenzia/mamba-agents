"""Tests for skill error hierarchy."""

from __future__ import annotations

import pickle
from pathlib import Path

from mamba_agents.skills.errors import (
    SkillConflictError,
    SkillError,
    SkillLoadError,
    SkillNotFoundError,
    SkillParseError,
    SkillValidationError,
)


class TestSkillError:
    """Tests for base SkillError."""

    def test_is_exception(self) -> None:
        """Test SkillError is an Exception."""
        error = SkillError("Test error")
        assert isinstance(error, Exception)

    def test_message(self) -> None:
        """Test error message stored and returned by str()."""
        error = SkillError("Something went wrong")
        assert error.message == "Something went wrong"
        assert str(error) == "Something went wrong"

    def test_repr(self) -> None:
        """Test repr produces useful debugging info."""
        error = SkillError("Something went wrong")
        assert repr(error) == "SkillError('Something went wrong')"

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SkillError("pickle test")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.message == error.message


class TestSkillNotFoundError:
    """Tests for SkillNotFoundError."""

    def test_basic_error(self) -> None:
        """Test error with name and path."""
        error = SkillNotFoundError("web-search", "/project/skills/web-search")

        assert error.name == "web-search"
        assert error.path == Path("/project/skills/web-search")
        assert "web-search" in str(error)
        assert "/project/skills/web-search" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from SkillError and Exception."""
        error = SkillNotFoundError("test", "/path")
        assert isinstance(error, SkillError)
        assert isinstance(error, Exception)

    def test_repr(self) -> None:
        """Test repr shows name and path."""
        error = SkillNotFoundError("web-search", "/project/skills/web-search")
        r = repr(error)
        assert "SkillNotFoundError" in r
        assert "web-search" in r
        assert "/project/skills/web-search" in r

    def test_path_coerced_to_pathlib(self) -> None:
        """Test string path is stored as Path object."""
        error = SkillNotFoundError("test", "/some/path")
        assert isinstance(error.path, Path)

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SkillNotFoundError("web-search", "/project/skills/web-search")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == "web-search"
        assert restored.path == Path("/project/skills/web-search")


class TestSkillParseError:
    """Tests for SkillParseError."""

    def test_basic_error(self) -> None:
        """Test error with name, path, and detail."""
        error = SkillParseError(
            "web-search", "/skills/web-search/SKILL.md", "Invalid YAML on line 3"
        )

        assert error.name == "web-search"
        assert error.path == Path("/skills/web-search/SKILL.md")
        assert error.detail == "Invalid YAML on line 3"
        assert "web-search" in str(error)
        assert "Invalid YAML on line 3" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from SkillError and Exception."""
        error = SkillParseError("test", "/path", "bad yaml")
        assert isinstance(error, SkillError)
        assert isinstance(error, Exception)

    def test_repr(self) -> None:
        """Test repr shows name, path, and detail."""
        error = SkillParseError("test", "/path/SKILL.md", "bad yaml")
        r = repr(error)
        assert "SkillParseError" in r
        assert "test" in r
        assert "/path/SKILL.md" in r
        assert "bad yaml" in r

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SkillParseError("web-search", "/skills/SKILL.md", "bad yaml")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == "web-search"
        assert restored.detail == "bad yaml"


class TestSkillValidationError:
    """Tests for SkillValidationError."""

    def test_single_error(self) -> None:
        """Test with a single validation error."""
        error = SkillValidationError("web-search", ["name must be lowercase"])

        assert error.name == "web-search"
        assert error.errors == ["name must be lowercase"]
        assert "web-search" in str(error)
        assert "name must be lowercase" in str(error)

    def test_multiple_errors(self) -> None:
        """Test with multiple validation errors."""
        errors = ["name is required", "description too long", "invalid license"]
        error = SkillValidationError("broken-skill", errors)

        assert error.errors == errors
        message = str(error)
        for e in errors:
            assert e in message

    def test_with_path(self) -> None:
        """Test with optional path."""
        error = SkillValidationError(
            "web-search",
            ["name mismatch"],
            path="/project/skills/web-search/SKILL.md",
        )

        assert error.path == Path("/project/skills/web-search/SKILL.md")
        assert "/project/skills/web-search/SKILL.md" in str(error)

    def test_without_path(self) -> None:
        """Test without path (programmatic registration)."""
        error = SkillValidationError("web-search", ["invalid name"])
        assert error.path is None

    def test_inheritance(self) -> None:
        """Test error inherits from SkillError and Exception."""
        error = SkillValidationError("test", ["error"])
        assert isinstance(error, SkillError)
        assert isinstance(error, Exception)

    def test_repr(self) -> None:
        """Test repr shows name, errors, and path."""
        error = SkillValidationError("test", ["err1", "err2"], path="/path")
        r = repr(error)
        assert "SkillValidationError" in r
        assert "test" in r
        assert "err1" in r
        assert "err2" in r

    def test_errors_list_is_copy(self) -> None:
        """Test errors list is copied to prevent mutation."""
        original = ["error1"]
        error = SkillValidationError("test", original)
        original.append("error2")
        assert error.errors == ["error1"]

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SkillValidationError("test", ["err1", "err2"], path="/path")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == "test"
        assert restored.errors == ["err1", "err2"]
        assert restored.path == Path("/path")


class TestSkillLoadError:
    """Tests for SkillLoadError."""

    def test_basic_error(self) -> None:
        """Test error with name and path."""
        error = SkillLoadError("web-search", "/skills/web-search/SKILL.md")

        assert error.name == "web-search"
        assert error.path == Path("/skills/web-search/SKILL.md")
        assert error.cause is None
        assert "web-search" in str(error)

    def test_with_cause(self) -> None:
        """Test error with underlying cause."""
        cause = PermissionError("Permission denied")
        error = SkillLoadError("web-search", "/skills/web-search/SKILL.md", cause=cause)

        assert error.cause is cause
        assert "Permission denied" in str(error)

    def test_inheritance(self) -> None:
        """Test error inherits from SkillError and Exception."""
        error = SkillLoadError("test", "/path")
        assert isinstance(error, SkillError)
        assert isinstance(error, Exception)

    def test_repr(self) -> None:
        """Test repr shows name, path, and cause."""
        cause = OSError("disk full")
        error = SkillLoadError("test", "/path", cause=cause)
        r = repr(error)
        assert "SkillLoadError" in r
        assert "test" in r
        assert "/path" in r
        assert "disk full" in r

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SkillLoadError("web-search", "/skills/SKILL.md")
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == "web-search"

    def test_picklable_with_cause(self) -> None:
        """Test error with cause can be pickled."""
        cause = PermissionError("no access")
        error = SkillLoadError("web-search", "/skills/SKILL.md", cause=cause)
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert isinstance(restored.cause, PermissionError)


class TestSkillConflictError:
    """Tests for SkillConflictError."""

    def test_basic_error(self) -> None:
        """Test error with name and paths."""
        paths = ["/project/skills/web-search", "/project/skills2/web-search"]
        error = SkillConflictError("web-search", paths)

        assert error.name == "web-search"
        assert len(error.paths) == 2
        message = str(error)
        assert "web-search" in message
        assert "/project/skills/web-search" in message
        assert "/project/skills2/web-search" in message

    def test_inheritance(self) -> None:
        """Test error inherits from SkillError and Exception."""
        error = SkillConflictError("test", ["/a", "/b"])
        assert isinstance(error, SkillError)
        assert isinstance(error, Exception)

    def test_paths_coerced_to_pathlib(self) -> None:
        """Test string paths are stored as Path objects."""
        error = SkillConflictError("test", ["/a", "/b"])
        for p in error.paths:
            assert isinstance(p, Path)

    def test_repr(self) -> None:
        """Test repr shows name and paths."""
        error = SkillConflictError("test", ["/a", "/b"])
        r = repr(error)
        assert "SkillConflictError" in r
        assert "test" in r
        assert "/a" in r
        assert "/b" in r

    def test_picklable(self) -> None:
        """Test error can be pickled and unpickled."""
        error = SkillConflictError("web-search", ["/a", "/b"])
        restored = pickle.loads(pickle.dumps(error))
        assert str(restored) == str(error)
        assert restored.name == "web-search"
        assert len(restored.paths) == 2


class TestInheritanceChain:
    """Tests verifying the complete inheritance chain."""

    def test_all_errors_are_skill_errors(self) -> None:
        """Test all error classes inherit from SkillError."""
        errors = [
            SkillNotFoundError("n", "/p"),
            SkillParseError("n", "/p", "d"),
            SkillValidationError("n", ["e"]),
            SkillLoadError("n", "/p"),
            SkillConflictError("n", ["/a"]),
        ]
        for error in errors:
            assert isinstance(error, SkillError), f"{type(error).__name__} is not a SkillError"

    def test_all_errors_are_exceptions(self) -> None:
        """Test all error classes inherit from Exception."""
        errors = [
            SkillError("base"),
            SkillNotFoundError("n", "/p"),
            SkillParseError("n", "/p", "d"),
            SkillValidationError("n", ["e"]),
            SkillLoadError("n", "/p"),
            SkillConflictError("n", ["/a"]),
        ]
        for error in errors:
            assert isinstance(error, Exception), f"{type(error).__name__} is not an Exception"

    def test_catch_all_with_base_class(self) -> None:
        """Test that catching SkillError catches all subclasses."""
        subclass_errors = [
            SkillNotFoundError("n", "/p"),
            SkillParseError("n", "/p", "d"),
            SkillValidationError("n", ["e"]),
            SkillLoadError("n", "/p"),
            SkillConflictError("n", ["/a"]),
        ]
        for error in subclass_errors:
            try:
                raise error
            except SkillError:
                pass  # Successfully caught
            except Exception as exc:
                raise AssertionError(
                    f"{type(error).__name__} was not caught by 'except SkillError'"
                ) from exc
