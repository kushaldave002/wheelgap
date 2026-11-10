from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

# Fake PyPI: name -> {version: [filenames]}, plus the "latest" version for unpinned lookups.
FAKE_INDEX = {
    "fastlib": {"2.0.0": ["fastlib-2.0.0-cp313-cp313-manylinux_2_17_x86_64.whl", "fastlib-2.0.0.tar.gz"]},
    "unpinned": {"4.2": ["unpinned-4.2-py3-none-any.whl"]},
    "winonly": {"311": ["winonly-311-cp313-cp313-win_amd64.whl"]},
    "purewheel": {"3.1": ["purewheel-3.1-py3-none-any.whl"]},
    "nowheels": {"0.9": ["nowheels-0.9.tar.gz"]},
    "ranged": {
        "1.5": ["ranged-1.5-py3-none-any.whl"],
        "1.9": ["ranged-1.9.tar.gz"],
        "2.0": ["ranged-2.0-py3-none-any.whl"],
    },
    "pythonranged": {
        "1.0": [{"filename": "pythonranged-1.0-py3-none-any.whl", "requires_python": ">=3.8"}],
        "2.0": [{"filename": "pythonranged-2.0-py3-none-any.whl", "requires_python": ">=3.10"}],
    },
    "yanked": {"1.0": [{"filename": "yanked-1.0-py3-none-any.whl", "yanked": True}]},
    "halfyanked": {"2.0": [{"filename": "halfyanked-2.0-py3-none-any.whl", "yanked": True}, "halfyanked-2.0.tar.gz"]},
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Tests shouldn't depend on the developer's colour or index settings."""
    for name in ("NO_COLOR", "FORCE_COLOR", "WHEELGAP_INDEX_URL"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES


@pytest.fixture
def fake_pypi(monkeypatch):
    import urllib.error

    from wheelgap import pypi

    calls = []

    def fetch_json(url, timeout=20.0):
        calls.append(url)
        parts = url.removeprefix(pypi.DEFAULT_INDEX + "/").removesuffix("/json").split("/")
        name = parts[0]
        if name not in FAKE_INDEX:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        versions = FAKE_INDEX[name]
        version = parts[1] if len(parts) > 1 else next(reversed(versions))
        files = versions.get(version)
        if files is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        def entries(fs):
            return [f if isinstance(f, dict) else {"filename": f} for f in fs]

        data = {"info": {"version": version}, "urls": entries(files)}
        if len(parts) == 1:  # the project endpoint lists every release, like PyPI
            data["releases"] = {v: entries(fs) for v, fs in versions.items()}
        return data

    monkeypatch.setattr(pypi, "fetch_json", fetch_json)
    return calls
