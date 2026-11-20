# Typer: CPython 3.15 and 3.15t test dependencies across three platforms

[Typer](https://github.com/fastapi/typer) is a library for building command-line interfaces from Python type hints. This case study checks its locked **test environment**, not just its runtime dependencies, at revision [`2517edde5a1292a712e2f16e600754c52c6f00d9`](https://github.com/fastapi/typer/tree/2517edde5a1292a712e2f16e600754c52c6f00d9). The scan used **wheelgap 0.13.0** and package files available on **20 November 2026**.

The result is a clean bill on demanding targets: every registry package the CI test job installs has a wheel for CPython 3.15 and for free-threaded 3.15t on Linux, Windows and macOS, compiled packages included. One detail is still worth knowing: the locked `coverage` gets there through its pure-Python wheel (see [below](#the-compiled-packages)).

## Targets and selection

The pinned [test matrix](https://github.com/fastapi/typer/blob/2517edde5a1292a712e2f16e600754c52c6f00d9/.github/workflows/test.yml#L19-L38) runs on `ubuntu-latest`, `windows-latest` and `macos-latest` for Python 3.15 and 3.15t with uv's `highest` resolution, plus four jobs on older Pythons (3.11 and 3.12 with `lowest-direct`, 3.13 and 3.14 with `highest`). This study checks the 3.15 and 3.15t jobs on:

- `linux-x86_64` and `win-amd64`, the x64 Linux and Windows runners.
- `macos-arm64`, the Apple-silicon runner. The workflow's `macos-latest` label alone doesn't establish the runner's architecture; across GitHub-hosted images it is ARM today, and this study says so rather than assuming it for every reader.

Linux uses wheelgap's default glibc floor **2.36**; it doesn't measure the runner's installed libc.

Each job installs with `uv sync --no-dev --group tests` ([test.yml:65](https://github.com/fastapi/typer/blob/2517edde5a1292a712e2f16e600754c52c6f00d9/.github/workflows/test.yml#L65)), and the wheelgap command below uses the same selection against the [pinned `uv.lock`](https://github.com/fastapi/typer/blob/2517edde5a1292a712e2f16e600754c52c6f00d9/uv.lock): Typer's runtime dependencies plus the `tests` group. The lockfile records no resolution mode, so it holds uv's default `highest` resolution, the one the 3.15 jobs use; the `lowest-direct` jobs ask uv for a different resolution and aren't covered here. The documentation and other groups aren't part of this check.

## Reproduce the scan

In an empty folder, download the pinned lockfile and check it for both builds of 3.15:

```bash
curl -fL https://raw.githubusercontent.com/fastapi/typer/2517edde5a1292a712e2f16e600754c52c6f00d9/uv.lock -o uv.lock
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.15 -t linux-x86_64,win-amd64,macos-arm64 \
  --no-dev --group tests --explain --suggest --no-cache
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.15t -t linux-x86_64,win-amd64,macos-arm64 \
  --no-dev --group tests --explain --suggest --no-cache
```

Output of the first command:

```text
wheelgap 0.13.0 · uv.lock · 29 packages · Python 3.15

skipped 1 non-index package: typer (editable)
✓ All 29 packages have a wheel for every one of 3 targets.
```

The second prints the same, with `Python 3.15t` in the header. Both exit **0**. `typer` itself is skipped because the lockfile records it as the editable project, which CI installs from the checkout. With `--all`, the table also shows that `colorama` 0.4.6, which Typer only needs on Windows, doesn't apply on Linux or macOS (`–`).

## The compiled packages

Most of the 29 packages are pure Python. The ones with native code all have wheels that fit 3.15 and 3.15t at these pins:

- **`pydantic-core` 2.50.1, `mypy` 2.4.0 and `librt` 0.16.0** publish `cp315-cp315` and `cp315-cp315t` wheels for all three platforms.
- **`ast-serialize` 0.13.1** publishes `cp315-abi3.abi3t` wheels for all three, which both the regular and the free-threaded build accept.
- **`ruff` 0.17.2 and `ty` 0.0.85** publish `py3-none` platform wheels, which don't depend on the Python version or ABI.
- **`coverage` 7.13.1** publishes compiled wheels only up to `cp314`/`cp314t`, plus a pure-Python `py3-none-any` wheel. On 3.15 and 3.15t that pure-Python wheel is the one that installs. wheelgap counts it as a wheel, correctly, since nothing is built, but a `none-any` wheel can't hold coverage's compiled C extension. Later releases such as `coverage` 7.17.3 (12 November 2026) publish `cp315` and `cp315t` wheels, and the `tests` group's `coverage[toml] >=7.13` allows them. Because this isn't a gap, `--explain` and `--suggest` don't mention it.

## Independent pip check

The wheel cells were checked against public PyPI with pip **26.3**, one batch per Python and target with `--dry-run --no-deps --only-binary=:all: --python-version 3.15 --implementation cp`, using `--abi cp315` for 3.15 and `--abi cp315t` for 3.15t. Windows used `--platform win_amd64`; macOS used `macosx_*_arm64` and `universal2` tags from 14.0 down; Linux used every `manylinux_2_*` tag from 2.36 down to 2.5 plus `manylinux2014`, `manylinux2010`, `manylinux1` and `linux` for `x86_64`. For each of the six batches, pip selected a wheel for every pin (28 on Linux and macOS, 29 on Windows) with the same names and versions wheelgap reported. Among them, pip picked `coverage-7.13.1-py3-none-any.whl` and the `ast_serialize-0.13.1-cp315-abi3.abi3t` wheels on every target, and `mypy-2.4.0-cp315-cp315t` wheels for 3.15t.

To repeat it, save a scan as JSON (add `--json > report.json` to one of the commands above) and write one pin file per target:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64", "win-amd64", "macos-arm64"):
    pins = [f"{p['name']}=={p['version']}" for p in report["packages"] if p["results"].get(target) == "wheel"]
    Path(f"{target}-pins.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
```

Then, for Linux and 3.15:

```bash
platform_flags=()
for minor in {36..5}; do
  platform_flags+=(--platform "manylinux_2_${minor}_x86_64")
done
platform_flags+=(--platform manylinux2014_x86_64 --platform manylinux2010_x86_64)
platform_flags+=(--platform manylinux1_x86_64 --platform linux_x86_64)
uvx --from pip==26.3 python -m pip --isolated --disable-pip-version-check install \
  --dry-run --ignore-installed --no-deps --only-binary=:all: --index-url https://pypi.org/simple \
  --python-version 3.15 --implementation cp --abi cp315 \
  "${platform_flags[@]}" -r linux-x86_64-pins.txt --report pip-linux.json
```

For Windows, use `--platform win_amd64` and `win-amd64-pins.txt`; for macOS, `--platform macosx_14_0_arm64` and `macos-arm64-pins.txt`; for 3.15t, `--abi cp315t` and a report from the `-p 3.15t` scan. `--no-deps` checks each pin's files on its own; it doesn't check that the set resolves together. Neither check runs Typer's tests or any dependency's build.
