"""uv's exclude-newer upload cutoffs (#521): the absolute forms uv accepts, and the per-file filter it applies.

uv also accepts relative durations ("7 days", "P7D"); those are refused, since the cutoff they give moves with the
clock."""

import re
from datetime import UTC, datetime, timedelta

_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)", re.ASCII
)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


class UploadTimeError(ValueError):
    pass


def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise ValueError("expected an RFC 3339 timestamp with a timezone")
    try:
        return datetime.fromisoformat(value.upper()).astimezone(UTC)
    except (OverflowError, OSError):
        raise ValueError(f"{value} is out of range") from None


def parse_cutoff(value: object) -> datetime:
    """An RFC 3339 timestamp, or a date: as uv reads one, the midnight that ends it in the local time zone."""
    if isinstance(value, str) and _DATE.fullmatch(value):
        try:
            return (datetime.fromisoformat(value) + timedelta(days=1)).astimezone(UTC)
        except (OverflowError, OSError):
            raise ValueError(f"{value} is out of range") from None
    return timestamp(value)


def describe(cutoff: datetime) -> str:
    return cutoff.isoformat().replace("+00:00", "Z")


def _millisecond(moment: datetime) -> datetime:
    """uv compares upload times and cutoffs in whole milliseconds."""
    return moment.replace(microsecond=moment.microsecond - moment.microsecond % 1000)


def before_cutoff(files: list[dict], cutoff: datetime | None) -> list[dict]:
    """The files uploaded before `cutoff`, as uv keeps them: each file on its own, so a release can keep some."""
    if cutoff is None:
        return files
    limit = _millisecond(cutoff)
    kept = []
    for entry in files:
        try:
            uploaded = timestamp(entry.get("upload_time_iso_8601"))
        except ValueError:
            raise UploadTimeError(
                f"exclude-newer: {entry['filename']} has no valid upload_time_iso_8601; its age is unknown"
            ) from None
        if _millisecond(uploaded) < limit:
            kept.append(entry)
    return kept
