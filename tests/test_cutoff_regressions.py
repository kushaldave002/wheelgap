import json

from conftest import FAKE_INDEX
from packaging.requirements import Requirement
from test_deps import INDEX, LINUX, WIN_AMD, index, release  # noqa: F401

from wheelgap import cache, make_targets, pypi
from wheelgap.cli import main
from wheelgap.cutoff import parse_cutoff
from wheelgap.deps import Resolver
from wheelgap.sources import Package

CUTOFF = parse_cutoff("2025-01-01T00:00:00Z")


def test_cutoff_fill_handles_existing_timestamp_less_pinned_cache(fake_pypi, monkeypatch, lookup_cache):
    files = [{"filename": "dated-1.0-py3-none-any.whl", "upload_time_iso_8601": "2024-01-01T00:00:00Z"}]
    monkeypatch.setitem(FAKE_INDEX, "dated", {"1.0": files})
    # Existing cache entries intentionally omit upload times, even when a fresh response had them.
    cache.save_files(pypi.index_url(), "dated", "1.0", files)
    pkg = pypi.fill(Package("dated", "1.0", exclude_newer=CUTOFF), read_cache=True)
    assert pkg.error is None
    assert pkg.files == ["dated-1.0-py3-none-any.whl"]


def test_cutoff_unpinned_requirement_resolves_separately_for_each_python(fake_pypi, monkeypatch):
    monkeypatch.setitem(
        FAKE_INDEX,
        "dated",
        {
            "1.0": [
                {
                    "filename": "dated-1.0-py3-none-any.whl",
                    "requires_python": ">=3.11",
                    "upload_time_iso_8601": "2024-01-01T00:00:00Z",
                }
            ],
            "2.0": [
                {
                    "filename": "dated-2.0-py3-none-any.whl",
                    "requires_python": ">=3.13",
                    "upload_time_iso_8601": "2024-02-01T00:00:00Z",
                }
            ],
        },
    )
    pkg = pypi.fill(Package("dated", None, exclude_newer=CUTOFF), pythons=("3.12", "3.13"))
    assert {python: resolved.version for python, resolved in pkg.resolutions.items()} == {"3.12": "1.0", "3.13": "2.0"}


def test_cutoff_exact_pin_ignores_unrelated_releases_without_upload_times():
    resolver = Resolver(prefetch=False)
    resolver.exclude_newer = CUTOFF
    resolver._projects["dated"] = {
        "releases": {
            "1.0": [{"filename": "dated-1.0-py3-none-any.whl"}],
            "2.0": [{"filename": "dated-2.0-py3-none-any.whl"}],
        }
    }
    target = make_targets("3.13", "linux-x86_64")[0]
    assert resolver.pick("dated", ["==1.0"], target) == "1.0"


def test_cutoff_exact_pin_on_windows_does_not_exempt_linux_range(
    index,  # noqa: F811
    monkeypatch,
    tmp_path,
    capsys,
):
    monkeypatch.setitem(INDEX, "dated", {"1.0": release(files=(WIN_AMD, LINUX))})
    fetch_json = pypi.fetch_json

    def dated_json(url, **kwargs):
        data = fetch_json(url, **kwargs)
        for entries in [*data.get("releases", {}).values(), data.get("urls", [])]:
            for entry in entries:
                entry["upload_time_iso_8601"] = (
                    "2024-01-01T00:00:00Z" if entry["filename"].endswith(".tar.gz") else "2025-02-01T00:00:00Z"
                )
        return data

    monkeypatch.setattr(pypi, "fetch_json", dated_json)
    path = tmp_path / "pyproject.toml"
    path.write_text(
        "[project]\ndependencies = [\"dated==1.0; sys_platform == 'win32'\", "
        '"dated>=1; sys_platform == \'linux\'"]\n[tool.uv]\nexclude-newer="2025-01-01T00:00:00Z"\n',
        encoding="utf-8",
    )
    assert main([str(path), "--deps", "-p", "3.14", "-t", "win-amd64", "-t", "linux-x86_64", "--json"]) == 1
    packages = json.loads(capsys.readouterr().out)["packages"]
    assert [p["results"]["win-amd64"] for p in packages if p["results"]["win-amd64"] != "n/a"] == ["wheel"]
    assert [p["results"]["linux-x86_64"] for p in packages if p["results"]["linux-x86_64"] != "n/a"] == ["source"]


def test_cutoff_abandoned_round_pin_does_not_exempt_a_later_range(index, monkeypatch):  # noqa: F811
    monkeypatch.setitem(INDEX, "dated", {"1.0": release(files=(LINUX,))})
    fetch_json = pypi.fetch_json

    def dated_json(url, **kwargs):
        data = fetch_json(url, **kwargs)
        for entries in [*data.get("releases", {}).values(), data.get("urls", [])]:
            for entry in entries:
                entry["upload_time_iso_8601"] = (
                    "2024-01-01T00:00:00Z" if entry["filename"].endswith(".tar.gz") else "2025-02-01T00:00:00Z"
                )
        return data

    monkeypatch.setattr(pypi, "fetch_json", dated_json)
    resolver = Resolver(prefetch=False)
    resolver.exclude_newer = CUTOFF
    target = make_targets("3.14", "linux-x86_64")[0]
    resolver._round([Requirement("dated==1.0")], target, {})
    assert resolver._wheels("dated", "1.0", target)
    # An exact constraint reached only in an abandoned round must not remain an exemption.
    resolver._round([Requirement("dated>=1")], target, {})
    assert resolver._wheels("dated", "1.0", target) == []
