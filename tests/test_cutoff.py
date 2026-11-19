from datetime import UTC, datetime

import pytest

from wheelgap.cutoff import before_cutoff, parse_cutoff


def test_date_includes_its_whole_local_day():
    cutoff = parse_cutoff("2025-01-01")
    expected = datetime(2025, 1, 2).astimezone(UTC)
    assert cutoff == expected


def test_timestamp_normalizes_its_explicit_offset():
    assert parse_cutoff("2025-01-01T05:30:00+05:30") == datetime(2025, 1, 1, tzinfo=UTC)


@pytest.mark.parametrize("offset", ["+00:60", "-00:60", "+05:99"])
def test_timestamp_refuses_invalid_offset_minutes(offset):
    with pytest.raises(ValueError):
        parse_cutoff(f"2025-01-01T00:00:00{offset}")


def test_cutoff_excludes_equal_and_later_artifacts():
    files = [
        {"filename": "old.whl", "upload_time_iso_8601": "2024-12-31T23:59:59Z"},
        {"filename": "equal.whl", "upload_time_iso_8601": "2025-01-01T00:00:00Z"},
        {"filename": "later.whl", "upload_time_iso_8601": "2025-01-01T00:00:01Z"},
    ]
    assert before_cutoff(files, parse_cutoff("2025-01-01T00:00:00Z")) == files[:1]


def test_artifact_times_are_checked_separately_for_one_release():
    files = [
        {"filename": "old.tar.gz", "upload_time_iso_8601": "2024-12-31T00:00:00Z"},
        {"filename": "late.whl", "upload_time_iso_8601": "2025-01-02T00:00:00Z"},
    ]
    assert before_cutoff(files, parse_cutoff("2025-01-01T00:00:00Z")) == files[:1]


def test_range_ignores_timestamps_of_releases_outside_its_constraint():
    from wheelgap.pypi import _newest_matching

    older = {"filename": "dated-1.0-py3-none-any.whl"}
    matching = {"filename": "dated-2.0-py3-none-any.whl", "upload_time_iso_8601": "2024-01-01T00:00:00Z"}
    assert _newest_matching(
        {"releases": {"1.0": [older], "2.0": [matching]}}, ">=2", "3.13", parse_cutoff("2025-01-01")
    ) == ("2.0", [matching])
