"""Tests for UsageTracker subagent token aggregation."""

from __future__ import annotations

from unittest.mock import MagicMock

from mamba_agents.tokens.tracker import UsageRecord, UsageTracker


def _make_usage(
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int | None = None,
) -> MagicMock:
    """Create a mock pydantic-ai Usage object."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.total_tokens = total_tokens if total_tokens is not None else input_tokens + output_tokens
    return usage


class TestRecordUsageWithSource:
    """Tests for record_usage() with source tag."""

    def test_record_usage_with_source_tags_record(self) -> None:
        """record_usage(usage, source='subagent-name') tags usage with source."""
        tracker = UsageTracker()
        usage = _make_usage(input_tokens=100, output_tokens=50)

        tracker.record_usage(usage, source="researcher")

        records = tracker.get_usage_history()
        assert len(records) == 1
        assert records[0].source == "researcher"
        assert records[0].prompt_tokens == 100
        assert records[0].completion_tokens == 50
        assert records[0].total_tokens == 150

    def test_record_usage_without_source_has_none_source(self) -> None:
        """record_usage() without source leaves source as None (backward compat)."""
        tracker = UsageTracker()
        usage = _make_usage(input_tokens=50, output_tokens=25)

        tracker.record_usage(usage)

        records = tracker.get_usage_history()
        assert len(records) == 1
        assert records[0].source is None

    def test_record_usage_with_source_and_model(self) -> None:
        """record_usage() accepts source alongside model and tool_name."""
        tracker = UsageTracker()
        usage = _make_usage(input_tokens=200, output_tokens=100)

        tracker.record_usage(usage, model="gpt-4o", tool_name="read_file", source="coder")

        records = tracker.get_usage_history()
        assert len(records) == 1
        assert records[0].source == "coder"
        assert records[0].model == "gpt-4o"
        assert records[0].tool_name == "read_file"


class TestGetSubagentUsage:
    """Tests for get_subagent_usage() method."""

    def test_returns_empty_dict_when_no_subagent_usage(self) -> None:
        """get_subagent_usage() returns empty dict when no source-tagged usage recorded."""
        tracker = UsageTracker()
        assert tracker.get_subagent_usage() == {}

    def test_returns_empty_dict_after_unsourced_usage(self) -> None:
        """get_subagent_usage() returns empty dict when only unsourced usage exists."""
        tracker = UsageTracker()
        usage = _make_usage(input_tokens=100, output_tokens=50)
        tracker.record_usage(usage)

        assert tracker.get_subagent_usage() == {}

    def test_returns_breakdown_by_subagent(self) -> None:
        """get_subagent_usage() returns per-subagent token usage breakdown."""
        tracker = UsageTracker()

        tracker.record_usage(_make_usage(input_tokens=100, output_tokens=50), source="researcher")
        tracker.record_usage(_make_usage(input_tokens=200, output_tokens=80), source="coder")

        breakdown = tracker.get_subagent_usage()

        assert "researcher" in breakdown
        assert "coder" in breakdown

        assert breakdown["researcher"].prompt_tokens == 100
        assert breakdown["researcher"].completion_tokens == 50
        assert breakdown["researcher"].total_tokens == 150
        assert breakdown["researcher"].request_count == 1

        assert breakdown["coder"].prompt_tokens == 200
        assert breakdown["coder"].completion_tokens == 80
        assert breakdown["coder"].total_tokens == 280
        assert breakdown["coder"].request_count == 1

    def test_multiple_delegations_to_same_subagent_accumulate(self) -> None:
        """Multiple delegations to same subagent accumulate usage."""
        tracker = UsageTracker()

        tracker.record_usage(_make_usage(input_tokens=100, output_tokens=50), source="researcher")
        tracker.record_usage(_make_usage(input_tokens=200, output_tokens=75), source="researcher")

        breakdown = tracker.get_subagent_usage()

        assert len(breakdown) == 1
        assert breakdown["researcher"].prompt_tokens == 300
        assert breakdown["researcher"].completion_tokens == 125
        assert breakdown["researcher"].total_tokens == 425
        assert breakdown["researcher"].request_count == 2

    def test_returns_shallow_copy(self) -> None:
        """get_subagent_usage() returns a copy, not a reference to internal state."""
        tracker = UsageTracker()
        tracker.record_usage(_make_usage(input_tokens=100, output_tokens=50), source="agent-a")

        result1 = tracker.get_subagent_usage()
        result2 = tracker.get_subagent_usage()

        assert result1 is not result2


class TestSubagentUsageInTotalAggregate:
    """Tests that subagent usage is included in total get_usage() aggregate."""

    def test_subagent_usage_included_in_total(self) -> None:
        """Subagent usage is included in the total aggregate usage."""
        tracker = UsageTracker()

        # Record non-subagent usage
        tracker.record_usage(_make_usage(input_tokens=100, output_tokens=50))
        # Record subagent usage
        tracker.record_usage(_make_usage(input_tokens=200, output_tokens=80), source="researcher")

        total = tracker.get_total_usage()
        assert total.prompt_tokens == 300
        assert total.completion_tokens == 130
        assert total.total_tokens == 430
        assert total.request_count == 2

    def test_only_subagent_usage_still_in_total(self) -> None:
        """When only subagent-sourced usage is recorded, it appears in totals."""
        tracker = UsageTracker()
        tracker.record_usage(_make_usage(input_tokens=150, output_tokens=60), source="coder")

        total = tracker.get_total_usage()
        assert total.prompt_tokens == 150
        assert total.completion_tokens == 60
        assert total.total_tokens == 210
        assert total.request_count == 1


class TestBackwardCompatibility:
    """Tests that existing functionality is preserved."""

    def test_record_usage_without_source_works_as_before(self) -> None:
        """record_usage() without source works identically to before."""
        tracker = UsageTracker()
        usage = _make_usage(input_tokens=100, output_tokens=50)

        tracker.record_usage(usage, model="gpt-4o", tool_name="search")

        total = tracker.get_total_usage()
        assert total.prompt_tokens == 100
        assert total.completion_tokens == 50
        assert total.total_tokens == 150
        assert total.request_count == 1

        records = tracker.get_usage_history()
        assert len(records) == 1
        assert records[0].model == "gpt-4o"
        assert records[0].tool_name == "search"
        assert records[0].source is None

    def test_get_breakdown_by_tool_unaffected(self) -> None:
        """get_breakdown_by_tool() still works correctly with source-tagged usage."""
        tracker = UsageTracker()

        tracker.record_usage(
            _make_usage(input_tokens=100, output_tokens=50),
            tool_name="read_file",
            source="researcher",
        )
        tracker.record_usage(
            _make_usage(input_tokens=50, output_tokens=25),
            tool_name="read_file",
        )

        breakdown = tracker.get_breakdown_by_tool()
        assert "read_file" in breakdown
        assert breakdown["read_file"].prompt_tokens == 150
        assert breakdown["read_file"].request_count == 2

    def test_reset_clears_subagent_tracking(self) -> None:
        """reset() clears subagent tracking data as well."""
        tracker = UsageTracker()
        tracker.record_usage(_make_usage(input_tokens=100, output_tokens=50), source="researcher")

        tracker.reset()

        assert tracker.get_subagent_usage() == {}
        assert tracker.get_total_usage().total_tokens == 0
        assert tracker.get_usage_history() == []

    def test_usage_record_source_field_defaults_to_none(self) -> None:
        """UsageRecord.source defaults to None when not specified."""
        from datetime import datetime

        record = UsageRecord(
            timestamp=datetime.now(),
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        assert record.source is None

    def test_usage_record_source_field_can_be_set(self) -> None:
        """UsageRecord.source can be set to a string value."""
        from datetime import datetime

        record = UsageRecord(
            timestamp=datetime.now(),
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            source="my-agent",
        )
        assert record.source == "my-agent"
