"""Cross-cutting integration tests for the skills subsystem.

These tests verify interactions between multiple skills components
(loader, registry, discovery, validator, invocation, manager) working
together. Individual module tests are in tests/unit/test_skill_*.py.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from mamba_agents.skills.config import (
    Skill,
    SkillConfig,
    SkillInfo,
    SkillScope,
    TrustLevel,
)
from mamba_agents.skills.discovery import discover_skills, scan_directory
from mamba_agents.skills.errors import (
    SkillConflictError,
    SkillInvocationError,
    SkillNotFoundError,
    SkillValidationError,
)
from mamba_agents.skills.invocation import (
    InvocationSource,
    activate,
    check_invocation_permission,
    deactivate,
    substitute_arguments,
)
from mamba_agents.skills.loader import load_full, load_metadata
from mamba_agents.skills.manager import SkillManager
from mamba_agents.skills.registry import SkillRegistry
from mamba_agents.skills.validator import (
    check_trust_restrictions,
    resolve_trust_level,
    validate,
    validate_frontmatter,
)

# ---------------------------------------------------------------------------
# Loader -> Registry integration
# ---------------------------------------------------------------------------


class TestLoaderRegistryIntegration:
    """Tests verifying loader output feeds correctly into the registry."""

    def test_load_metadata_result_registers_in_registry(self, tmp_path: Path) -> None:
        """SkillInfo from load_metadata can be registered in a SkillRegistry."""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Loader to registry\n---\n\n# Body\n"
        )

        info = load_metadata(skill_dir / "SKILL.md")
        registry = SkillRegistry()
        registry.register(info)

        assert registry.has("my-skill")
        assert registry.list()[0].name == "my-skill"

    def test_load_full_result_registers_with_body(self, tmp_path: Path) -> None:
        """Skill from load_full registers with body content intact."""
        skill_dir = tmp_path / "body-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: body-skill\ndescription: With body\n---\n\n# Instructions\n\nDo stuff.\n"
        )

        skill = load_full(skill_dir / "SKILL.md")
        registry = SkillRegistry()
        registry.register(skill)

        result = registry.get("body-skill")
        assert result is not None
        assert result.body is not None
        assert "Instructions" in result.body

    def test_load_metadata_then_lazy_body_via_registry(self, tmp_path: Path) -> None:
        """Metadata registered first, body lazy-loaded when accessed via get()."""
        skill_dir = tmp_path / "lazy-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: lazy-skill\ndescription: Lazy load\n---\n\n# Lazily Loaded\n"
        )

        info = load_metadata(skill_dir / "SKILL.md")
        registry = SkillRegistry()
        registry.register(info)

        # Body should be lazy-loaded on get()
        skill = registry.get("lazy-skill")
        assert skill is not None
        assert skill.body is not None
        assert "Lazily Loaded" in skill.body


# ---------------------------------------------------------------------------
# Loader -> Validator integration
# ---------------------------------------------------------------------------


class TestLoaderValidatorIntegration:
    """Tests verifying loader and validator work consistently."""

    def test_loader_rejects_what_validator_flags(self, tmp_path: Path) -> None:
        """Loader raises errors for the same issues validator detects."""
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: BAD-NAME!\n---\n")

        # Validator should flag this
        result = validate(skill_dir)
        assert not result.valid

        # Loader should also reject it
        with pytest.raises((SkillValidationError, SkillNotFoundError)):
            load_metadata(skill_dir / "SKILL.md")

    def test_valid_skill_passes_both_loader_and_validator(self, tmp_path: Path) -> None:
        """A valid skill passes both the validator and the loader."""
        skill_dir = tmp_path / "valid-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: valid-skill\ndescription: All good\n---\n\n# Body\n"
        )

        # Validator passes
        result = validate(skill_dir)
        assert result.valid

        # Loader succeeds
        info = load_metadata(skill_dir / "SKILL.md")
        assert info.name == "valid-skill"

    def test_frontmatter_validation_matches_loader_requirements(self) -> None:
        """validate_frontmatter and loader enforce the same field requirements."""
        # Missing both required fields
        data_missing: dict[str, object] = {"license": "MIT"}
        result = validate_frontmatter(data_missing)
        assert not result.valid
        assert any("name" in e for e in result.errors)
        assert any("description" in e for e in result.errors)

        # Valid fields
        data_valid = {"name": "ok", "description": "ok"}
        result = validate_frontmatter(data_valid)
        assert result.valid


# ---------------------------------------------------------------------------
# Discovery -> Registry -> Activation chain
# ---------------------------------------------------------------------------


class TestDiscoveryRegistryActivationChain:
    """Tests verifying the full discover -> register -> activate chain."""

    def test_discover_register_activate_deactivate(self, tmp_path: Path) -> None:
        """Full lifecycle through discovery, registry, and invocation."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        # Create a skill with $ARGUMENTS placeholder
        skill_dir = project_dir / "chain-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: chain-skill\ndescription: Full chain\n---\n\n"
            "Process: $ARGUMENTS\n"
        )

        # Discover
        config = SkillConfig(
            skills_dirs=[project_dir],
            user_skills_dir=tmp_path / "user",
            custom_paths=[],
        )
        discovered = discover_skills(config)
        assert len(discovered) == 1

        # Register in a new registry
        registry = SkillRegistry()
        registry.register(discovered[0])
        assert registry.has("chain-skill")

        # Get and activate with arguments
        skill = registry.get("chain-skill")
        assert skill is not None
        content = activate(skill, "hello world")
        assert "Process: hello world" in content
        assert skill.is_active

        # Deactivate
        deactivate(skill)
        assert not skill.is_active

    def test_discovered_skills_activate_with_substitution(
        self, tmp_path: Path
    ) -> None:
        """Discovered skills support argument substitution when activated."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        skill_dir = project_dir / "sub-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: sub-skill\ndescription: Substitution test\n---\n\n"
            "File: $0\nMode: $1\n"
        )

        config = SkillConfig(
            skills_dirs=[project_dir],
            user_skills_dir=tmp_path / "user",
            custom_paths=[],
        )
        discovered = discover_skills(config)

        registry = SkillRegistry()
        registry.register(discovered[0])
        skill = registry.get("sub-skill")
        content = activate(skill, "test.py read")

        assert "File: test.py" in content
        assert "Mode: read" in content


# ---------------------------------------------------------------------------
# Discovery -> Trust Level -> Invocation Permission chain
# ---------------------------------------------------------------------------


class TestDiscoveryTrustInvocationChain:
    """Tests verifying trust level flows from discovery to invocation checks."""

    def test_project_skill_is_trusted_and_invocable(self, tmp_path: Path) -> None:
        """Project-scoped skills are trusted and pass all permission checks."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        skill_dir = project_dir / "trusted-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: trusted-skill\ndescription: Project trusted\n---\n\nBody.\n"
        )

        infos = scan_directory(project_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)
        assert len(infos) == 1
        info = infos[0]

        assert info.trust_level is TrustLevel.TRUSTED
        assert check_invocation_permission(info, InvocationSource.MODEL) is True
        assert check_invocation_permission(info, InvocationSource.USER) is True
        assert check_invocation_permission(info, InvocationSource.CODE) is True

    def test_custom_untrusted_skill_with_hooks_has_violations(
        self, tmp_path: Path
    ) -> None:
        """Custom untrusted skill with hooks triggers trust violations."""
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        skill_dir = custom_dir / "restricted"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: restricted\ndescription: Has hooks\n"
            "hooks:\n  on_activate: setup\n---\n\nBody.\n"
        )

        infos = scan_directory(custom_dir, SkillScope.CUSTOM, TrustLevel.UNTRUSTED)
        assert len(infos) == 1
        info = infos[0]

        assert info.trust_level is TrustLevel.UNTRUSTED

        violations = check_trust_restrictions(info)
        assert len(violations) == 1
        assert "hooks" in violations[0].lower()

    def test_trust_resolution_matches_discovery_scope(self, tmp_path: Path) -> None:
        """Trust level resolved by resolve_trust_level matches discovery assignment."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        skill_dir_p = project_dir / "proj-skill"
        skill_dir_p.mkdir()
        (skill_dir_p / "SKILL.md").write_text(
            "---\nname: proj-skill\ndescription: ok\n---\n"
        )

        skill_dir_c = custom_dir / "cust-skill"
        skill_dir_c.mkdir()
        (skill_dir_c / "SKILL.md").write_text(
            "---\nname: cust-skill\ndescription: ok\n---\n"
        )

        # Project scope -> trusted
        level = resolve_trust_level(SkillScope.PROJECT, skill_dir_p)
        assert level is TrustLevel.TRUSTED

        # Custom scope -> untrusted by default
        level = resolve_trust_level(SkillScope.CUSTOM, skill_dir_c)
        assert level is TrustLevel.UNTRUSTED


# ---------------------------------------------------------------------------
# Error propagation across boundaries
# ---------------------------------------------------------------------------


class TestErrorPropagationAcrossBoundaries:
    """Tests verifying errors propagate correctly across component boundaries."""

    def test_loader_error_propagates_through_registry(self, tmp_path: Path) -> None:
        """Invalid SKILL.md causes an error when registered via path in registry."""
        bad_dir = tmp_path / "bad-skill"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("no frontmatter here")

        registry = SkillRegistry()

        with pytest.raises(SkillValidationError):
            registry.register(bad_dir)

    def test_discovery_error_does_not_crash_manager(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Manager.discover() handles discovery errors gracefully."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        # Bad skill
        bad_dir = project_dir / "bad-skill"
        bad_dir.mkdir()
        (bad_dir / "SKILL.md").write_text("no frontmatter")

        # Good skill
        good_dir = project_dir / "good-skill"
        good_dir.mkdir()
        (good_dir / "SKILL.md").write_text(
            "---\nname: good-skill\ndescription: ok\n---\n\nBody.\n"
        )

        config = SkillConfig(
            skills_dirs=[project_dir],
            user_skills_dir=tmp_path / "user",
            custom_paths=[],
        )
        manager = SkillManager(config=config)

        with caplog.at_level(logging.ERROR):
            result = manager.discover()

        assert len(result) == 1
        assert result[0].name == "good-skill"

    def test_activation_error_on_nonexistent_skill_through_manager(self) -> None:
        """Manager raises SkillNotFoundError for activation of missing skill."""
        manager = SkillManager()

        with pytest.raises(SkillNotFoundError, match="ghost"):
            manager.activate("ghost")

    def test_conflict_error_on_duplicate_registration_through_manager(self) -> None:
        """Manager raises SkillConflictError on duplicate registration."""
        manager = SkillManager()
        info = SkillInfo(
            name="dup",
            description="Dup skill",
            path=Path("/skills/dup"),
            scope=SkillScope.PROJECT,
        )
        manager.register(info)

        with pytest.raises(SkillConflictError, match="dup"):
            manager.register(
                SkillInfo(
                    name="dup",
                    description="Another dup",
                    path=Path("/skills/dup2"),
                    scope=SkillScope.PROJECT,
                )
            )


# ---------------------------------------------------------------------------
# Manager facade - end-to-end workflows
# ---------------------------------------------------------------------------


class TestManagerEndToEndWorkflows:
    """End-to-end tests through the SkillManager facade."""

    def test_discover_validate_activate_references_deactivate(
        self, tmp_path: Path
    ) -> None:
        """Complete workflow: discover -> validate -> activate -> refs -> deactivate."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        # Create a skill with references
        skill_dir = project_dir / "documented"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: documented\ndescription: With references\n---\n\n"
            "Use: $ARGUMENTS\n"
        )
        refs_dir = skill_dir / "references"
        refs_dir.mkdir()
        (refs_dir / "api.md").write_text("# API\n\nEndpoints.\n")

        config = SkillConfig(
            skills_dirs=[project_dir],
            user_skills_dir=tmp_path / "user",
            custom_paths=[],
        )
        manager = SkillManager(config=config)

        # 1. Discover
        discovered = manager.discover()
        assert len(discovered) == 1

        # 2. Validate
        result = manager.validate(skill_dir)
        assert result.valid

        # 3. Activate with arguments
        content = manager.activate("documented", arguments="test-arg")
        assert "Use: test-arg" in content
        assert manager.get("documented").is_active

        # 4. Check references
        refs = manager.get_references("documented")
        assert len(refs) == 1
        ref_content = manager.load_reference("documented", "api.md")
        assert "Endpoints" in ref_content

        # 5. Deactivate
        manager.deactivate("documented")
        assert not manager.get("documented").is_active

    def test_multi_scope_discover_with_priority(self, tmp_path: Path) -> None:
        """Manager discover respects scope priority across project/user/custom."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)
        user_dir = tmp_path / "user" / ".mamba" / "skills"
        user_dir.mkdir(parents=True)
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        # Same name in project and user - project should win
        for d in [project_dir, user_dir]:
            skill_dir = d / "shared"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: shared\ndescription: Shared skill\n---\n\nBody.\n"
            )

        # Unique custom skill
        custom_skill = custom_dir / "unique"
        custom_skill.mkdir()
        (custom_skill / "SKILL.md").write_text(
            "---\nname: unique\ndescription: Custom only\n---\n\nBody.\n"
        )

        config = SkillConfig(
            skills_dirs=[project_dir],
            user_skills_dir=user_dir,
            custom_paths=[custom_dir],
        )
        manager = SkillManager(config=config)
        discovered = manager.discover()

        # Should have 2: shared (project wins) + unique
        assert len(discovered) == 2
        names = {info.name for info in discovered}
        assert "shared" in names
        assert "unique" in names

        # Shared should have PROJECT scope (project wins over user)
        shared_info = next(i for i in discovered if i.name == "shared")
        assert shared_info.scope is SkillScope.PROJECT

    def test_register_then_discover_skips_existing(self, tmp_path: Path) -> None:
        """Skills registered before discover() are not duplicated."""
        project_dir = tmp_path / "project" / ".mamba" / "skills"
        project_dir.mkdir(parents=True)

        skill_dir = project_dir / "pre-registered"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: pre-registered\ndescription: ok\n---\n\nBody.\n"
        )

        config = SkillConfig(
            skills_dirs=[project_dir],
            user_skills_dir=tmp_path / "user",
            custom_paths=[],
        )
        manager = SkillManager(config=config)

        # Pre-register the same skill
        manager.register(skill_dir)
        assert len(manager) == 1

        # Discover should skip the already-registered one
        discovered = manager.discover()
        assert len(discovered) == 0
        assert len(manager) == 1

    def test_deregister_active_skill_then_reregister(self, tmp_path: Path) -> None:
        """Deregister active skill, then re-register and activate again."""
        skill_dir = tmp_path / "toggle"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: toggle\ndescription: Toggle test\n---\n\n"
            "Toggle content with $ARGUMENTS.\n"
        )

        manager = SkillManager()
        manager.register(skill_dir)
        content1 = manager.activate("toggle", arguments="first")
        assert "first" in content1

        manager.deregister("toggle")
        assert manager.get("toggle") is None

        # Re-register and activate again
        manager.register(skill_dir)
        content2 = manager.activate("toggle", arguments="second")
        assert "second" in content2


# ---------------------------------------------------------------------------
# Fixture integration tests
# ---------------------------------------------------------------------------


class TestFixtureIntegration:
    """Tests verifying the conftest.py fixtures work with skills components."""

    def test_sample_skill_dir_discovery(self, sample_skill_dir: Path) -> None:
        """sample_skill_dir fixture produces discoverable skills."""
        infos = scan_directory(sample_skill_dir, SkillScope.PROJECT, TrustLevel.TRUSTED)

        assert len(infos) == 2
        names = {info.name for info in infos}
        assert names == {"alpha", "beta"}

    def test_sample_skill_dir_loader(self, sample_skill_dir: Path) -> None:
        """sample_skill_dir fixture skills can be loaded by the loader."""
        alpha_md = sample_skill_dir / "alpha" / "SKILL.md"
        info = load_metadata(alpha_md)

        assert info.name == "alpha"
        assert info.description == "A sample skill called alpha"

    def test_sample_skill_dir_full_load(self, sample_skill_dir: Path) -> None:
        """sample_skill_dir skills load with body content."""
        alpha_md = sample_skill_dir / "alpha" / "SKILL.md"
        skill = load_full(alpha_md)

        assert skill.body is not None
        assert "$ARGUMENTS" in skill.body

    def test_sample_skill_dir_validation(self, sample_skill_dir: Path) -> None:
        """sample_skill_dir skills pass validation."""
        for name in ["alpha", "beta"]:
            result = validate(sample_skill_dir / name)
            assert result.valid, f"Skill '{name}' failed validation: {result.errors}"

    def test_sample_skill_dir_has_references(self, sample_skill_dir: Path) -> None:
        """sample_skill_dir beta skill has a references directory."""
        refs_dir = sample_skill_dir / "beta" / "references"
        assert refs_dir.exists()
        assert (refs_dir / "guide.md").exists()

    def test_sample_skill_info_fixture(self, sample_skill_info: SkillInfo) -> None:
        """sample_skill_info fixture provides a valid SkillInfo."""
        assert sample_skill_info.name == "sample-skill"
        assert sample_skill_info.scope is SkillScope.PROJECT
        assert isinstance(sample_skill_info, SkillInfo)

    def test_sample_skill_info_registers(self, sample_skill_info: SkillInfo) -> None:
        """sample_skill_info can be registered in a SkillRegistry."""
        registry = SkillRegistry()
        registry.register(sample_skill_info)
        assert registry.has("sample-skill")

    def test_sample_skill_fixture(self, sample_skill: Skill) -> None:
        """sample_skill fixture provides a Skill with body."""
        assert sample_skill.info.name == "sample-skill"
        assert sample_skill.body is not None
        assert "$ARGUMENTS" in sample_skill.body
        assert isinstance(sample_skill, Skill)

    def test_sample_skill_activates(self, sample_skill: Skill) -> None:
        """sample_skill can be activated with argument substitution."""
        content = activate(sample_skill, "test-input")
        assert "Process: test-input" in content
        assert sample_skill.is_active

    def test_sample_skill_registers_and_activates(self, sample_skill: Skill) -> None:
        """sample_skill works through the full registry -> activate chain."""
        registry = SkillRegistry()
        registry.register(sample_skill)

        skill = registry.get("sample-skill")
        assert skill is not None
        content = activate(skill, "hello")
        assert "Process: hello" in content

    def test_sample_skill_dir_manager_workflow(self, sample_skill_dir: Path) -> None:
        """sample_skill_dir works with SkillManager for full workflow."""
        config = SkillConfig(
            skills_dirs=[sample_skill_dir],
            user_skills_dir=sample_skill_dir.parent / "user",
            custom_paths=[],
        )
        manager = SkillManager(config=config)

        discovered = manager.discover()
        assert len(discovered) == 2

        content = manager.activate("alpha", arguments="my-file.txt")
        assert "my-file.txt" in content

        refs = manager.get_references("beta")
        assert len(refs) == 1

        manager.deactivate("alpha")
        assert not manager.get("alpha").is_active


# ---------------------------------------------------------------------------
# Validator -> Invocation interaction
# ---------------------------------------------------------------------------


class TestValidatorInvocationInteraction:
    """Tests verifying validator results influence invocation behavior."""

    def test_untrusted_skill_with_disable_model_invocation(self) -> None:
        """Untrusted skill that disables model invocation is correctly restricted."""
        info = SkillInfo(
            name="restricted",
            description="Restricted skill",
            path=Path("/skills/restricted"),
            scope=SkillScope.CUSTOM,
            trust_level=TrustLevel.UNTRUSTED,
            disable_model_invocation=True,
        )

        # Trust violations should be detected
        assert info.trust_level is TrustLevel.UNTRUSTED

        # Permission check should block model
        assert check_invocation_permission(info, InvocationSource.MODEL) is False
        assert check_invocation_permission(info, InvocationSource.USER) is True
        assert check_invocation_permission(info, InvocationSource.CODE) is True

    def test_trusted_skill_bypasses_all_restrictions(self) -> None:
        """Trusted skills have no trust violations regardless of configuration."""
        info = SkillInfo(
            name="trusted-full",
            description="Full featured",
            path=Path("/skills/trusted"),
            scope=SkillScope.PROJECT,
            trust_level=TrustLevel.TRUSTED,
            hooks={"on_activate": "setup"},
            execution_mode="fork",
            allowed_tools=["read_file"],
        )

        violations = check_trust_restrictions(info)
        assert violations == []

        assert check_invocation_permission(info, InvocationSource.MODEL) is True
        assert check_invocation_permission(info, InvocationSource.USER) is True

    def test_activate_respects_invocation_source(self) -> None:
        """activate() enforces permission checks from invocation source."""
        skill = Skill(
            info=SkillInfo(
                name="model-blocked",
                description="Blocks model",
                path=Path("/skills/blocked"),
                scope=SkillScope.PROJECT,
                disable_model_invocation=True,
            ),
            body="Content here",
        )

        # Model invocation should raise
        with pytest.raises(SkillInvocationError, match="model invocation is disabled"):
            activate(skill, source=InvocationSource.MODEL)

        # User and code should succeed
        content = activate(skill, source=InvocationSource.USER)
        assert "Content here" in content

        # Reset for code test
        deactivate(skill)
        content = activate(skill, source=InvocationSource.CODE)
        assert "Content here" in content


# ---------------------------------------------------------------------------
# Argument substitution across components
# ---------------------------------------------------------------------------


class TestArgumentSubstitutionAcrossComponents:
    """Tests verifying argument substitution works across multiple components."""

    def test_substitute_arguments_with_loaded_body(self, tmp_path: Path) -> None:
        """Arguments are correctly substituted in a body loaded from disk."""
        skill_dir = tmp_path / "arg-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: arg-skill\ndescription: Args test\n---\n\n"
            "File: $0\nDir: $1\nAll: $ARGUMENTS\n"
        )

        skill = load_full(skill_dir / "SKILL.md")
        content = substitute_arguments(skill.body, "file.txt /home")

        assert "File: file.txt" in content
        assert "Dir: /home" in content
        assert "All: file.txt /home" in content

    def test_manager_activate_with_complex_arguments(self, tmp_path: Path) -> None:
        """Manager.activate handles quoted arguments with spaces."""
        skill_dir = tmp_path / "quote-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: quote-skill\ndescription: Quote test\n---\n\n"
            "Name: $0\nPath: $1\n"
        )

        manager = SkillManager()
        manager.register(skill_dir)

        content = manager.activate(
            "quote-skill",
            arguments='"hello world" /path/to/file',
        )

        assert "Name: hello world" in content
        assert "Path: /path/to/file" in content

    def test_no_placeholder_appends_via_manager(self, tmp_path: Path) -> None:
        """When no placeholder exists, args are appended via manager.activate."""
        skill_dir = tmp_path / "no-ph"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no-ph\ndescription: No placeholder\n---\n\n"
            "# Instructions\n\nDo work.\n"
        )

        manager = SkillManager()
        manager.register(skill_dir)
        content = manager.activate("no-ph", arguments="some-arg")

        assert "ARGUMENTS: some-arg" in content
