"""Display module for formatted message rendering.

Provides the renderer abstraction, preset configuration, named preset
instances, concrete renderer implementations, and standalone helper
functions for controlling how message analytics data is rendered.

Public API:
    MessageRenderer: ABC for format-specific renderers.
    RichRenderer: Concrete renderer producing Rich Console output.
    PlainTextRenderer: Concrete renderer producing ASCII text output.
    HtmlRenderer: Concrete renderer producing HTML string output.
    DisplayPreset: Dataclass controlling display detail level.
    get_preset: Factory function to retrieve named presets with overrides.
    print_stats: Standalone function to render message statistics.
    print_timeline: Standalone function to render conversation timeline.
    print_tools: Standalone function to render tool usage summary.
    COMPACT: Minimal preset -- counts only, short truncation.
    DETAILED: Balanced preset -- full tables, moderate truncation.
    VERBOSE: Maximum preset -- expanded content, full tool details.
"""

from mamba_agents.agent.display.functions import (
    print_stats,
    print_timeline,
    print_tools,
)
from mamba_agents.agent.display.html_renderer import HtmlRenderer
from mamba_agents.agent.display.plain_renderer import PlainTextRenderer
from mamba_agents.agent.display.presets import (
    COMPACT,
    DETAILED,
    VERBOSE,
    DisplayPreset,
    get_preset,
)
from mamba_agents.agent.display.renderer import MessageRenderer
from mamba_agents.agent.display.rich_renderer import RichRenderer

__all__ = [
    "COMPACT",
    "DETAILED",
    "VERBOSE",
    "DisplayPreset",
    "HtmlRenderer",
    "MessageRenderer",
    "PlainTextRenderer",
    "RichRenderer",
    "get_preset",
    "print_stats",
    "print_timeline",
    "print_tools",
]
