#!/usr/bin/env python3
"""Prompt template management example.

This example demonstrates:
- Using string prompts (backward compatible)
- Using TemplateConfig for file-based templates
- Standalone PromptManager usage
- Template inheritance with Jinja2

Prerequisites:
- Set OPENAI_API_KEY environment variable
"""

import os
import tempfile
from pathlib import Path

from mamba_agents import Agent
from mamba_agents.prompts import PromptConfig, PromptManager, TemplateConfig


def string_prompt_example():
    """Basic string prompt (backward compatible)."""
    print("--- String Prompt Example ---\n")

    if not os.environ.get("OPENAI_API_KEY"):
        print("Skipping (no API key)")
        return

    agent = Agent("gpt-4o-mini", system_prompt="You are a helpful Python expert.")
    result = agent.run_sync("What's a list comprehension?")
    print(f"Response: {result.output[:100]}...")


def standalone_manager_example():
    """Standalone PromptManager usage."""
    print("\n--- Standalone PromptManager Example ---\n")

    manager = PromptManager()

    # Register templates programmatically
    manager.register("greeting", "Hello, {{ name }}! Welcome to {{ place }}.")
    manager.register(
        "code_review",
        """
You are reviewing {{ language }} code.
Focus on: {{ focus | default("readability and best practices") }}.
""".strip(),
    )

    # Render templates
    greeting = manager.render("greeting", name="Alice", place="Python land")
    print(f"Greeting: {greeting}")

    review_prompt = manager.render("code_review", language="Python", focus="security")
    print(f"Review prompt: {review_prompt}")


def file_based_templates_example():
    """File-based templates with directory structure."""
    print("\n--- File-Based Templates Example ---\n")

    # Create temporary prompts directory
    with tempfile.TemporaryDirectory() as tmpdir:
        prompts_dir = Path(tmpdir) / "prompts"

        # Create directory structure
        (prompts_dir / "v1" / "system").mkdir(parents=True)
        (prompts_dir / "v1" / "base").mkdir(parents=True)

        # Create base template
        base_template = """{% block persona %}You are a helpful assistant.{% endblock %}

{% block instructions %}{% endblock %}

{% block constraints %}{% endblock %}"""
        (prompts_dir / "v1" / "base" / "base.jinja2").write_text(base_template)

        # Create child template that extends base
        coder_template = """{% extends "v1/base/base.jinja2" %}

{% block persona %}
You are an expert {{ language | default("Python") }} developer.
{% endblock %}

{% block instructions %}
Help the user write clean, efficient code.
Focus on {{ focus | default("best practices") }}.
{% endblock %}"""
        (prompts_dir / "v1" / "system" / "coder.jinja2").write_text(coder_template)

        # Configure PromptManager
        config = PromptConfig(
            prompts_dir=str(prompts_dir),
            default_version="v1",
            enable_caching=True,
        )
        manager = PromptManager(config)

        # Render template
        prompt = manager.render("system/coder", language="Python", focus="security")
        print(f"Rendered prompt:\n{prompt}")

        # List available templates
        templates = manager.list_prompts()
        print(f"\nAvailable templates: {templates}")


def template_config_example():
    """Using TemplateConfig with agents."""
    print("\n--- TemplateConfig Example ---\n")

    # This would load from file: prompts/v1/system/assistant.jinja2
    # config = TemplateConfig(
    #     name="system/assistant",
    #     version="v1",
    #     variables={"name": "CodeBot", "expertise": "Python"}
    # )
    # agent = Agent("gpt-4o", system_prompt=config)

    print("Using TemplateConfig with Agent:")
    print("  config = TemplateConfig(")
    print('      name="system/assistant",')
    print('      version="v1",')
    print('      variables={"name": "CodeBot"}')
    print("  )")
    print('  agent = Agent("gpt-4o", system_prompt=config)')


def main():
    string_prompt_example()
    standalone_manager_example()
    file_based_templates_example()
    template_config_example()


if __name__ == "__main__":
    main()
