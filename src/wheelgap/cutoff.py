"""Absolute uv upload cutoffs; relative durations cannot reproduce a resolution."""

import re
from datetime import UTC, datetime, timedelta

_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)", re.ASCII
)


class UploadTimeError(ValueError):
    pass


def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise ValueError("expected an RFC 3339 timestamp with a timezone")
    return datetime.fromisoformat(value.upper()).astimezone(UTC)


def parse_cutoff(value: object) -> datetime:
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value, re.ASCII):
        # uv includes the whole local date, ending at the following local midnight.
        return (datetime.fromisoformat(value) + timedelta(days=1)).astimezone(UTC)
    return timestamp(value)


def before_cutoff(files: list[dict], cutoff: datetime | None) -> list[dict]:
    if cutoff is None:
        return files
    kept = []
    for entry in files:
        try:
            uploaded = timestamp(entry.get("upload_time_iso_8601"))
        except ValueError:
            raise UploadTimeError(
                f"exclude-newer: {entry['filename']} has no valid upload_time_iso_8601; its age is unknown"
            ) from None
        if uploaded < cutoff:
            kept.append(entry)
    return kept
