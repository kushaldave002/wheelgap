# Textual: syntax-highlighting wheels on Python 3.14

[Textual](https://github.com/Textualize/textual) is a terminal user-interface framework. This study pins revision
[`5e5b7ef58b8c5572c13a3ff9027d756623661495`](https://github.com/Textualize/textual/tree/5e5b7ef58b8c5572c13a3ff9027d756623661495),
uses **wheelgap 0.13.0**, and records package availability checked on **20 November 2026**.

## Input, selection and targets

The input is the unchanged [poetry.lock](https://github.com/Textualize/textual/blob/5e5b7ef58b8c5572c13a3ff9027d756623661495/poetry.lock), with its adjacent
[pyproject.toml](https://github.com/Textualize/textual/blob/5e5b7ef58b8c5572c13a3ff9027d756623661495/pyproject.toml). The
[pythonpackage.yml workflow](https://github.com/Textualize/textual/blob/5e5b7ef58b8c5572c13a3ff9027d756623661495/.github/workflows/pythonpackage.yml#L21-L23)
tests Python 3.9 through 3.14 on `ubuntu-latest`, `windows-latest` and `macos-latest`, and installs the `syntax`
extra on every Python except 3.9. This study checks the Python 3.14 jobs on:

- `linux-x86_64`, with wheelgap's default glibc floor **2.36**. This is an explicit floor, not a measurement of the hosted runner's libc.
- `win-amd64`.
- `macos-arm64` as an illustrative Apple-silicon target; the workflow's `macos-latest` label alone does not establish that runner's architecture.

The main scan selects the runtime dependencies plus the `syntax` extra (the tree-sitter packages) and leaves out the
`dev` group that CI also installs; that wider selection is checked [below](#the-dev-group).

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/Textualize/textual/5e5b7ef58b8c5572c13a3ff9027d756623661495/poetry.lock -o poetry.lock
curl -fL https://raw.githubusercontent.com/Textualize/textual/5e5b7ef58b8c5572c13a3ff9027d756623661495/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock \
  -p 3.14 -t linux-x86_64,win-amd64,macos-arm64 --glibc 2.36 --no-dev --extra syntax \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **0**. Its JSON summary, one row per target, was:

| Target | Wheel | Source | Missing | Unknown |
| --- | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 25 | 0 | 0 | 0 |
| `win-amd64` | 25 | 0 | 0 | 0 |
| `macos-arm64` | 25 | 0 | 0 | 0 |

The report contains **25 packages**: the runtime dependencies plus the 16 tree-sitter packages from the extra.

There were no source, missing or unknown cells and no gap-specific upgrade suggestions. No dependency change is proposed.

### The dev group

The test job's `poetry install --extras syntax` also installs the `dev` group. Dropping `--no-dev` from the command
above gives that selection: **105 packages**, and the scan exited **1** with two gaps, both from the `dev` group:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock -p 3.14 \
  -t linux-x86_64,win-amd64,macos-arm64 --glibc 2.36 --extra syntax --explain --suggest --no-cache
```

Trimmed output (the watchdog rejected-file list is cut to its first two lines):

```text
wheelgap: note: --suggest didn't look up 2 packages whose index isn't known to be PyPI (mkdocs-exclude, watchdog), so their names stay private
wheelgap 0.13.0 · poetry.lock · 105 packages · Python 3.14

package         version  linux-x86_64  win-amd64  macos-arm64
mkdocs-exclude  1.0.2    ● source      ● source   ● source
watchdog        6.0.0    ✓             ✓          ● source

103 packages with wheels for every target hidden (--all to show)

mkdocs-exclude 1.0.2 on linux-x86_64: ● source
  no wheels published for this version

mkdocs-exclude 1.0.2 on win-amd64: ● source
  no wheels published for this version

mkdocs-exclude 1.0.2 on macos-arm64: ● source
  no wheels published for this version

watchdog 6.0.0 on macos-arm64: ● source
  watchdog-6.0.0-cp313-cp313-macosx_10_13_universal2.whl  built for cp313-cp313, not CPython 3.14
  watchdog-6.0.0-cp313-cp313-macosx_11_0_arm64.whl        built for cp313-cp313, not CPython 3.14
  … and 21 more (--json lists them all)

linux-x86_64  1 from source
win-amd64     1 from source
macos-arm64   2 from source
2 of 105 packages have gaps: 2 will build from source.
```

mkdocs-exclude 1.0.2 publishes only an sdist, on every Python. watchdog 6.0.0's macOS wheels stop at CPython 3.13
(its Linux and Windows wheels are `py3-none`, so those targets are covered); checked separately on PyPI,
[watchdog 7.0.0 and 7.1.0](https://pypi.org/project/watchdog/7.1.0/#files) have `cp314` macOS arm64 wheels, and
mkdocs, which pulls watchdog in, accepts `watchdog>=2.0`. A matching wheel is not proof of compatibility:
re-resolve and test any upgrade.

## Independent pip check

Pip **26.3** independently accepted all **25 wheel pins on each of the three targets** (75 in all), and every
wheel pin of the dev-group selection (103 on Linux, 104 on Windows, 102 on macOS). Single-pin
`--only-binary=:all:` checks of `mkdocs-exclude==1.0.2` (all three targets) and `watchdog==6.0.0` (macOS) exited 1
with `No matching distribution found`; `watchdog==7.1.0` on macOS exited 0.

To reproduce the wheel-only batches, extract pins by target from `report.json`:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64", "win-amd64", "macos-arm64"):
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

For Windows, replace the platform array with `--platform win_amd64` and use `win-amd64-pins.txt` / `pip-win.json`.
For macOS, use `--platform macosx_14_0_arm64` (wheelgap's default `--macos 14.0`; pip widens macOS tags to older
versions itself) and `macos-arm64-pins.txt`.

Each dry run exited **0** and selected 25 wheels whose package names and versions matched the wheelgap rows.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No Textual code was run. New uploads can change these results.
