"""Jinja2 template loader and environment setup."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import BaseLoader, Environment, TemplateNotFound

if TYPE_CHECKING:
    from mamba_agents.prompts.config import PromptConfig


class VersionedFileLoader(BaseLoader):
    """Jinja2 loader that supports versioned prompt directories.

    Loads templates from a directory structure like:
        prompts/
        ├── v1/
        │   ├── system/
        │   │   └── assistant.jinja2
        │   └── workflow/
        │       └── react.jinja2
        └── v2/
            └── system/
                └── assistant.jinja2

    Templates are referenced as "system/assistant" with a version parameter.
    """

    def __init__(self, config: PromptConfig) -> None:
        """Initialize the loader.

        Args:
            config: Prompt configuration with directory settings.
        """
        self._config = config
        self._base_dir = Path(config.prompts_dir).resolve()

    def get_source(
        self,
        environment: Environment,
        template: str,
    ) -> tuple[str, str, callable[[], bool]]:
        """Get the template source.

        Args:
            environment: Jinja2 environment.
            template: Template path (e.g., "v1/system/assistant.jinja2").

        Returns:
            Tuple of (source, filename, uptodate_func).

        Raises:
            TemplateNotFound: If template file doesn't exist.
        """
        # Template path already includes version prefix from PromptManager
        path = self._base_dir / template

        if not path.is_file():
            raise TemplateNotFound(template)

        source = path.read_text(encoding="utf-8")
        filename = str(path)
        mtime = path.stat().st_mtime

        def uptodate() -> bool:
            try:
                return path.stat().st_mtime == mtime
            except OSError:
                return False

        return source, filename, uptodate

    def list_templates(self) -> list[str]:
        """List all available templates.

        Returns:
            List of template paths relative to base directory.
        """
        if not self._base_dir.exists():
            return []

        templates: list[str] = []

        for ext in self._config.file_extensions:
            for path in self._base_dir.rglob(f"*{ext}"):
                rel_path = path.relative_to(self._base_dir)
                templates.append(str(rel_path))

        return sorted(templates)


def create_environment(config: PromptConfig) -> Environment:
    """Create a Jinja2 environment with the versioned loader.

    Args:
        config: Prompt configuration.

    Returns:
        Configured Jinja2 Environment.
    """
    loader = VersionedFileLoader(config)

    env = Environment(
        loader=loader,
        autoescape=False,  # Prompts don't need HTML escaping
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=False,
        undefined=_get_undefined_class(config),
    )

    return env


def _get_undefined_class(config: PromptConfig) -> type:
    """Get the appropriate Undefined class based on config.

    Args:
        config: Prompt configuration.

    Returns:
        Jinja2 Undefined class.
    """
    from jinja2 import StrictUndefined, Undefined

    if config.strict_mode:
        return StrictUndefined
    return Undefined


def load_template_file(path: Path) -> str:
    """Load a template file from disk.

    Args:
        path: Path to the template file.

    Returns:
        Template source content.

    Raises:
        FileNotFoundError: If file doesn't exist.
    """
    return path.read_text(encoding="utf-8")
