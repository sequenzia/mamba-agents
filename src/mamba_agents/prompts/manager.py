"""Prompt manager for loading and rendering templates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from mamba_agents.prompts.config import PromptConfig, TemplateConfig
from mamba_agents.prompts.errors import PromptNotFoundError
from mamba_agents.prompts.loader import create_environment
from mamba_agents.prompts.template import PromptTemplate

if TYPE_CHECKING:
    from jinja2 import Environment


class PromptManager:
    """Manages prompt templates and rendering.

    The PromptManager handles loading templates from files, caching,
    and rendering with variables. It supports versioned templates
    and runtime registration for testing.

    Example:
        >>> manager = PromptManager()
        >>> template = manager.get("system/assistant")
        >>> prompt = template.render(name="Code Helper")

        >>> # Or render directly
        >>> prompt = manager.render("system/assistant", name="Code Helper")

        >>> # Register a test template
        >>> manager.register("test/greeting", "Hello, {{ name }}!")
        >>> manager.render("test/greeting", name="World")
        'Hello, World!'
    """

    def __init__(self, config: PromptConfig | None = None) -> None:
        """Initialize the prompt manager.

        Args:
            config: Prompt configuration. Uses defaults if not provided.
        """
        self._config = config or PromptConfig()
        self._env: Environment | None = None
        self._cache: dict[str, PromptTemplate] = {}
        self._registered: dict[str, dict[str, PromptTemplate]] = {}

    @property
    def config(self) -> PromptConfig:
        """Get the prompt configuration."""
        return self._config

    def _get_env(self) -> Environment:
        """Get or create the Jinja2 environment.

        Returns:
            Configured Jinja2 Environment.
        """
        if self._env is None:
            self._env = create_environment(self._config)
        return self._env

    def _get_template_path(self, name: str, version: str) -> str:
        """Build the full template path.

        Args:
            name: Template name (e.g., "system/assistant").
            version: Template version (e.g., "v1").

        Returns:
            Full path relative to prompts directory.
        """
        ext = self._config.file_extension
        return f"{version}/{name}{ext}"

    def get(
        self,
        name: str,
        version: str | None = None,
    ) -> PromptTemplate:
        """Get a template by name.

        Args:
            name: Template name (e.g., "system/assistant").
            version: Template version. Uses default if not specified.

        Returns:
            PromptTemplate instance.

        Raises:
            PromptNotFoundError: If template doesn't exist.
        """
        version = version or self._config.default_version

        # Check registered templates first (for testing)
        if name in self._registered and version in self._registered[name]:
            return self._registered[name][version]

        # Check cache
        cache_key = f"{version}/{name}"
        if self._config.enable_caching and cache_key in self._cache:
            return self._cache[cache_key]

        # Load from file
        template = self._load_template(name, version)

        # Cache if enabled
        if self._config.enable_caching:
            self._cache[cache_key] = template

        return template

    def _load_template(self, name: str, version: str) -> PromptTemplate:
        """Load a template from the filesystem.

        Args:
            name: Template name.
            version: Template version.

        Returns:
            Loaded PromptTemplate.

        Raises:
            PromptNotFoundError: If template file doesn't exist.
        """
        from jinja2 import TemplateNotFound

        template_path = self._get_template_path(name, version)

        try:
            env = self._get_env()
            jinja_template = env.get_template(template_path)
            # Get source from the loader
            source, _, _ = env.loader.get_source(env, template_path)
        except TemplateNotFound as e:
            raise PromptNotFoundError(name, version) from e

        return PromptTemplate(
            name=name,
            version=version,
            source=source,
            _compiled=jinja_template,
        )

    def render(
        self,
        template_name: str,
        version: str | None = None,
        **variables: Any,
    ) -> str:
        """Render a template with variables.

        Args:
            template_name: Template name (e.g., "system/assistant").
            version: Template version. Uses default if not specified.
            **variables: Variables to substitute in the template.

        Returns:
            Rendered template string.

        Raises:
            PromptNotFoundError: If template doesn't exist.
            TemplateRenderError: If rendering fails.
        """
        template = self.get(template_name, version)
        return template.render(**variables)

    def render_config(self, config: TemplateConfig) -> str:
        """Render a template from a TemplateConfig.

        Args:
            config: Template configuration with name, version, and variables.

        Returns:
            Rendered template string.

        Raises:
            PromptNotFoundError: If template doesn't exist.
            TemplateRenderError: If rendering fails.
        """
        return self.render(
            template_name=config.name,
            version=config.version,
            **config.variables,
        )

    def register(
        self,
        name: str,
        template: str | PromptTemplate,
        version: str | None = None,
    ) -> None:
        """Register a template programmatically.

        This is useful for testing or dynamic template creation.

        Args:
            name: Template name (e.g., "test/greeting").
            template: Template source string or PromptTemplate instance.
            version: Template version. Uses default if not specified.

        Example:
            >>> manager = PromptManager()
            >>> manager.register("test/hello", "Hello, {{ name }}!")
            >>> manager.render("test/hello", name="World")
            'Hello, World!'
        """
        version = version or self._config.default_version

        if isinstance(template, str):
            template = PromptTemplate(
                name=name,
                version=version,
                source=template,
            )

        if name not in self._registered:
            self._registered[name] = {}
        self._registered[name][version] = template

    def list_prompts(self, category: str | None = None) -> list[str]:
        """List available prompt templates.

        Args:
            category: Optional category filter (e.g., "system", "workflow").

        Returns:
            List of template names.
        """
        prompts: set[str] = set()

        # Add registered templates
        for name in self._registered:
            if category is None or name.startswith(f"{category}/"):
                prompts.add(name)

        # Add file-based templates
        base_dir = Path(self._config.prompts_dir)
        if base_dir.exists():
            ext = self._config.file_extension
            for version_dir in base_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                for path in version_dir.rglob(f"*{ext}"):
                    rel_path = path.relative_to(version_dir)
                    name = str(rel_path.with_suffix(""))
                    if category is None or name.startswith(f"{category}/"):
                        prompts.add(name)

        return sorted(prompts)

    def list_versions(self, name: str) -> list[str]:
        """List available versions for a template.

        Args:
            name: Template name (e.g., "system/assistant").

        Returns:
            List of version strings.
        """
        versions: set[str] = set()

        # Check registered versions
        if name in self._registered:
            versions.update(self._registered[name].keys())

        # Check file-based versions
        base_dir = Path(self._config.prompts_dir)
        if base_dir.exists():
            ext = self._config.file_extension
            for version_dir in base_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                template_path = version_dir / f"{name}{ext}"
                if template_path.is_file():
                    versions.add(version_dir.name)

        return sorted(versions)

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()
        self._env = None

    def exists(self, name: str, version: str | None = None) -> bool:
        """Check if a template exists.

        Args:
            name: Template name.
            version: Template version. Uses default if not specified.

        Returns:
            True if template exists, False otherwise.
        """
        version = version or self._config.default_version

        # Check registered templates
        if name in self._registered and version in self._registered[name]:
            return True

        # Check file system
        base_dir = Path(self._config.prompts_dir)
        ext = self._config.file_extension
        template_path = base_dir / version / f"{name}{ext}"

        return template_path.is_file()
