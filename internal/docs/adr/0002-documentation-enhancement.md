# ADR-0002: Documentation Enhancement with Examples Directory

**Date:** 2026-01-22
**Status:** Accepted
**Feature:** Documentation improvement and examples directory

## Context

The mamba-agents documentation needs improvement to better serve users and contributors:

1. **Outdated content:** v0.1.2 and v0.1.3 features are not fully documented
   - Streamable HTTP transport (v0.1.3) missing from README and MCP docs
   - Connection testing methods not documented
   - graceful_tool_errors feature needs better visibility
   - Architecture diagrams show only "stdio & SSE"

2. **Missing examples:** No standalone `examples/` directory
   - Users must look at tests or README for runnable code
   - No hands-on learning path for new users

3. **Sparse docstrings:** Module `__init__.py` files have minimal documentation
   - Poor IDE discoverability
   - No usage examples in docstrings

Target audiences:
- New users getting started
- Existing users upgrading
- Contributors to the project

## Decision

We will implement a comprehensive documentation enhancement:

1. **Create `examples/` directory** with runnable Python scripts organized by feature:
   - basic/ - Getting started examples
   - tools/ - Tool usage and graceful errors
   - mcp/ - MCP integration including v0.1.3 features
   - workflows/ - ReAct and custom workflows
   - advanced/ - Context compaction, local models, etc.

2. **Update existing documentation** to cover v0.1.2/v0.1.3 features:
   - Add Streamable HTTP transport to README and MCP docs
   - Add connection testing documentation
   - Update architecture diagrams
   - Add `[prompts]` section to config.example.toml

3. **Enhance module docstrings** with usage examples and cross-references:
   - mamba_agents/__init__.py
   - mamba_agents/agent/__init__.py
   - mamba_agents/mcp/__init__.py
   - mamba_agents/tools/__init__.py
   - mamba_agents/context/__init__.py
   - mamba_agents/tokens/__init__.py
   - mamba_agents/backends/__init__.py

## Consequences

### Positive
- Better onboarding for new users via runnable examples
- Improved IDE discoverability through enhanced docstrings
- Documentation accuracy for v0.1.2/v0.1.3 features
- Clear learning path: examples -> docs -> API reference

### Negative
- More files to maintain (examples directory)
- Risk of examples becoming stale with API changes
- Larger repo size

### Risks
- Examples may become outdated: Mitigated by linking examples in tests or CI syntax checks
- Inconsistent docstring style: Mitigated by following existing Google-style conventions
- Examples require API keys: Mitigated by clear prerequisites in examples/README.md

## Alternatives Considered

### Alternative 1: Minimal fixes only
Fix only the outdated v0.1.2/v0.1.3 content in existing files.
- **Pros:** Faster, less maintenance burden
- **Cons:** Doesn't address examples gap or docstring discoverability
- **Why rejected:** User expressed desire for examples directory and all-audience coverage

### Alternative 2: Generate examples from tests
Extract test code into examples automatically.
- **Pros:** Always in sync with codebase
- **Cons:** Test code isn't optimized for learning, complex setup
- **Why rejected:** Hand-crafted examples are more pedagogical

## Implementation Notes

**New files to create (11):**
- examples/README.md - Index
- examples/basic/__init__.py, basic_agent.py, multi_turn.py
- examples/tools/__init__.py, graceful_errors.py
- examples/mcp/__init__.py, mcp_connection_test.py, mcp_http.py
- examples/workflows/__init__.py
- examples/advanced/__init__.py

**Files to modify (11):**
- src/mamba_agents/__init__.py
- src/mamba_agents/agent/__init__.py
- src/mamba_agents/mcp/__init__.py
- src/mamba_agents/tools/__init__.py
- src/mamba_agents/context/__init__.py
- src/mamba_agents/tokens/__init__.py
- src/mamba_agents/backends/__init__.py
- README.md
- docs/user-guide/mcp-integration.md
- docs/api/mcp/client.md
- config.example.toml

**Key patterns:**
- Examples include shebang and module docstring explaining prerequisites
- Module docstrings follow Google style with Example sections
- Cross-references point to examples/ directory and docs

## References

- [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- pydantic-ai documentation patterns
