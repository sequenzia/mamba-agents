"""Prompt manager for loading and rendering templates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from mamba_agents.prompts.config import PromptConfig, TemplateConfig
from mamba_agents.prompts.errors import PromptNotFoundError, TemplateConflictError
from mamba_agents.prompts.loader import create_environment
from mamba_agents.prompts.template import PromptTemplate, TemplateType

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

    def _get_template_path(self, name: str, version: str, ext: str | None = None) -> str:
        """Build the full template path.

        Args:
            name: Template name (e.g., "system/assistant").
            version: Template version (e.g., "v1").
            ext: File extension. Uses primary extension if not specified.

        Returns:
            Full path relative to prompts directory.
        """
        if ext is None:
            ext = self._config.file_extension
        return f"{version}/{name}{ext}"

    def _resolve_template_path(self, name: str, version: str) -> tuple[Path, str]:
        """Resolve the template file path, checking all extensions.

        Args:
            name: Template name (e.g., "system/assistant").
            version: Template version (e.g., "v1").

        Returns:
            Tuple of (absolute path, file extension).

        Raises:
            PromptNotFoundError: If no template file exists.
            TemplateConflictError: If multiple files exist for same template.
        """
        base_dir = Path(self._config.prompts_dir).resolve()
        found: list[tuple[Path, str]] = []

        for ext in self._config.file_extensions:
            path = base_dir / version / f"{name}{ext}"
            if path.is_file():
                found.append((path, ext))

        if len(found) > 1:
            raise TemplateConflictError(name, version, [ext for _, ext in found])

        if not found:
            raise PromptNotFoundError(name, version)

        return found[0]

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
            TemplateConflictError: If multiple template files exist.
        """
        # Resolve the template path (handles conflict detection)
        path, ext = self._resolve_template_path(name, version)

        # Read the file content
        source = path.read_text(encoding="utf-8")

        # Handle markdown templates
        if ext == ".md":
            return self._load_markdown_template(name, version, source)

        # Handle Jinja2 templates
        return self._load_jinja2_template(name, version, source, ext)

    def _load_jinja2_template(
        self, name: str, version: str, source: str, ext: str
    ) -> PromptTemplate:
        """Load a Jinja2 template.

        Args:
            name: Template name.
            version: Template version.
            source: Template source content.
            ext: File extension.

        Returns:
            PromptTemplate configured for Jinja2.
        """
        from jinja2 import TemplateNotFound

        template_path = self._get_template_path(name, version, ext)

        try:
            env = self._get_env()
            jinja_template = env.get_template(template_path)
        except TemplateNotFound as e:
            raise PromptNotFoundError(name, version) from e

        return PromptTemplate(
            name=name,
            version=version,
            source=source,
            template_type=TemplateType.JINJA2,
            _compiled=jinja_template,
        )

    def _load_markdown_template(self, name: str, version: str, source: str) -> PromptTemplate:
        """Load a markdown template with YAML frontmatter.

        Args:
            name: Template name.
            version: Template version.
            source: Template source content.

        Returns:
            PromptTemplate configured for markdown.
        """
        from mamba_agents.prompts.markdown import parse_markdown_prompt

        data = parse_markdown_prompt(source, name)

        return PromptTemplate(
            name=name,
            version=version,
            source=data.content,
            template_type=TemplateType.MARKDOWN,
            _default_variables=data.default_variables,
            _strict=self._config.strict_mode,
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
            List of template names (deduplicated across extensions).
        """
        prompts: set[str] = set()

        # Add registered templates
        for name in self._registered:
            if category is None or name.startswith(f"{category}/"):
                prompts.add(name)

        # Add file-based templates (scan all extensions)
        base_dir = Path(self._config.prompts_dir)
        if base_dir.exists():
            for version_dir in base_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                for ext in self._config.file_extensions:
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

        # Check file-based versions (all extensions)
        base_dir = Path(self._config.prompts_dir)
        if base_dir.exists():
            for version_dir in base_dir.iterdir():
                if not version_dir.is_dir():
                    continue
                for ext in self._config.file_extensions:
                    template_path = version_dir / f"{name}{ext}"
                    if template_path.is_file():
                        versions.add(version_dir.name)
                        break  # Found in this version, no need to check other extensions

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

        # Check file system (any extension)
        base_dir = Path(self._config.prompts_dir)
        for ext in self._config.file_extensions:
            template_path = base_dir / version / f"{name}{ext}"
            if template_path.is_file():
                return True

        return False
