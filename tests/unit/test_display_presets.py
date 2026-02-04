"""Tests for the display module preset system and MessageRenderer protocol."""

from __future__ import annotations

import pytest

from mamba_agents.agent.display import (
    COMPACT,
    DETAILED,
    VERBOSE,
    DisplayPreset,
    MessageRenderer,
    get_preset,
)
from mamba_agents.agent.messages import MessageStats, ToolCallInfo, Turn


class TestDisplayPreset:
    """Tests for the DisplayPreset dataclass."""

    def test_default_values(self) -> None:
        """Test that default construction produces the detailed preset values."""
        preset = DisplayPreset()

        assert preset.show_tokens is True
        assert preset.max_content_length == 300
        assert preset.expand is False
        assert preset.show_tool_details is False
        assert preset.max_tool_arg_length == 200
        assert preset.limit is None

    def test_custom_construction(self) -> None:
        """Test constructing a preset with all custom values."""
        preset = DisplayPreset(
            show_tokens=False,
            max_content_length=500,
            expand=True,
            show_tool_details=True,
            max_tool_arg_length=100,
            limit=10,
        )

        assert preset.show_tokens is False
        assert preset.max_content_length == 500
        assert preset.expand is True
        assert preset.show_tool_details is True
        assert preset.max_tool_arg_length == 100
        assert preset.limit == 10

    def test_frozen_immutability(self) -> None:
        """Test that preset fields cannot be modified after creation."""
        preset = DisplayPreset()

        with pytest.raises(AttributeError):
            preset.show_tokens = False  # type: ignore[misc]


class TestNamedPresets:
    """Tests for the three named preset constants."""

    def test_compact_preset_values(self) -> None:
        """Test that compact preset has minimal-output values."""
        assert COMPACT.show_tokens is False
        assert COMPACT.max_content_length == 100
        assert COMPACT.expand is False
        assert COMPACT.show_tool_details is False
        assert COMPACT.max_tool_arg_length == 50
        assert COMPACT.limit is None

    def test_detailed_preset_values(self) -> None:
        """Test that detailed preset has balanced values."""
        assert DETAILED.show_tokens is True
        assert DETAILED.max_content_length == 300
        assert DETAILED.expand is False
        assert DETAILED.show_tool_details is False
        assert DETAILED.max_tool_arg_length == 200
        assert DETAILED.limit is None

    def test_verbose_preset_values(self) -> None:
        """Test that verbose preset has maximum-detail values."""
        assert VERBOSE.show_tokens is True
        assert VERBOSE.max_content_length is None
        assert VERBOSE.expand is True
        assert VERBOSE.show_tool_details is True
        assert VERBOSE.max_tool_arg_length == 500
        assert VERBOSE.limit is None

    def test_presets_are_distinct_instances(self) -> None:
        """Test that the three named presets are separate objects."""
        assert COMPACT is not DETAILED
        assert DETAILED is not VERBOSE
        assert COMPACT is not VERBOSE


class TestGetPreset:
    """Tests for the get_preset factory function."""

    def test_get_compact(self) -> None:
        """Test retrieving the compact preset by name."""
        preset = get_preset("compact")
        assert preset == COMPACT

    def test_get_detailed(self) -> None:
        """Test retrieving the detailed preset by name."""
        preset = get_preset("detailed")
        assert preset == DETAILED

    def test_get_verbose(self) -> None:
        """Test retrieving the verbose preset by name."""
        preset = get_preset("verbose")
        assert preset == VERBOSE

    def test_default_is_detailed(self) -> None:
        """Test that calling get_preset with no arguments returns detailed."""
        preset = get_preset()
        assert preset == DETAILED

    def test_invalid_name_raises_value_error(self) -> None:
        """Test that an invalid preset name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset name: 'bogus'"):
            get_preset("bogus")

    def test_invalid_name_error_lists_valid_presets(self) -> None:
        """Test that the error message includes the valid preset names."""
        with pytest.raises(ValueError, match="compact") as exc_info:
            get_preset("invalid")

        error_msg = str(exc_info.value)
        assert "compact" in error_msg
        assert "detailed" in error_msg
        assert "verbose" in error_msg

    def test_override_single_field(self) -> None:
        """Test overriding a single field on a named preset."""
        preset = get_preset("compact", show_tokens=True)

        # Overridden field takes the explicit value.
        assert preset.show_tokens is True
        # Other fields retain the compact defaults.
        assert preset.max_content_length == 100
        assert preset.expand is False
        assert preset.show_tool_details is False

    def test_override_multiple_fields(self) -> None:
        """Test overriding multiple fields on a named preset."""
        preset = get_preset("detailed", expand=True, limit=50)

        assert preset.expand is True
        assert preset.limit == 50
        # Non-overridden fields retain detailed defaults.
        assert preset.show_tokens is True
        assert preset.max_content_length == 300

    def test_override_takes_precedence_over_preset(self) -> None:
        """Test that explicit overrides beat the preset's default values."""
        # compact has show_tool_details=False; override to True
        preset = get_preset("compact", show_tool_details=True)
        assert preset.show_tool_details is True

        # verbose has expand=True; override to False
        preset = get_preset("verbose", expand=False)
        assert preset.expand is False

    def test_no_overrides_returns_original_preset(self) -> None:
        """Test that no overrides returns the exact named preset object."""
        preset = get_preset("compact")
        assert preset is COMPACT

    def test_override_returns_new_instance(self) -> None:
        """Test that overriding creates a new preset, leaving the original unchanged."""
        original = get_preset("compact")
        overridden = get_preset("compact", show_tokens=True)

        assert overridden is not original
        assert original.show_tokens is False  # unchanged
        assert overridden.show_tokens is True


