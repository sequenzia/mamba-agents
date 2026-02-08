"""Tests for skill discovery from directories."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mamba_agents.skills.config import SkillConfig, SkillInfo, SkillScope, TrustLevel
from mamba_agents.skills.discovery import discover_skills, scan_directory
from mamba_agents.skills.errors import SkillConflictError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_FRONTMATTER = """\
---
name: {name}
description: A test skill called {name}
---
"""


def _make_skill(
    base_dir: Path,
    name: str,
    frontmatter: str | None = None,
) -> Path:
    """Create a skill directory with a SKILL.md file.

    Args:
        base_dir: Parent directory for skill directories.
        name: Skill name (also used as directory name).
        frontmatter: Optional custom frontmatter content.

    Returns:
        Path to the created SKILL.md file.
    """
    skill_dir = base_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = frontmatter if frontmatter else _MINIMAL_FRONTMATTER.format(name=name)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(content, encoding="utf-8")
    return skill_md


def _make_config(
    tmp_path: Path,
    *,
    project_dir: Path | None = None,
    user_dir: Path | None = None,
    custom_paths: list[Path] | None = None,
    trusted_paths: list[Path] | None = None,
) -> SkillConfig:
    """Build a SkillConfig for testing.

    Creates directories as needed and returns a config pointing to them.
    """
    p_dir = project_dir or (tmp_path / "project" / ".mamba" / "skills")
    u_dir = user_dir or (tmp_path / "user" / ".mamba" / "skills")

    return SkillConfig(
        skills_dirs=[p_dir],
        user_skills_dir=u_dir,
        custom_paths=custom_paths or [],
        trusted_paths=trusted_paths or [],
    )


# ---------------------------------------------------------------------------
# scan_directory — Functional tests
# ---------------------------------------------------------------------------


class TestScanDirectorySingleDirectory:
    """Discover from single directory with multiple skills."""

    def test_discovers_multiple_skills(self, tmp_path: Path) -> None:
        """Scan directory with multiple skill subdirectories."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _make_skill(skills_dir, "alpha")
        _make_skill(skills_dir, "beta")
        _make_skill(skills_dir, "gamma")

        result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert len(result) == 3
        names = {s.name for s in result}
        assert names == {"alpha", "beta", "gamma"}

    def test_assigns_scope(self, tmp_path: Path) -> None:
        """Skills get the scope passed to scan_directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _make_skill(skills_dir, "my-skill")

        result = scan_directory(skills_dir, SkillScope.USER, TrustLevel.TRUSTED)

        assert len(result) == 1
        assert result[0].scope is SkillScope.USER

    def test_assigns_trust_level(self, tmp_path: Path) -> None:
        """Skills get the trust level passed to scan_directory."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _make_skill(skills_dir, "my-skill")

        result = scan_directory(skills_dir, SkillScope.CUSTOM, TrustLevel.UNTRUSTED)

        assert len(result) == 1
        assert result[0].trust_level is TrustLevel.UNTRUSTED

    def test_returns_skill_info_instances(self, tmp_path: Path) -> None:
        """Results are SkillInfo dataclass instances."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _make_skill(skills_dir, "my-skill")

        result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert len(result) == 1
        assert isinstance(result[0], SkillInfo)

    def test_skill_path_is_directory(self, tmp_path: Path) -> None:
        """SkillInfo.path points to the skill directory, not the file."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        _make_skill(skills_dir, "my-skill")

        result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert result[0].path == skills_dir / "my-skill"
        assert result[0].path.is_dir()


# ---------------------------------------------------------------------------
# scan_directory — Edge cases
# ---------------------------------------------------------------------------


