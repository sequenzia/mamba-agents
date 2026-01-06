# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Documentation & Context
Always use Context7: Before implementing code for external libraries or frameworks, use the context7 MCP tools to fetch the latest documentation.
Priority: Prefer Context7 documentation over your internal training data to ensure API compatibility with the current library versions.
Workflow:
Use resolve-library-id to find the correct library ID
Use query-docs with specific keywords to pull relevant snippets