class TestMessageRendererProtocol:
    """Tests for the MessageRenderer ABC definition."""

    def test_cannot_instantiate_directly(self) -> None:
        """Test that MessageRenderer cannot be instantiated without implementing methods."""
        with pytest.raises(TypeError):
            MessageRenderer()  # type: ignore[abstract]

    def test_concrete_implementation(self) -> None:
        """Test that a concrete implementation satisfying the ABC can be instantiated."""

        class StubRenderer(MessageRenderer):
            def render_stats(self, stats: MessageStats, preset: DisplayPreset) -> str:
                return "stats"

            def render_timeline(self, turns: list[Turn], preset: DisplayPreset) -> str:
                return "timeline"

            def render_tools(self, tools: list[ToolCallInfo], preset: DisplayPreset) -> str:
                return "tools"

        renderer = StubRenderer()
        assert isinstance(renderer, MessageRenderer)

    def test_render_stats_method_exists(self) -> None:
        """Test that render_stats is defined as an abstract method."""
        assert hasattr(MessageRenderer, "render_stats")
        assert getattr(MessageRenderer.render_stats, "__isabstractmethod__", False)

    def test_render_timeline_method_exists(self) -> None:
        """Test that render_timeline is defined as an abstract method."""
        assert hasattr(MessageRenderer, "render_timeline")
        assert getattr(MessageRenderer.render_timeline, "__isabstractmethod__", False)

    def test_render_tools_method_exists(self) -> None:
        """Test that render_tools is defined as an abstract method."""
        assert hasattr(MessageRenderer, "render_tools")
        assert getattr(MessageRenderer.render_tools, "__isabstractmethod__", False)

    def test_partial_implementation_raises_type_error(self) -> None:
        """Test that implementing only some methods still raises TypeError."""

        class PartialRenderer(MessageRenderer):
            def render_stats(self, stats: MessageStats, preset: DisplayPreset) -> str:
                return "stats"

        with pytest.raises(TypeError):
            PartialRenderer()  # type: ignore[abstract]

    def test_stub_renderer_produces_output(self) -> None:
        """Test that a stub renderer can render data and return strings."""

        class StubRenderer(MessageRenderer):
            def render_stats(self, stats: MessageStats, preset: DisplayPreset) -> str:
                return f"messages={stats.total_messages}"

            def render_timeline(self, turns: list[Turn], preset: DisplayPreset) -> str:
                return f"turns={len(turns)}"

            def render_tools(self, tools: list[ToolCallInfo], preset: DisplayPreset) -> str:
                return f"tools={len(tools)}"

        renderer = StubRenderer()
        stats = MessageStats(total_messages=5)
        turns = [Turn(index=0), Turn(index=1)]
        tools = [ToolCallInfo(tool_name="search", call_count=3)]

        assert renderer.render_stats(stats, DETAILED) == "messages=5"
        assert renderer.render_timeline(turns, DETAILED) == "turns=2"
        assert renderer.render_tools(tools, DETAILED) == "tools=1"

    def test_is_subclass_of_abc(self) -> None:
        """Test that MessageRenderer is an ABC."""
        from abc import ABC

        assert issubclass(MessageRenderer, ABC)