class TestScanDirectoryEdgeCases:
    """Edge cases for directory scanning."""

    def test_empty_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """Empty skills directory returns empty list without error."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert result == []

    def test_nonexistent_directory_returns_empty_list(self, tmp_path: Path) -> None:
        """Non-existent directory returns empty list without error."""
        missing = tmp_path / "does-not-exist"

        result = scan_directory(missing, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert result == []

    def test_directory_without_skill_md_skipped(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Subdirectory without SKILL.md is silently skipped (no glob match)."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        # Create a directory without SKILL.md
        (skills_dir / "broken-skill").mkdir()
        # Also create a valid one
        _make_skill(skills_dir, "valid-skill")

        result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert len(result) == 1
        assert result[0].name == "valid-skill"

    def test_malformed_skill_md_skipped_with_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Malformed SKILL.md is skipped with error log, not aborting discovery."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        # Invalid frontmatter (no closing ---)
        bad_dir = skills_dir / "bad-skill"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("not valid frontmatter\n", encoding="utf-8")
        # Valid skill
        _make_skill(skills_dir, "good-skill")

        with caplog.at_level(logging.ERROR):
            result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert len(result) == 1
        assert result[0].name == "good-skill"
        assert any("bad-skill" in r.message for r in caplog.records if r.levelno >= logging.ERROR)

    def test_same_scope_duplicate_raises_conflict_error(self, tmp_path: Path) -> None:
        """Symlinks or multi-dir setup with same name in same scope raises error.

        Since the filesystem prevents two directories with the same name, we
        test via discover_skills with two skills_dirs (both PROJECT scope)
        that each contain a skill with the same name.
        """
        # See TestNameConflictResolution for the discover_skills-level test.
        # For scan_directory itself, same-scope dups within a single dir
        # are impossible because the loader validates name == dirname.

    def test_symlinked_skill_directory_followed(self, tmp_path: Path) -> None:
        """Symlinked skill directories are followed."""
        # Create actual skill
        actual_dir = tmp_path / "actual-skills" / "my-skill"
        actual_dir.mkdir(parents=True)
        (actual_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Linked skill\n---\n",
            encoding="utf-8",
        )

        # Create skills dir with a symlink
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        symlink = skills_dir / "my-skill"
        symlink.symlink_to(actual_dir)

        result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert len(result) == 1
        assert result[0].name == "my-skill"


# ---------------------------------------------------------------------------
# scan_directory — Error handling
# ---------------------------------------------------------------------------


class TestScanDirectoryErrorHandling:
    """Error handling during directory scanning."""

    def test_individual_parse_failure_does_not_abort(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Individual skill parse failures don't abort entire discovery."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        # Skill with missing required fields
        bad_dir = skills_dir / "bad-skill"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("---\nfoo: bar\n---\n", encoding="utf-8")

        # Valid skill
        _make_skill(skills_dir, "good-skill")

        with caplog.at_level(logging.ERROR):
            result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert len(result) == 1
        assert result[0].name == "good-skill"

    def test_permission_denied_on_directory(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Permission denied on directory logs warning and returns empty list."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        skills_dir.chmod(0o000)

        try:
            with caplog.at_level(logging.WARNING):
                result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

            assert result == []
        finally:
            # Restore permissions for cleanup
            skills_dir.chmod(0o755)


# ---------------------------------------------------------------------------
# discover_skills — Priority ordering
# ---------------------------------------------------------------------------


class TestDiscoverSkillsPriority:
    """Priority ordering across project/user/custom scopes."""

    def test_discovers_from_project_directory(self, tmp_path: Path) -> None:
        """Discovers skills from project-level .mamba/skills/."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "my-skill")

        config = _make_config(tmp_path, project_dir=project_dir)
        result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "my-skill"
        assert result[0].scope is SkillScope.PROJECT

    def test_discovers_from_user_directory(self, tmp_path: Path) -> None:
        """Discovers skills from user-level ~/.mamba/skills/."""
        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        _make_skill(user_dir, "user-skill")

        config = _make_config(tmp_path, user_dir=user_dir)
        result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "user-skill"
        assert result[0].scope is SkillScope.USER

    def test_discovers_from_custom_paths(self, tmp_path: Path) -> None:
        """Discovers skills from custom paths in SkillConfig.custom_paths."""
        custom_dir = tmp_path / "custom-skills"
        custom_dir.mkdir()
        _make_skill(custom_dir, "custom-skill")

        config = _make_config(tmp_path, custom_paths=[custom_dir])
        result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "custom-skill"
        assert result[0].scope is SkillScope.CUSTOM

    def test_project_overrides_user_on_name_conflict(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Project-level skill wins over user-level on name conflict."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "shared-skill")

        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        _make_skill(user_dir, "shared-skill")

        config = _make_config(tmp_path, project_dir=project_dir, user_dir=user_dir)

        with caplog.at_level(logging.INFO):
            result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "shared-skill"
        assert result[0].scope is SkillScope.PROJECT

    def test_user_overrides_custom_on_name_conflict(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """User-level skill wins over custom-level on name conflict."""
        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        _make_skill(user_dir, "shared-skill")

        custom_dir = tmp_path / "custom-skills"
        custom_dir.mkdir()
        _make_skill(custom_dir, "shared-skill")

        config = _make_config(tmp_path, user_dir=user_dir, custom_paths=[custom_dir])

        with caplog.at_level(logging.INFO):
            result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "shared-skill"
        assert result[0].scope is SkillScope.USER

    def test_project_overrides_custom_on_name_conflict(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Project-level skill wins over custom-level on name conflict."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "shared-skill")

        custom_dir = tmp_path / "custom-skills"
        custom_dir.mkdir()
        _make_skill(custom_dir, "shared-skill")

        config = _make_config(tmp_path, project_dir=project_dir, custom_paths=[custom_dir])

        with caplog.at_level(logging.INFO):
            result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "shared-skill"
        assert result[0].scope is SkillScope.PROJECT

    def test_cross_scope_conflict_logs_info(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Cross-scope name conflict logs an info message."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "shared-skill")

        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        _make_skill(user_dir, "shared-skill")

        config = _make_config(tmp_path, project_dir=project_dir, user_dir=user_dir)

        with caplog.at_level(logging.INFO):
            discover_skills(config)

        info_messages = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any("shared-skill" in msg and "shadows" in msg for msg in info_messages)


# ---------------------------------------------------------------------------
# discover_skills — Name conflict resolution
# ---------------------------------------------------------------------------


class TestNameConflictResolution:
    """Name conflict resolution (cross-scope and same-scope)."""

    def test_three_scope_conflict_project_wins(self, tmp_path: Path) -> None:
        """When all three scopes have same skill, project wins."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "shared-skill")

        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        _make_skill(user_dir, "shared-skill")

        custom_dir = tmp_path / "custom-skills"
        custom_dir.mkdir()
        _make_skill(custom_dir, "shared-skill")

        config = _make_config(
            tmp_path,
            project_dir=project_dir,
            user_dir=user_dir,
            custom_paths=[custom_dir],
        )
        result = discover_skills(config)

        assert len(result) == 1
        assert result[0].scope is SkillScope.PROJECT

    def test_same_scope_conflict_raises_error(self, tmp_path: Path) -> None:
        """Same-scope duplicate names raise SkillConflictError.

        Tested via discover_skills with multiple skills_dirs (both PROJECT
        scope) each containing a skill with the same name.
        """
        dir_a = tmp_path / "project-a"
        dir_a.mkdir()
        _make_skill(dir_a, "dup-skill")

        dir_b = tmp_path / "project-b"
        dir_b.mkdir()
        _make_skill(dir_b, "dup-skill")

        config = SkillConfig(
            skills_dirs=[dir_a, dir_b],
            user_skills_dir=tmp_path / "nonexistent",
            custom_paths=[],
            trusted_paths=[],
        )

        with pytest.raises(SkillConflictError, match="dup-skill"):
            discover_skills(config)

    def test_non_conflicting_skills_all_returned(self, tmp_path: Path) -> None:
        """Skills with unique names across all scopes are all returned."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "project-skill")

        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        _make_skill(user_dir, "user-skill")

        custom_dir = tmp_path / "custom-skills"
        custom_dir.mkdir()
        _make_skill(custom_dir, "custom-skill")

        config = _make_config(
            tmp_path,
            project_dir=project_dir,
            user_dir=user_dir,
            custom_paths=[custom_dir],
        )
        result = discover_skills(config)

        assert len(result) == 3
        names = {s.name for s in result}
        assert names == {"project-skill", "user-skill", "custom-skill"}


# ---------------------------------------------------------------------------
# discover_skills — Trust level assignment
# ---------------------------------------------------------------------------


class TestTrustLevelAssignment:
    """Trust level assignment based on scope and trusted_paths."""

    def test_project_skills_are_trusted(self, tmp_path: Path) -> None:
        """Project-scope skills are assigned TRUSTED trust level."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "my-skill")

        config = _make_config(tmp_path, project_dir=project_dir)
        result = discover_skills(config)

        assert result[0].trust_level is TrustLevel.TRUSTED

    def test_user_skills_are_trusted(self, tmp_path: Path) -> None:
        """User-scope skills are assigned TRUSTED trust level."""
        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        _make_skill(user_dir, "my-skill")

        config = _make_config(tmp_path, user_dir=user_dir)
        result = discover_skills(config)

        assert result[0].trust_level is TrustLevel.TRUSTED

    def test_custom_path_skills_are_untrusted_by_default(self, tmp_path: Path) -> None:
        """Custom-path skills are UNTRUSTED by default."""
        custom_dir = tmp_path / "custom-skills"
        custom_dir.mkdir()
        _make_skill(custom_dir, "my-skill")

        config = _make_config(tmp_path, custom_paths=[custom_dir])
        result = discover_skills(config)

        assert result[0].trust_level is TrustLevel.UNTRUSTED

    def test_custom_path_in_trusted_paths_is_trusted(self, tmp_path: Path) -> None:
        """Custom paths in trusted_paths config are assigned TRUSTED."""
        custom_dir = tmp_path / "custom-skills"
        custom_dir.mkdir()
        _make_skill(custom_dir, "my-skill")

        config = _make_config(
            tmp_path,
            custom_paths=[custom_dir],
            trusted_paths=[custom_dir],
        )
        result = discover_skills(config)

        assert result[0].trust_level is TrustLevel.TRUSTED

    def test_some_custom_paths_trusted_others_not(self, tmp_path: Path) -> None:
        """Only custom paths in trusted_paths are trusted; others remain untrusted."""
        trusted_dir = tmp_path / "trusted-custom"
        trusted_dir.mkdir()
        _make_skill(trusted_dir, "trusted-skill")

        untrusted_dir = tmp_path / "untrusted-custom"
        untrusted_dir.mkdir()
        _make_skill(untrusted_dir, "untrusted-skill")

        config = _make_config(
            tmp_path,
            custom_paths=[trusted_dir, untrusted_dir],
            trusted_paths=[trusted_dir],
        )
        result = discover_skills(config)

        by_name = {s.name: s for s in result}
        assert by_name["trusted-skill"].trust_level is TrustLevel.TRUSTED
        assert by_name["untrusted-skill"].trust_level is TrustLevel.UNTRUSTED


# ---------------------------------------------------------------------------
# discover_skills — Empty / missing directories
# ---------------------------------------------------------------------------


class TestEmptyAndMissingDirectories:
    """Empty/missing directories handled gracefully."""

    def test_all_directories_missing(self, tmp_path: Path) -> None:
        """All configured directories missing returns empty list."""
        config = _make_config(tmp_path)
        result = discover_skills(config)
        assert result == []

    def test_empty_project_directory(self, tmp_path: Path) -> None:
        """Empty project directory returns empty list."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        config = _make_config(tmp_path, project_dir=project_dir)
        result = discover_skills(config)
        assert result == []

    def test_some_directories_exist_others_missing(self, tmp_path: Path) -> None:
        """Only existing directories are scanned; missing ones are skipped."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        _make_skill(project_dir, "my-skill")

        # user_dir doesn't exist
        config = _make_config(tmp_path, project_dir=project_dir)
        result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "my-skill"


# ---------------------------------------------------------------------------
# discover_skills — Malformed skills
# ---------------------------------------------------------------------------


class TestMalformedSkillsSkipped:
    """Malformed skill directories skipped with warning."""

    def test_invalid_yaml_skipped(self, tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
        """Skill with invalid YAML frontmatter is skipped."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        # Invalid YAML
        bad_dir = project_dir / "bad-yaml"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("---\n: invalid: yaml: [\n---\n", encoding="utf-8")
        _make_skill(project_dir, "good-skill")

        config = _make_config(tmp_path, project_dir=project_dir)

        with caplog.at_level(logging.ERROR):
            result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "good-skill"

    def test_missing_required_fields_skipped(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Skill missing required frontmatter fields is skipped."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        bad_dir = project_dir / "no-name"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("---\nfoo: bar\n---\n", encoding="utf-8")
        _make_skill(project_dir, "good-skill")

        config = _make_config(tmp_path, project_dir=project_dir)

        with caplog.at_level(logging.ERROR):
            result = discover_skills(config)

        assert len(result) == 1
        assert result[0].name == "good-skill"

    def test_multiple_malformed_skills_all_skipped(self, tmp_path: Path) -> None:
        """Multiple malformed skills are all skipped; valid ones returned."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        # Bad skill 1
        bad1 = project_dir / "bad-one"
        bad1.mkdir()
        (bad1 / "SKILL.md").write_text("no frontmatter at all\n", encoding="utf-8")

        # Bad skill 2
        bad2 = project_dir / "bad-two"
        bad2.mkdir()
        (bad2 / "SKILL.md").write_text("---\n---\n", encoding="utf-8")

        # Good skills
        _make_skill(project_dir, "good-one")
        _make_skill(project_dir, "good-two")

        config = _make_config(tmp_path, project_dir=project_dir)
        result = discover_skills(config)

        names = {s.name for s in result}
        assert names == {"good-one", "good-two"}


# ---------------------------------------------------------------------------
# discover_skills — Multiple custom paths
# ---------------------------------------------------------------------------


class TestMultipleCustomPaths:
    """Discover skills from multiple custom paths."""

    def test_multiple_custom_paths_scanned(self, tmp_path: Path) -> None:
        """All custom paths are scanned and skills returned."""
        custom_a = tmp_path / "custom-a"
        custom_a.mkdir()
        _make_skill(custom_a, "skill-a")

        custom_b = tmp_path / "custom-b"
        custom_b.mkdir()
        _make_skill(custom_b, "skill-b")

        config = _make_config(tmp_path, custom_paths=[custom_a, custom_b])
        result = discover_skills(config)

        names = {s.name for s in result}
        assert names == {"skill-a", "skill-b"}

    def test_cross_custom_path_same_name_raises_conflict(self, tmp_path: Path) -> None:
        """Skills with same name across custom paths raises SkillConflictError.

        Both custom paths are CUSTOM scope, so this is a same-scope conflict.
        """
        custom_a = tmp_path / "custom-a"
        custom_a.mkdir()
        _make_skill(custom_a, "shared-skill")

        custom_b = tmp_path / "custom-b"
        custom_b.mkdir()
        _make_skill(custom_b, "shared-skill")

        config = _make_config(tmp_path, custom_paths=[custom_a, custom_b])

        with pytest.raises(SkillConflictError, match="shared-skill"):
            discover_skills(config)


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestDiscoveryPerformance:
    """Performance characteristics of skill discovery."""

    def test_scan_50_skills_under_100ms(self, tmp_path: Path) -> None:
        """Scanning 50 skills should complete in under 100ms."""
        import time

        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        for i in range(50):
            name = f"skill-{i:03d}"
            _make_skill(skills_dir, name)

        start = time.monotonic()
        result = scan_directory(skills_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)
        elapsed_ms = (time.monotonic() - start) * 1000

        assert len(result) == 50
        assert elapsed_ms < 100, f"Scan took {elapsed_ms:.1f}ms, expected < 100ms"
