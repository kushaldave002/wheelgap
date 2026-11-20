# Litestar: two documentation-only source builds on Python 3.14

[Litestar](https://github.com/litestar-org/litestar) is an ASGI application framework. This study pins revision
[`df860951b3ab08da7a0aaf3711b9b796e966642b`](https://github.com/litestar-org/litestar/tree/df860951b3ab08da7a0aaf3711b9b796e966642b),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/uv.lock), with its adjacent
[pyproject.toml](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/pyproject.toml). The [ci.yml workflow](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/.github/workflows/ci.yml)
runs the reusable [test.yml](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/.github/workflows/test.yml) workflow in two places:

- the [`test` job](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/.github/workflows/ci.yml#L87-L96) on `ubuntu-latest` for Python 3.11, 3.12, 3.13 and 3.14;
- the [`test-platform-compat` job](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/.github/workflows/ci.yml#L182-L192) on `macos-latest` and `windows-latest` for Python 3.14, on pushes and on pull requests labelled `test platform compat`.

This study checks Python 3.14 on the three platforms those jobs name: `linux-x86_64`, `macos-arm64` and `win-amd64`. The
`macos-latest` label alone doesn't fix the runner's architecture or macOS version; this study models Apple silicon with
wheelgap's default macOS floor, **14.0**. Linux is modeled as x86_64 with glibc **2.36**, wheelgap's default floor; this
is not a measurement of the hosted runner’s libc.

test.yml installs with a plain [`uv sync`](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/.github/workflows/test.yml#L62-L63), so CI gets
Litestar's runtime dependencies plus all four [default groups](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/pyproject.toml#L123):
`dev`, `linting`, `test` and `docs`. With any selection flag, wheelgap counts the project's dependencies and uv's default
groups, so `--group dev` (one of those groups) selects exactly what `uv sync` installs, without extras.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/litestar-org/litestar/df860951b3ab08da7a0aaf3711b9b796e966642b/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/litestar-org/litestar/df860951b3ab08da7a0aaf3711b9b796e966642b/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.14 -t linux-x86_64 -t macos-arm64 -t win-amd64 --glibc 2.36 --group dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. Counts below are package/version rows, not necessarily unique names:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 211 | 2 | 0 | 1 | 0 |
| `macos-arm64` | 210 | 3 | 0 | 1 | 0 |
| `win-amd64` | 211 | 2 | 0 | 1 | 0 |

The report contains **214 rows**. The `n/a` cells are `tzdata` (installed only on Windows) and `uvloop` (not installed
on Windows). It separately skips **3 non-index packages**: the editable `litestar` and the Git dependencies
`advanced-alchemy` and `litestar-sphinx-theme`; they are not counted as missing wheels.

The same selection on Linux for each Python in the `test` matrix (`-p 3.11 -p 3.12 -p 3.13 -p 3.14 -t linux-x86_64 --group dev`)
reports the same two source builds on every version, and nothing else.

## Gaps and options

| Locked pin | Affected targets | `--explain` evidence |
| --- | --- | --- |
| `autodocsumm==0.2.6` | all three (source) | no wheels published for this version |
| `sphinx-paramlinks==0.6.0` | all three (source) | no wheels published for this version |
| `autobahn==26.11.1` | `macos-arm64` (source) | its macOS arm64 wheels are tagged `macosx_15_0`, newer than the 14.0 floor |

Running the same scan without `--json` prints the human-readable `--explain --suggest` details:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.14 \
  -t linux-x86_64 -t macos-arm64 -t win-amd64 --glibc 2.36 --group dev --explain --suggest --no-cache
```

Its gap table and `--suggest` lines (the per-file `--explain` lines and the skipped-package summary are trimmed):

```text
wheelgap 0.13.0 · uv.lock · 214 packages · Python 3.14

package                              version  linux-x86_64  macos-arm64  win-amd64
autobahn (via daphne)                26.11.1  ✓             ● source     ✓
autodocsumm (via sphinx-toolbox +1)  0.2.6    ● source      ● source     ● source
sphinx-paramlinks                    0.6.0    ● source      ● source     ● source

211 packages with wheels for every target hidden (--all to show)

autobahn 26.11.1: no newer release has a wheel for macos-arm64; the last one that did is 25.9.1
autodocsumm 0.2.6 -> 0.2.8 has wheels for linux-x86_64, macos-arm64, win-amd64
sphinx-paramlinks 0.6.0: no newer release has a wheel for linux-x86_64, macos-arm64, win-amd64; the last one that did is 0.5.1

linux-x86_64  2 from source
macos-arm64   3 from source
win-amd64     2 from source
3 of 214 packages have gaps: 3 will build from source.
```

- **`autodocsumm` 0.2.6** (through `sphinx-toolbox`) and **`sphinx-paramlinks` 0.6.0** are both in the `docs` group and
  publish only an sdist at these versions. `autodocsumm` 0.2.8 has a wheel; `sphinx-paramlinks` has none after 0.5.1.
  These are documentation dependencies, not evidence of a gap in Litestar's runtime install.
- **`autobahn` 26.11.1** reaches the tree through `daphne` in the `dev` group. Its only macOS arm64 wheels are tagged
  `macosx_15_0_arm64`, so with `--macos 15.0` wheelgap reports a wheel and only the two documentation gaps remain. A
  macOS 15 or newer runner gets the wheel; this study doesn't establish which macOS version `macos-latest` provides.

Every newer-version suggestion listed above was separately checked with pip on its target.
A matching wheel is not proof of dependency or application compatibility: re-resolve and test any upgrade.
Historical wheel versions printed by `--suggest` are not downgrade recommendations. Source builds still need
their own build/interpreter checks; a pure-Python sdist need not require a C compiler.

## Independent pip check

Pip **26.3** accepted every wheel pin in the report except one on each target: **210** of 211 on Linux, **209** of 210
on macOS and **210** of 211 on Windows. The exception is `beanie==2.1.0`, from the `dev` group. Its only wheel,
`beanie-2.1.0-py3-none-any.whl`, declares `Requires-Python >=3.10,<3.14`, so pip refuses it on 3.14.

That is a difference between installers, not a wheelgap error. [uv ignores Requires-Python upper
bounds](https://docs.astral.sh/uv/pip/compatibility/#requires-python-upper-bounds), and wheelgap answers a `uv.lock` the
way `uv sync` installs it, so `wheel` is right for this CI. `uv pip compile` with `--python-version 3.14 --no-deps
--only-binary :all:` resolves `beanie==2.1.0` with uv 0.13.9 and with uv 0.8.8, the version test.yml pins. With
`--online`, wheelgap 0.13.0 drops the file as pip would and reports `beanie` as `missing`;
[wheelgap #544](https://github.com/wheelgap/wheelgap/issues/544) tracks making that answer follow uv too, while still
saying where pip would refuse a file.

For the gap cells, individual `--only-binary=:all:` checks of `autodocsumm==0.2.6` and `sphinx-paramlinks==0.6.0` on each
target, and of `autobahn==26.11.1` with `--platform macosx_14_0_arm64`, exited 1 with `No matching distribution found`.
That confirms absence of an eligible wheel, not whether a source build works. With `--platform macosx_15_0_arm64`, pip
picks the `autobahn` 26.11.1 wheel.

To reproduce the wheel-only batches, extract pins by target from `report.json`:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64", "macos-arm64", "win-amd64"):
    pins = [f"{p['name']}=={p['version']}" for p in report["packages"] if p["results"].get(target) == "wheel"]
    Path(f"{target}-pins.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
```

For Linux, pass every accepted manylinux tag, including the legacy aliases:

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

For macOS use `--platform macosx_14_0_arm64` (pip widens it to older macOS versions itself) with `macos-arm64-pins.txt`,
and for Windows `--platform win_amd64` with `win-amd64-pins.txt`. Each batch stops at `beanie==2.1.0`; take that line out
of the pins file and run it again. For a gap, replace `-r ... --report ...` with its single exact pin from the table.
The checks above compared pip’s selected package names and versions with the wheelgap rows and confirmed that every
selected file was a wheel. `--no-deps` deliberately does not validate consistency of the whole environment or activate
project extras/groups. No project code, model, service, database, browser or hardware was run. New uploads can change
these results.
