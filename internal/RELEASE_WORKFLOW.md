# Release Workflow

This document describes the build, release, and deployment processes for the mamba-agents project.

## Overview

The project uses a fully automated CI/CD pipeline:

```
Git Tag (v0.1.0) → Build → TestPyPI → PyPI → GitHub Release
```

**Key technologies:**
- **Build system:** hatchling + hatch-vcs
- **Package manager:** uv
- **CI/CD:** GitHub Actions
- **Publishing:** OIDC Trusted Publishing (no API tokens)

---

## Version Management

Versions are derived automatically from git tags using [hatch-vcs](https://github.com/ofek/hatch-vcs).

### Configuration

From `pyproject.toml`:

```toml
[project]
dynamic = ["version"]  # Version is dynamic, not hardcoded

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"

[tool.hatch.version.raw-options]
version_scheme = "python-simplified-semver"
local_scheme = "no-local-version"

[tool.hatch.build.hooks.vcs]
version-file = "src/mamba_agents/_version.py"
```

### How It Works

| Scenario | Version |
|----------|---------|
| Tag `v0.1.0` | `0.1.0` |
| 3 commits after `v0.1.0` | `0.1.1.dev3` |
| Tag `v1.2.3` | `1.2.3` |

The version file `src/mamba_agents/_version.py` is auto-generated during build and is `.gitignored`.

### Accessing Version in Code

```python
from mamba_agents import __version__
print(__version__)  # e.g., "0.1.0" or "0.1.1.dev3"
```

---

## CI Pipeline

**File:** `.github/workflows/ci.yml`

**Triggers:**
- Push to `main` branch
- Pull requests targeting `main`

### Jobs

```
┌─────────┐     ┌─────────┐
│  Lint   │     │  Test   │  (run in parallel)
└────┬────┘     └────┬────┘
     │               │
     └───────┬───────┘
             ▼
        ┌─────────┐
        │  Build  │  (runs after lint + test pass)
        └─────────┘
```

#### 1. Lint Job

- Python 3.12
- Checks code formatting: `uv run ruff format --check`
- Runs linter: `uv run ruff check`

#### 2. Test Job (Matrix)

- Runs on Python **3.12** and **3.13**
- Executes: `uv run pytest --cov=mamba_agents --cov-report=xml`
- Uploads coverage to Codecov (Python 3.12 only)
- Coverage threshold: 50% minimum

#### 3. Build Job

- Depends on lint and test jobs
- Uses `fetch-depth: 0` (required for hatch-vcs)
- Runs: `uv build`
- Uploads artifacts to GitHub

---

## Release Pipeline

**File:** `.github/workflows/release.yml`

**Trigger:** Push of tags matching `v*` (e.g., `v0.1.0`, `v1.2.3`)

### Jobs

```
┌─────────┐
│  Build  │
└────┬────┘
     ▼
┌──────────────────┐
│ Publish TestPyPI │  (validates packaging)
└────────┬─────────┘
         ▼
┌──────────────────┐
│  Publish PyPI    │  (production release)
└────────┬─────────┘
         ▼
┌──────────────────┐
│ GitHub Release   │  (creates release with artifacts)
└──────────────────┘
```

#### 1. Build Job

- Checks out code with full history (`fetch-depth: 0`)
- Builds package: `uv build`
- Produces:
  - `dist/mamba_agents-X.Y.Z-py3-none-any.whl`
  - `dist/mamba_agents-X.Y.Z.tar.gz`
- Uploads artifacts for subsequent jobs

#### 2. Publish to TestPyPI

- **Environment:** `testpypi`
- **Permissions:** `id-token: write` (for OIDC)
- Downloads build artifacts
- Publishes to `https://test.pypi.org/legacy/`
- Purpose: Validates packaging before production

#### 3. Publish to PyPI

- **Environment:** `pypi`
- **Permissions:** `id-token: write` (for OIDC)
- Downloads build artifacts
- Publishes to PyPI production

#### 4. GitHub Release

- **Permissions:** `contents: write`
- Downloads build artifacts
- Creates GitHub Release with:
  - Tag name as release title
  - Auto-generated release notes
  - Attached wheel and sdist files

---

## OIDC Trusted Publishing

This project uses [OIDC Trusted Publishing](https://docs.pypi.org/trusted-publishers/) instead of API tokens.

### Benefits

- No long-lived API tokens to store or rotate
- GitHub-issued tokens are short-lived and scoped
- Better security posture
- Automatic revocation

### Setup Requirements

#### GitHub Repository Settings

Create two environments in **Settings → Environments**:

1. **`testpypi`**
   - Deployment branches: `main`
   - No secrets required (OIDC handles auth)

2. **`pypi`**
   - Deployment branches: `main`
   - No secrets required (OIDC handles auth)

#### PyPI Configuration

For each environment (TestPyPI and PyPI):

1. Go to your project on PyPI/TestPyPI
2. Navigate to **Publishing → Add a new publisher**
3. Configure the trusted publisher:
   - **Owner:** `sequenzia`
   - **Repository:** `mamba-agents`
   - **Workflow name:** `release.yml`
   - **Environment:** `testpypi` or `pypi`

---

## Creating a Release

### Prerequisites

1. All changes merged to `main`
2. CI passing on `main` branch
3. `CHANGELOG.md` updated with release notes

### Release Checklist

```bash
# 1. Ensure you're on main and up to date
git checkout main
git pull origin main

# 2. Verify tests pass locally
uv run pytest --cov=mamba_agents

# 3. Verify lint passes
uv run ruff check
uv run ruff format --check

# 4. Verify build succeeds
uv build

# 5. Update CHANGELOG.md
# - Move items from [Unreleased] to new version section
# - Add release date
# - Update comparison links

# 6. Commit changelog update
git add CHANGELOG.md
git commit -m "docs: update changelog for v0.2.0"
git push origin main

# 7. Create annotated tag
git tag -a v0.2.0 -m "Release v0.2.0"

# 8. Push tag (triggers release workflow)
git push origin v0.2.0
```

### Post-Release

1. Monitor the [Actions tab](https://github.com/sequenzia/mamba-agents/actions) for workflow progress
2. Verify package on [TestPyPI](https://test.pypi.org/project/mamba-agents/)
3. Verify package on [PyPI](https://pypi.org/project/mamba-agents/)
4. Check the [GitHub Releases](https://github.com/sequenzia/mamba-agents/releases) page

---

## Changelog Format

The project follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

**File:** `CHANGELOG.md`

### Structure

```markdown
# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- New features go here during development

## [0.2.0] - 2025-01-25

### Added
- Feature X
- Feature Y

### Changed
- Modified behavior Z

### Fixed
- Bug fix A

## [0.1.0] - 2025-01-20

### Added
- Initial release

[Unreleased]: https://github.com/sequenzia/mamba-agents/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/sequenzia/mamba-agents/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sequenzia/mamba-agents/releases/tag/v0.1.0
```

### Categories

- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Features to be removed
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Security fixes

---

## Troubleshooting

### Version shows `0.0.0` or incorrect version

**Cause:** Shallow clone missing git history.

**Solution:** Ensure `fetch-depth: 0` in checkout step:
```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
```

### TestPyPI publish fails with 403

**Cause:** OIDC trusted publisher not configured.

**Solution:**
1. Go to TestPyPI project settings
2. Add trusted publisher with correct repository and workflow details

### PyPI publish fails after TestPyPI succeeds

**Cause:** Package with same version already exists on PyPI.

**Solution:** You cannot overwrite existing versions. Create a new version tag.

### GitHub Release not created

**Cause:** Missing `contents: write` permission.

**Solution:** Ensure the job has:
```yaml
permissions:
  contents: write
```

### Build fails locally but passes in CI

**Cause:** Missing `_version.py` file.

**Solution:** The version file is auto-generated. Run `uv build` to create it, or use:
```bash
uv run python -c "from mamba_agents import __version__; print(__version__)"
```

---

## Related Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline configuration |
| `.github/workflows/release.yml` | Release workflow |
| `pyproject.toml` | Build and project configuration |
| `CHANGELOG.md` | Release history |
| `src/mamba_agents/_version.py` | Auto-generated version file |
