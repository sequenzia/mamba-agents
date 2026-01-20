"""Tests for filesystem tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from mamba_agents.tools.filesystem import (
    FilesystemSecurity,
    append_file,
    copy_file,
    delete_file,
    file_info,
    list_directory,
    move_file,
    read_file,
    write_file,
)


class TestFilesystemSecurity:
    """Tests for FilesystemSecurity."""

    def test_validate_path_in_sandbox(self, tmp_sandbox: Path) -> None:
        """Test that paths within sandbox are validated."""
        security = FilesystemSecurity(base_directory=tmp_sandbox)
        result = security.validate_path(str(tmp_sandbox / "file1.txt"))

        assert result == tmp_sandbox / "file1.txt"

    def test_validate_path_outside_sandbox_raises(self, tmp_sandbox: Path) -> None:
        """Test that paths outside sandbox raise PermissionError."""
        security = FilesystemSecurity(base_directory=tmp_sandbox)

        with pytest.raises(PermissionError, match="Path outside allowed directory"):
            security.validate_path("/etc/passwd")

    def test_validate_path_traversal_attack(self, tmp_sandbox: Path) -> None:
        """Test that path traversal attacks are blocked."""
        security = FilesystemSecurity(base_directory=tmp_sandbox)

        with pytest.raises(PermissionError, match="Path outside allowed directory"):
            security.validate_path(str(tmp_sandbox / ".." / ".." / "etc" / "passwd"))

    def test_validate_path_no_sandbox(self) -> None:
        """Test that without sandbox, all paths are allowed."""
        security = FilesystemSecurity()
        result = security.validate_path("/some/path")

        assert result == Path("/some/path")

    def test_allowed_extensions(self, tmp_sandbox: Path) -> None:
        """Test that only allowed extensions pass."""
        security = FilesystemSecurity(
            base_directory=tmp_sandbox,
            allowed_extensions={".txt"},
        )

        # txt should be allowed
        result = security.validate_path(str(tmp_sandbox / "file1.txt"))
        assert result == tmp_sandbox / "file1.txt"

        # py should be denied
        with pytest.raises(PermissionError, match=r"Extension \.py not allowed"):
            security.validate_path(str(tmp_sandbox / "file2.py"))

    def test_denied_extensions(self, tmp_sandbox: Path) -> None:
        """Test that denied extensions are blocked."""
        security = FilesystemSecurity(
            base_directory=tmp_sandbox,
            denied_extensions={".exe", ".sh"},
        )

        # txt should be allowed
        result = security.validate_path(str(tmp_sandbox / "file1.txt"))
        assert result == tmp_sandbox / "file1.txt"

        # Create a .sh file for testing
        sh_file = tmp_sandbox / "script.sh"
        sh_file.touch()

        with pytest.raises(PermissionError, match=r"Extension \.sh is denied"):
            security.validate_path(str(sh_file))


class TestReadFile:
    """Tests for read_file tool."""

    def test_read_existing_file(self, tmp_sandbox: Path) -> None:
        """Test reading an existing file."""
        content = read_file(str(tmp_sandbox / "file1.txt"))
        assert content == "Hello, World!"

    def test_read_nested_file(self, tmp_sandbox: Path) -> None:
        """Test reading a nested file."""
        content = read_file(str(tmp_sandbox / "subdir" / "nested.txt"))
        assert content == "Nested content"

    def test_read_with_encoding(self, tmp_sandbox: Path) -> None:
        """Test reading file with specific encoding."""
        # Create a UTF-8 file with special characters
        test_file = tmp_sandbox / "unicode.txt"
        test_file.write_text("Hello \u4e16\u754c", encoding="utf-8")

        content = read_file(str(test_file), encoding="utf-8")
        assert content == "Hello \u4e16\u754c"

    def test_read_nonexistent_file(self, tmp_sandbox: Path) -> None:
        """Test that reading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            read_file(str(tmp_sandbox / "nonexistent.txt"))

    def test_read_with_security(self, tmp_sandbox: Path) -> None:
        """Test reading with security context."""
        security = FilesystemSecurity(base_directory=tmp_sandbox)

        content = read_file(str(tmp_sandbox / "file1.txt"), security=security)
        assert content == "Hello, World!"

    def test_read_outside_sandbox(self, tmp_sandbox: Path) -> None:
        """Test that reading outside sandbox is blocked."""
        security = FilesystemSecurity(base_directory=tmp_sandbox)

        with pytest.raises(PermissionError):
            read_file("/etc/passwd", security=security)


