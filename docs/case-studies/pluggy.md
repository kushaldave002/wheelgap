# pluggy: test dependencies rather than runtime dependencies

[pluggy](https://github.com/pytest-dev/pluggy) is the plugin and hook-calling library behind pytest. It declares no runtime dependencies (its [`pyproject.toml`](https://github.com/pytest-dev/pluggy/blob/93de545c3a31880feaf0f6bb8870b30d602cf681/pyproject.toml) has no `dependencies` list), so this case study checks its locked **development and test environment** at revision [`93de545c3a31880feaf0f6bb8870b30d602cf681`](https://github.com/pytest-dev/pluggy/tree/93de545c3a31880feaf0f6bb8870b30d602cf681). The scan used **wheelgap 0.13.0** and package files available on **20 November 2026**.

The result is a clean bill: every package in the lockfile has a wheel for CPython 3.14 on Linux and Windows. It's a small check, since the only compiled package in the test set is `coverage`; what it mostly shows is how to scope a scan for a project with no runtime dependencies whose CI doesn't install from its lockfile.

## Targets and selection

The pinned [test workflow](https://github.com/pytest-dev/pluggy/blob/93de545c3a31880feaf0f6bb8870b30d602cf681/.github/workflows/test.yml#L31-L104) runs on `ubuntu-latest` for CPython 3.10 through 3.14 and on `windows-latest` for 3.10, 3.13 and 3.14, plus PyPy 3.10 on both; there is no macOS job. This study checks the CPython 3.14 jobs on `linux-x86_64` and `win-amd64`, the x64 Linux and Windows runners. The PyPy jobs aren't covered. Linux uses wheelgap's default glibc floor **2.36**; it doesn't measure the runner's installed libc.

Those jobs don't install from `uv.lock`. They pip-install tox and run `tox run --installpkg dist/*.whl` ([test.yml:124-136](https://github.com/pytest-dev/pluggy/blob/93de545c3a31880feaf0f6bb8870b30d602cf681/.github/workflows/test.yml#L124-L136)), and the [`tox.ini`](https://github.com/pytest-dev/pluggy/blob/93de545c3a31880feaf0f6bb8870b30d602cf681/tox.ini#L13) test environment installs the `testing` dependency group (`pytest>=8`, `pytest-benchmark`, `coverage`), which pip resolves from PyPI at run time. So the scan below checks the locked versions of those packages, the closest record of the test environment in the repository; a given CI run can pick newer releases. The lockfile also holds the `dev` group (`pre-commit` and its dependencies), which the test jobs don't install.

## Reproduce the scan

In an empty folder, download the pinned lockfile and check the `testing` group:

```bash
curl -fL https://raw.githubusercontent.com/pytest-dev/pluggy/93de545c3a31880feaf0f6bb8870b30d602cf681/uv.lock -o uv.lock
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.14 -t linux-x86_64,win-amd64 --only-group testing \
  --explain --suggest --no-cache
```

Output:

```text
wheelgap 0.13.0 · uv.lock · 8 packages · Python 3.14

skipped 1 non-index package: pluggy (editable)
✓ All 8 packages have a wheel for every one of 2 targets.
```

The command exits **0**. `pluggy` itself is skipped because the lockfile records it as the editable project; CI tests the wheel it builds from the checkout. With `--all`, the table also shows that `colorama` 0.4.6, which pytest only needs on Windows, doesn't apply on Linux (`–`).

The one compiled package here is `coverage` 7.13.5, which publishes `cp314` wheels for both targets. The rest are pure-Python wheels.

## The whole lockfile

With no selection flags, wheelgap checks every group in the lockfile, adding `pre-commit` and its dependencies:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.14 -t linux-x86_64,win-amd64 --explain --suggest --no-cache
```

```text
wheelgap 0.13.0 · uv.lock · 18 packages · Python 3.14

skipped 1 non-index package: pluggy (editable)
✓ All 18 packages have a wheel for every one of 2 targets.
```

This also exits **0**. The only other compiled package is `pyyaml` 6.0.3, through `pre-commit`, which has `cp314` wheels for both targets.

## Independent pip check

The wheel cells of the whole-lockfile scan were checked against public PyPI with pip **26.3**, one batch per target with `--dry-run --no-deps --only-binary=:all: --python-version 3.14 --implementation cp --abi cp314`. Windows used `--platform win_amd64`; Linux used every `manylinux_2_*` tag from 2.36 down to 2.5 plus `manylinux2014`, `manylinux2010`, `manylinux1` and `linux` for `x86_64`. pip selected a wheel for every pin, 17 on Linux and 18 on Windows, with the same names and versions wheelgap reported.

To repeat it, save the scan as JSON (add `--json > report.json` to the command above) and write one pin file per target:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64", "win-amd64"):
    pins = [f"{p['name']}=={p['version']}" for p in report["packages"] if p["results"].get(target) == "wheel"]
    Path(f"{target}-pins.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
```

Then, for Linux:

```bash
platform_flags=()
for minor in {36..5}; do
  platform_flags+=(--platform "manylinux_2_${minor}_x86_64")
done
platform_flags+=(--platform manylinux2014_x86_64 --platform manylinux2010_x86_64)
platform_flags+=(--platform manylinux1_x86_64 --platform linux_x86_64)
uvx --from pip==26.3 python -m pip --isolated --disable-pip-version-check install \
  --dry-run --ignore-installed --no-deps --only-binary=:all: --index-url https://pypi.org/simple \
  --python-version 3.14 --implementation cp --abi cp314 \
  "${platform_flags[@]}" -r linux-x86_64-pins.txt --report pip-linux.json
```

For Windows, use `--platform win_amd64` and `win-amd64-pins.txt` instead. `--no-deps` checks each pin's files on its own; it doesn't check that the set resolves together. Neither check runs pluggy's tests or any dependency's build.
