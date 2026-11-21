# Prefect: a glibc-floor gap and PyYAML on Python 3.15

[Prefect](https://github.com/PrefectHQ/prefect) is a workflow orchestration framework. This study pins revision
[`ed96dafb35df5b7e09ef38c5a037d6f280fb5517`](https://github.com/PrefectHQ/prefect/tree/ed96dafb35df5b7e09ef38c5a037d6f280fb5517),
uses **wheelgap 0.13.0**, and records package availability checked on **21 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/uv.lock), with its adjacent
[pyproject.toml](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/pyproject.toml).
Python 3.15 is the newest version the pinned workflows name, and three of them name it:

- the [python-tests.yaml workflow](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/.github/workflows/python-tests.yaml#L98-L107),
  which runs the test suite on `ubuntu-latest` for Python 3.11 through 3.15, after `uv sync --locked`;
- the [windows-tests.yaml workflow](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/.github/workflows/windows-tests.yaml#L47-L50),
  which runs its tests on `windows-latest` for Python 3.11, 3.12 and 3.15, with `uv run`;
- the [docker-images.yaml workflow](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/.github/workflows/docker-images.yaml#L131),
  which builds images for Python 3.11 through 3.15 on `linux/amd64` and `linux/arm64`.

This study checks Python 3.15 on `linux-x86_64`, `linux-aarch64` and `win-amd64`. Linux is modeled with wheelgap's
default glibc floor, **2.36**; that is an explicit floor, not a measurement of the hosted runner's or the image's libc,
and one of the two gaps below depends on it. [Python 3.14](#python-314) is a short second section.

The main scan selects Prefect's runtime dependencies (`--no-dev`), which is what the images are built from: the
Dockerfile installs Prefect against constraints
[exported from the lock with `--no-dev`](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/Dockerfile#L108), and a CI step
[checks the built image](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/.github/workflows/python-tests.yaml#L742-L746)
with `uv sync --check --frozen --no-dev`. The test jobs also install the `dev` group; that wider selection is checked
[below](#the-dev-group). Prefect's database, services, workers and integrations, and the image build itself, are
outside this wheel-only check.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/PrefectHQ/prefect/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/PrefectHQ/prefect/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.15 -t linux-x86_64,linux-aarch64,win-amd64 --glibc 2.36 --no-dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. One row per target, counted from the report's `packages`:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 101 | 2 | 0 | 2 | 0 |
| `linux-aarch64` | 101 | 2 | 0 | 2 | 0 |
| `win-amd64` | 104 | 1 | 0 | 0 | 0 |

The report contains **105 packages**. The two `n/a` cells on each Linux target are `pywin32` and `tzdata`, which the
lock installs on Windows only. The report also lists Prefect itself under `skipped` (an editable install, not an
index package); it is not counted as a missing wheel. Without `--json`, the same scan prints:

```text
wheelgap 0.13.0 · uv.lock · 105 packages · Python 3.15

package  version  linux-x86_64  linux-aarch64  win-amd64
orjson   3.13.0   ● source      ● source       ✓
pyyaml   6.0.3    ● source      ● source       ● source

103 packages with wheels for every target hidden (--all to show)
```

and, after the `--explain` details, ends with:

```text
skipped 1 non-index package: prefect (editable)
linux-x86_64   2 from source
linux-aarch64  2 from source
win-amd64      1 from source
2 of 105 packages have gaps: 2 will build from source.
```

## Gaps and options

Both gaps are direct dependencies of Prefect (`via: prefect → orjson`, `via: prefect → pyyaml`).

| Locked pin | Affected targets | `--explain` evidence |
| --- | --- | --- |
| `orjson==3.13.0` | `linux-x86_64`, `linux-aarch64` (source) | it has a cp315 wheel, but for a newer glibc: "manylinux_2_39_x86_64 needs glibc 2.39, newer than 2.36 (--glibc)" (and `manylinux_2_39_aarch64`) |
| `pyyaml==6.0.3` | all three (source) | wheels up to cp314 only: "built for cp314-cp314, not CPython 3.15" |

The `--suggest` lines are:

- `orjson 3.13.0: no newer release has a wheel for linux-x86_64, linux-aarch64`
- `pyyaml 6.0.3 -> 6.0.4 has wheels for linux-x86_64, linux-aarch64, win-amd64`

**orjson** is the glibc floor at work. For CPython 3.11 to 3.14, orjson 3.13.0 publishes `manylinux_2_17` wheels; its
CPython 3.15 Linux wheels are tagged `manylinux_2_39` only, and 3.13.0 is the newest release. Its `win_amd64` cp315
wheel is why Windows is covered. Raising the floor to 2.39 (the glibc of Ubuntu 24.04) leaves PyYAML as the only gap:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.15 -t linux-x86_64,linux-aarch64 --glibc 2.39 --no-dev --no-cache
```

```text
wheelgap 0.13.0 · uv.lock · 103 packages · Python 3.15

package  version  linux-x86_64  linux-aarch64
pyyaml   6.0.3    ● source      ● source

102 packages with wheels for every target hidden (--all to show)
```

So whether a Python 3.15 test runner or image gets the orjson wheel or builds it depends on its glibc, which this study
doesn't measure: 2.39 or newer installs the wheel, and anything older builds orjson from its sdist.

**PyYAML** 6.0.4 was uploaded to PyPI on 20 November 2026, the day after the pinned commit, and has CPython 3.15
wheels for all three targets. The lock pins 6.0.3, so the gap stays until the lock is updated.

A matching wheel is not proof of dependency or application compatibility: re-resolve and test any upgrade. Source
builds still need their own build and interpreter checks.

### The image's extras

The [Dockerfile](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/Dockerfile#L200)
installs Prefect with `PREFECT_EXTRAS=[redis,client,otel]` by default. `redis` and `otel` are extras in
`pyproject.toml` (`client` is not, so wheelgap rejects `--extra client`); adding `--extra redis --extra otel` to the
two Linux targets gives **124 packages** with the same two gaps and no others. The image installs from an exported
constraints file rather than from `uv.lock` directly, so this is an approximation of the image's package set, not a
check of the image.

### The dev group

The test jobs install the runtime dependencies plus uv's default `dev` group. Replacing `--no-dev` with `--group dev`
gives that selection on the two platforms that run tests: **213 packages**, and the scan exited **1** with five gaps:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.15 -t linux-x86_64,win-amd64 --glibc 2.36 \
  --group dev --explain --suggest --no-cache
```

```text
wheelgap 0.13.0 · uv.lock · 213 packages · Python 3.15

package                  version  linux-x86_64  win-amd64
orjson                   3.13.0   ● source      ✓
pyre-check (via typsht)  0.9.23   ✓             ● source
pyyaml                   6.0.3    ● source      ● source
testslide (via typsht)   2.7.1    ● source      ● source
watchfiles               1.2.0    ✓             ● source

208 packages with wheels for every target hidden (--all to show)
```

The three the `dev` group adds:

- **testslide 2.7.1** (`(dev group) → typsht → pyre-check → testslide`) publishes only an sdist, so uv builds it on
  any target and Python; it is the newest release.
- **pyre-check 0.9.23** (`(dev group) → typsht → pyre-check`) has `py3-none` wheels for `manylinux1_x86_64` and macOS
  Intel only, so it is a source build on Windows on every Python; no newer release has a Windows wheel.
- **watchfiles 1.2.0** has Windows wheels up to CPython 3.14 only ("built for cp314-cp314, not CPython 3.15");
  `--suggest` reports `watchfiles 1.2.0 -> 1.3.0 has wheels for win-amd64`.

The same selection on the other Pythons the test workflows name (3.11 to 3.13 on `linux-x86_64`, 3.11 and 3.12 on
`win-amd64`) has only the gaps that don't depend on the Python version: testslide on both platforms and pyre-check
on Windows.

## Python 3.14

The first version of this study checked Python 3.14, which the Linux test and image matrices also name (the Windows
tests don't). There the runtime dependencies have no gaps:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.14 -t linux-x86_64,linux-aarch64 --glibc 2.36 --no-dev --no-cache
```

```text
wheelgap 0.13.0 · uv.lock · 103 packages · Python 3.14

skipped 1 non-index package: prefect (editable)
✓ All 103 packages have a wheel for every one of 2 targets.
```

With `--extra redis --extra otel` it is 124 packages, again all wheels on both targets. With `--group dev` on
`linux-x86_64` it is 211 packages and exit 1 with one gap, testslide 2.7.1. orjson 3.13.0 and PyYAML 6.0.3 both have
cp314 wheels that fit the 2.36 floor, so both gaps of the main scan are specific to CPython 3.15.

## Independent checks

The Python 3.15 gaps and suggestions were checked against the file lists in PyPI's JSON API on 21 November 2026:

- orjson 3.13.0 is the newest release, and its only cp315 Linux wheels are `manylinux_2_39` (`x86_64`, `aarch64`,
  `armv7l`, `i686`) and `musllinux_1_2`; it has a cp315 `win_amd64` wheel;
- PyYAML 6.0.3 has no cp315 file, and 6.0.4 (uploaded 20 November 2026) has cp315 `manylinux2014`/`manylinux_2_28`
  wheels for `x86_64` and `aarch64` and a cp315 `win_amd64` wheel;
- testslide 2.7.1 is the newest release and has an sdist only;
- pyre-check 0.9.23, 0.9.25 and 0.10.0 have no Windows wheel;
- watchfiles 1.2.0 has cp315 wheels for Linux but none for Windows, and 1.3.0 has a `cp310-abi3` `win_amd64` wheel.

That confirms which files exist, not whether a source build works.

For the Python 3.14 scans, pip **26.3** independently accepted all **103 wheel pins on each of the two targets**, all
124 pins of the extras selection on each target, and the 210 wheel pins of the dev-group selection on `linux-x86_64`.
For the dev-group gap, a single-pin `--only-binary=:all:` check of `testslide==2.7.1` exited 1 with
`No matching distribution found`.

To reproduce the wheel-only batches, save the 3.14 scan's report (the command above with
`--json --explain --suggest`, redirected to `report-314.json`) and extract pins by target:

```python
import json
from pathlib import Path

report = json.loads(Path("report-314.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64", "linux-aarch64"):
    pins = [f"{p['name']}=={p['version']}" for p in report["packages"] if p["results"].get(target) == "wheel"]
    Path(f"{target}-pins.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
```

For x86_64, pass every accepted manylinux tag, including the legacy aliases:

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

For aarch64, change the architecture, stop the loop at 17 (`{36..17}`), and follow it with only
`manylinux2014_aarch64` and `linux_aarch64`, since there are no older manylinux tags for that architecture; use
`linux-aarch64-pins.txt`.

For a gap, replace `-r ... --report ...` with its single exact pin. The checks above compared
pip's selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No Prefect code was run. New uploads can change these results.