class TestWriteFile:
    """Tests for write_file tool."""

    def test_write_new_file(self, tmp_sandbox: Path) -> None:
        """Test writing a new file."""
        new_file = tmp_sandbox / "new_file.txt"

        result = write_file(str(new_file), "New content")

        assert new_file.read_text() == "New content"
        assert result == str(new_file)

    def test_overwrite_existing_file(self, tmp_sandbox: Path) -> None:
        """Test overwriting an existing file."""
        existing_file = tmp_sandbox / "file1.txt"

        result = write_file(str(existing_file), "Overwritten content")

        assert existing_file.read_text() == "Overwritten content"
        assert result == str(existing_file)

    def test_write_with_encoding(self, tmp_sandbox: Path) -> None:
        """Test writing file with specific encoding."""
        test_file = tmp_sandbox / "unicode.txt"

        write_file(str(test_file), "Hello \u4e16\u754c", encoding="utf-8")

        assert test_file.read_text(encoding="utf-8") == "Hello \u4e16\u754c"

    def test_write_creates_parent_dirs(self, tmp_sandbox: Path) -> None:
        """Test that write creates parent directories if needed."""
        deep_file = tmp_sandbox / "new_dir" / "deep" / "file.txt"

        write_file(str(deep_file), "Deep content", create_parents=True)

        assert deep_file.read_text() == "Deep content"

    def test_write_with_security(self, tmp_sandbox: Path) -> None:
        """Test writing with security context."""
        security = FilesystemSecurity(base_directory=tmp_sandbox)
        new_file = tmp_sandbox / "secured.txt"

        write_file(str(new_file), "Secured content", security=security)

        assert new_file.read_text() == "Secured content"


class TestAppendFile:
    """Tests for append_file tool."""

    def test_append_to_existing_file(self, tmp_sandbox: Path) -> None:
        """Test appending to an existing file."""
        existing_file = tmp_sandbox / "file1.txt"

        result = append_file(str(existing_file), "\nAppended content")

        assert existing_file.read_text() == "Hello, World!\nAppended content"
        assert result == str(existing_file)

    def test_append_to_new_file(self, tmp_sandbox: Path) -> None:
        """Test appending to a new file (creates it)."""
        new_file = tmp_sandbox / "append_new.txt"

        append_file(str(new_file), "New content")

        assert new_file.read_text() == "New content"


class TestListDirectory:
    """Tests for list_directory tool."""

    def test_list_directory_flat(self, tmp_sandbox: Path) -> None:
        """Test listing directory without recursion."""
        entries = list_directory(str(tmp_sandbox), recursive=False)

        # Should contain file1.txt, file2.py, and subdir
        names = [entry["name"] for entry in entries]
        assert "file1.txt" in names
        assert "file2.py" in names
        assert "subdir" in names

    def test_list_directory_recursive(self, tmp_sandbox: Path) -> None:
        """Test listing directory with recursion."""
        entries = list_directory(str(tmp_sandbox), recursive=True)

        # Should include nested.txt from subdir
        paths = [entry["path"] for entry in entries]
        assert any("nested.txt" in p for p in paths)

    def test_list_directory_max_depth(self, tmp_sandbox: Path) -> None:
        """Test listing with max depth."""
        # Create deeper structure
        deep_dir = tmp_sandbox / "level1" / "level2" / "level3"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.txt").write_text("deep")

        entries = list_directory(str(tmp_sandbox), recursive=True, max_depth=2)

        # level3 should not be included
        paths = [entry["path"] for entry in entries]
        assert not any("level3" in p for p in paths)

    def test_list_nonexistent_directory(self, tmp_sandbox: Path) -> None:
        """Test listing nonexistent directory."""
        with pytest.raises(FileNotFoundError):
            list_directory(str(tmp_sandbox / "nonexistent"))

    def test_list_file_as_directory(self, tmp_sandbox: Path) -> None:
        """Test listing a file instead of directory."""
        with pytest.raises(NotADirectoryError):
            list_directory(str(tmp_sandbox / "file1.txt"))


