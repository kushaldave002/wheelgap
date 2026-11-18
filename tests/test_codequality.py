"""GitLab Code Quality reports locate each package/target gap in its input file."""

import json
import re
import shutil

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


def test_advisory_and_allowed_source_build_severities(tmp_path, fixtures, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(fixtures.parent.parent))
    _, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP, "--advisory", "musl-aarch64")
    assert [f["severity"] for f in findings] == ["info", "critical", "info"]
    assert findings[0]["description"] == "armlib 1.4.0 builds from source on musl-aarch64 (advisory)."
    _, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP, "--fail-on", "missing")
    assert [f["severity"] for f in findings] == ["minor", "critical", "critical"]


def test_ignored_and_unknown_gaps_have_no_finding(tmp_path, fixtures, fake_pypi, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(fixtures.parent.parent))
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


ARM = Target(3, 13, False, "linux-aarch64")


def test_a_version_bump_keeps_the_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    lock = tmp_path / "uv.lock"
    findings = []
    for version in ("1.0", "2.0"):
        lock.write_text(f'version = 1\n[[package]]\nname = "nowheels"\nversion = "{version}"\n', encoding="utf-8")
        package = Package("nowheels", version, files=[])
        source = Source("uv.lock", packages=[package], path=lock, kind="uv")
        (finding,) = codequality_report([Row(package, {ARM: Status.MISSING})], [ARM], [source], "source")
        findings.append(finding)
    assert [f["description"] for f in findings] == [
        "nowheels 1.0 can't install on linux-aarch64.",
        "nowheels 2.0 can't install on linux-aarch64.",
    ]
    assert findings[0]["fingerprint"] == findings[1]["fingerprint"]


def test_two_inputs_locking_the_same_package_are_separate_findings(tmp_path, fixtures, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    locks = []
    for folder in ("a", "b"):
        (tmp_path / folder).mkdir()
        locks.append(str(shutil.copy(fixtures / "armgap" / "uv.lock", tmp_path / folder / "uv.lock")))
    _, findings = report(tmp_path, *locks, *ARMGAP)
    assert len(findings) == 6 and len({f["fingerprint"] for f in findings}) == 6
    assert {f["location"]["path"] for f in findings} == {"a/uv.lock", "b/uv.lock"}


def test_duplicates_in_one_file_are_one_finding(tmp_path, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    lock = tmp_path / "uv.lock"
    lock.write_bytes(
        b'version = 1\n\n[[package]]\nname = "dup"\nversion = "1.0"\n\n[[package]]\nname = "dup"\nversion = "2.0"\n'
    )
    old, new = Package("dup", "1.0", files=[]), Package("dup", "2.0", files=[])
    source = Source("uv.lock", packages=[old, new], path=lock, kind="uv")
    rows = [Row(old, {ARM: Status.MISSING}), Row(new, {ARM: Status.MISSING})]
    (finding,) = codequality_report(rows, [ARM], [source], "source")
    assert finding["description"] == "dup 1.0 can't install on linux-aarch64."
    assert finding["location"]["lines"]["begin"] == 4


def test_description_names_the_direct_dependency(tmp_path, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(tmp_path))
    lock = tmp_path / "uv.lock"
    lock.write_text('version = 1\n[[package]]\nname = "cryptography"\nversion = "50.0.2"\n', encoding="utf-8")
    package = Package("cryptography", "50.0.2", files=[])
    source = Source("uv.lock", packages=[package], path=lock, kind="uv")
    row = Row(package, {ARM: Status.SOURCE}, direct_via={ARM: ("mcp", "MCP", "httpx")})
    (finding,) = codequality_report([row], [ARM], [source], "source", frozenset({ARM}))
    assert finding["description"] == "cryptography 50.0.2 (via mcp +1) builds from source on linux-aarch64 (advisory)."


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


def test_report_keeps_json_stdout(tmp_path, fixtures, capsys, monkeypatch):
    monkeypatch.setenv("CI_PROJECT_DIR", str(fixtures.parent.parent))
    code, findings = report(tmp_path, str(fixtures / "armgap"), *ARMGAP, "--json")
    assert code == 1 and len(findings) == 3
    assert json.loads(capsys.readouterr().out)["packages"]
