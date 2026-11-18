"""GitLab Code Quality findings for packages without wheels on a target."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .check import Row, Status
from .github import Locator, relative_path
from .sarif import WORDS, level, via_hint
from .sources import Source
from .targets import Target


def codequality_report(
    rows: list[Row],
    targets: list[Target],
    sources: list[Source],
    fail_on: str,
    advisory: frozenset[Target] = frozenset(),
) -> list[dict]:
    """One finding per package and gap target, with a repository-relative location (CI_PROJECT_DIR, else the current
    directory). GitLab requires a file and line, so packages named on the command line and inputs outside the
    repository have no finding."""
    locator = Locator(sources)
    multi_py = len({t.python for t in targets}) > 1
    findings = []
    emitted: set[str] = set()
    for row in rows:
        if row.ok or (located := locator.locate(row.package)) is None:
            continue
        if (path := relative_path(located[0], "CI_PROJECT_DIR")) is None:
            continue
        pkg = row.package
        name = f"{pkg.name} {pkg.version}" if pkg.version else pkg.name
        for target in targets:
            status = row.results[target]
            if status not in WORDS or target in row.ignored:
                continue
            # The same file, package and target is the same finding from one run to the next, whatever its version,
            # as SARIF's fingerprint; the Python is always named, so adding another Python changes no fingerprint.
            identity = json.dumps([path, pkg.key, target.label(True)])
            fingerprint = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            if fingerprint in emitted:  # GitLab needs each fingerprint once per report
                continue
            emitted.add(fingerprint)
            severity = {"note": "info", "warning": "minor"}.get(
                level(status, target, fail_on, advisory), "critical" if status is Status.MISSING else "major"
            )
            findings.append(
                {
                    "description": f"{name}{via_hint(row, target)} {WORDS[status]} {target.label(multi_py)}"
                    + (" (advisory)" if target in advisory else "")
                    + ".",
                    "check_name": f"wheelgap/{status.value}",
                    "fingerprint": fingerprint,
                    "severity": severity,
                    "location": {"path": path, "lines": {"begin": located[1] or 1}},
                }
            )
    return findings


def write_codequality(
    path: str,
    rows: list[Row],
    targets: list[Target],
    sources: list[Source],
    fail_on: str,
    advisory: frozenset[Target] = frozenset(),
) -> None:
    Path(path).write_text(
        json.dumps(codequality_report(rows, targets, sources, fail_on, advisory), indent=2) + "\n", "utf-8"
    )