class TestFileInfo:
    """Tests for file_info tool."""

    def test_file_info_regular_file(self, tmp_sandbox: Path) -> None:
        """Test getting info for a regular file."""
        info = file_info(str(tmp_sandbox / "file1.txt"))

        assert info["name"] == "file1.txt"
        assert info["is_file"] is True
        assert info["is_dir"] is False
        assert info["size"] == len("Hello, World!")
        assert "modified" in info
        assert "created" in info

    def test_file_info_directory(self, tmp_sandbox: Path) -> None:
        """Test getting info for a directory."""
        info = file_info(str(tmp_sandbox / "subdir"))

        assert info["name"] == "subdir"
        assert info["is_file"] is False
        assert info["is_dir"] is True

    def test_file_info_nonexistent(self, tmp_sandbox: Path) -> None:
        """Test getting info for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            file_info(str(tmp_sandbox / "nonexistent.txt"))


class TestDeleteFile:
    """Tests for delete_file tool."""

    def test_delete_file(self, tmp_sandbox: Path) -> None:
        """Test deleting a file."""
        target = tmp_sandbox / "to_delete.txt"
        target.write_text("delete me")

        result = delete_file(str(target))

        assert not target.exists()
        assert result is True

    def test_delete_nonexistent_file(self, tmp_sandbox: Path) -> None:
        """Test deleting nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            delete_file(str(tmp_sandbox / "nonexistent.txt"))

    def test_delete_with_security(self, tmp_sandbox: Path) -> None:
        """Test deleting with security context."""
        security = FilesystemSecurity(base_directory=tmp_sandbox)
        target = tmp_sandbox / "secured_delete.txt"
        target.write_text("delete me")

        delete_file(str(target), security=security)

        assert not target.exists()


class TestMoveFile:
    """Tests for move_file tool."""

    def test_move_file(self, tmp_sandbox: Path) -> None:
        """Test moving a file."""
        source = tmp_sandbox / "source.txt"
        source.write_text("move me")
        dest = tmp_sandbox / "dest.txt"

        result = move_file(str(source), str(dest))

        assert not source.exists()
        assert dest.exists()
        assert dest.read_text() == "move me"
        assert result == str(dest)

    def test_move_file_to_directory(self, tmp_sandbox: Path) -> None:
        """Test moving file into a directory."""
        source = tmp_sandbox / "source.txt"
        source.write_text("move me")

        move_file(str(source), str(tmp_sandbox / "subdir"))

        assert not source.exists()
        assert (tmp_sandbox / "subdir" / "source.txt").exists()

    def test_move_nonexistent_file(self, tmp_sandbox: Path) -> None:
        """Test moving nonexistent file."""
        with pytest.raises(FileNotFoundError):
            move_file(
                str(tmp_sandbox / "nonexistent.txt"),
                str(tmp_sandbox / "dest.txt"),
            )


class TestCopyFile:
    """Tests for copy_file tool."""

    def test_copy_file(self, tmp_sandbox: Path) -> None:
        """Test copying a file."""
        source = tmp_sandbox / "file1.txt"
        dest = tmp_sandbox / "copied.txt"

        result = copy_file(str(source), str(dest))

        assert source.exists()  # Original should still exist
        assert dest.exists()
        assert dest.read_text() == "Hello, World!"
        assert result == str(dest)

    def test_copy_file_to_directory(self, tmp_sandbox: Path) -> None:
        """Test copying file into a directory."""
        source = tmp_sandbox / "file1.txt"

        copy_file(str(source), str(tmp_sandbox / "subdir"))

        assert source.exists()
        assert (tmp_sandbox / "subdir" / "file1.txt").exists()
        assert (tmp_sandbox / "subdir" / "file1.txt").read_text() == "Hello, World!"

    def test_copy_nonexistent_file(self, tmp_sandbox: Path) -> None:
        """Test copying nonexistent file."""
        with pytest.raises(FileNotFoundError):
            copy_file(
                str(tmp_sandbox / "nonexistent.txt"),
                str(tmp_sandbox / "dest.txt"),
            )
