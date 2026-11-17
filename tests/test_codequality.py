"""GitLab Code Quality reports locate each package/target gap in its input file."""

import json
import re

import pytest

from wheelgap.check import Row, Status
from wheelgap.cli import main
from wheelgap.codequality import codequality_report
from wheelgap.sources import Package, Source
from wheelgap.targets import Target

ARMGAP = ("-p", "3.13", "-t", "linux-aarch64,musl-aarch64", "--offline")


def report(tmp_path, *args):
    path = tmp_path / "codequality.json"
    code = main([*args, "--gitlab-code-quality", str(path)])
    return code, json.loads(path.read_text(encoding="utf-8"))


def test_gaps_are_located_at_the_lockfile_line(tmp_path, fixtures, monkeypatch, capsys):
    monkeypatch.setenv("CI_PROJECT_DIR", str(fixtures.parent.parent))
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))  # GitLab's root wins
    code, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP)
    assert code == 1 and "armlib" in capsys.readouterr().out
    assert [f["severity"] for f in findings] == ["major", "critical", "critical"]
    assert [f["check_name"] for f in findings] == ["wheelgap/source", "wheelgap/missing", "wheelgap/missing"]
    lock = (fixtures / "armgap" / "uv.lock").read_text(encoding="utf-8").splitlines()
    for finding in findings:
        assert finding["location"]["path"] == "tests/fixtures/armgap/uv.lock"
        assert lock[finding["location"]["lines"]["begin"] - 1] == f'name = "{finding["description"].split()[0]}"'
        assert re.fullmatch("[0-9a-f]{64}", finding["fingerprint"])
    assert len({f["fingerprint"] for f in findings}) == 3
    assert findings[1]["description"].startswith("newglibc 2.0 can't install on linux-aarch64.")


def test_advisory_and_allowed_source_build_severities(tmp_path, fixtures):
    _, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP, "--advisory", "musl-aarch64")
    assert [f["severity"] for f in findings] == ["info", "critical", "info"]
    _, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP, "--fail-on", "missing")
    assert [f["severity"] for f in findings] == ["minor", "critical", "critical"]


def test_ignored_and_unknown_gaps_have_no_finding(tmp_path, fixtures, fake_pypi):
    _, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP, "--ignore", "newglibc")
    assert len(findings) == 1 and findings[0]["check_name"] == "wheelgap/source"
    code, findings = report(tmp_path, "not-on-pypi", "-p", "3.13", "-t", "linux-x86_64")
    assert code == 1 and findings == []


def test_package_named_on_command_line_has_no_location(tmp_path, fake_pypi):
    code, findings = report(tmp_path, "nowheels", "-p", "3.13", "-t", "linux-x86_64")
    assert code == 1 and findings == []  # GitLab requires a file and line; never invent one.


def test_fingerprint_is_stable_across_runs_and_target_lists(tmp_path, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    lock = tmp_path / "uv.lock"
    lock.write_text('version = 1\n[[package]]\nname = "nowheels"\nversion = "1.0"\n', encoding="utf-8")
    package = Package("nowheels", "1.0", files=[])
    linux = Target(3, 13, False, "linux-x86_64")
    newer = Target(3, 14, False, "linux-x86_64")
    row = Row(package, {linux: Status.MISSING, newer: Status.MISSING})
    source = Source("uv.lock", packages=[package], path=lock, kind="uv")
    first = codequality_report([row], [linux], [source], "source")
    assert first == codequality_report([row], [linux], [source], "source")
    more = codequality_report([row], [linux, newer], [source], "source")
    assert first[0]["fingerprint"] == more[0]["fingerprint"]
    assert len({f["fingerprint"] for f in more}) == 2
    package.version = "2.0"
    changed = codequality_report([row], [linux], [source], "source")
    assert first[0]["fingerprint"] != changed[0]["fingerprint"]


def test_cwd_is_used_when_gitlab_root_is_unset(tmp_path, fixtures, monkeypatch):
    monkeypatch.delenv("CI_PROJECT_DIR", raising=False)
    monkeypatch.chdir(fixtures)
    _, findings = report(tmp_path, "armgap", *ARMGAP)
    assert all(f["location"]["path"] == "armgap/uv.lock" for f in findings)


@pytest.mark.parametrize("path", ["", "missing-dir/report.json"])
def test_unwritable_output_is_an_input_error(tmp_path, fixtures, capsys, monkeypatch, path):
    monkeypatch.chdir(tmp_path)
    assert main([str(fixtures / "armgap"), *ARMGAP, "--gitlab-code-quality", path]) == 2
    assert "wheelgap: error:" in capsys.readouterr().err


def test_report_keeps_json_stdout(tmp_path, fixtures, capsys):
    code, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP, "--json")
    assert code == 1 and len(findings) == 3
    assert json.loads(capsys.readouterr().out)["packages"]
