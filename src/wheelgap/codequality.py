"""GitLab Code Quality findings for packages without wheels on a target."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .check import Row, Status
from .github import Locator
from .sarif import WORDS, level
from .sources import Source
from .targets import Target


def codequality_report(
    rows: list[Row],
    targets: list[Target],
    sources: list[Source],
    fail_on: str,
    advisory: frozenset[Target] = frozenset(),
) -> list[dict]:
    """One finding per package and gap target, with a repository-relative location. GitLab requires a file and
    line, so packages named on the command line and inputs outside the repository have no finding."""
    locator = Locator(sources)
    base = Path(os.environ.get("CI_PROJECT_DIR") or os.getcwd()).resolve()
    multi_py = len({t.python for t in targets}) > 1
    findings = []
    for row in rows:
        if row.ok or (located := locator.locate(row.package)) is None:
            continue
        try:
            path = located[0].resolve().relative_to(base).as_posix()
        except (OSError, ValueError):
            continue
        pkg = row.package
        name = f"{pkg.name} {pkg.version}" if pkg.version else pkg.name
        for target in targets:
            status = row.results[target]
            if status not in WORDS or target in row.ignored:
                continue
            severity = {"note": "info", "warning": "minor"}.get(
                level(status, target, fail_on, advisory), "critical" if status is Status.MISSING else "major"
            )
            # Always name the Python in the fingerprint, even if the report checks only one Python.
            identity = json.dumps([pkg.key, pkg.version, target.label(True)])
            findings.append(
                {
                    "description": f"{name} {WORDS[status]} {target.label(multi_py)}."
                    + (" (advisory)" if target in advisory else ""),
                    "check_name": f"wheelgap/{status.value}",
                    "fingerprint": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
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
