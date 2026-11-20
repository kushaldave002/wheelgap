# Fava: Beancount’s Python 3.15 wheel gap

[Fava](https://github.com/beancount/fava) is a web interface for Beancount accounting files. This study pins revision
[`67945a7321628aacfbcc20ae77f5796a5acff8c5`](https://github.com/beancount/fava/tree/67945a7321628aacfbcc20ae77f5796a5acff8c5),
uses **wheelgap 0.13.0**, and records package availability checked on **20 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/beancount/fava/blob/67945a7321628aacfbcc20ae77f5796a5acff8c5/uv.lock), with its adjacent
[pyproject.toml](https://github.com/beancount/fava/blob/67945a7321628aacfbcc20ae77f5796a5acff8c5/pyproject.toml). The
[test.yml workflow](https://github.com/beancount/fava/blob/67945a7321628aacfbcc20ae77f5796a5acff8c5/.github/workflows/test.yml#L16-L35)
runs the Python tests with Python 3.15 on `ubuntu-latest`, `macos-latest` and `windows-latest` (plus Python 3.11
and extra test variants on Ubuntu). This study checks the Python 3.15 jobs on:

- `linux-x86_64`, with wheelgap's default glibc floor **2.36**. This is an explicit floor, not a measurement of the hosted runner's libc.
- `win-amd64`.
- `macos-arm64` as an illustrative Apple-silicon target; the workflow's `macos-latest` label alone does not establish that runner's architecture.

The main scan selects Fava's runtime dependencies (`--no-dev`). The test job itself runs
`uv run --no-dev --group test` (see the [Makefile](https://github.com/beancount/fava/blob/67945a7321628aacfbcc20ae77f5796a5acff8c5/Makefile#L69-L70));
that wider selection is checked [below](#the-test-group). This study does not run those tests or establish that a source build succeeds.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/beancount/fava/67945a7321628aacfbcc20ae77f5796a5acff8c5/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/beancount/fava/67945a7321628aacfbcc20ae77f5796a5acff8c5/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.15 -t linux-x86_64,win-amd64,macos-arm64 --glibc 2.36 --no-dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. The report contains **32 packages**; per target:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 31 | 1 | 0 | 0 | 0 |
| `win-amd64` | 30 | 1 | 0 | 1 | 0 |
| `macos-arm64` | 31 | 1 | 0 | 0 | 0 |

The `n/a` cell is `python-magic`, which the lock marks as not needed on Windows. The report also lists Fava itself
under `skipped` (an editable install, not an index package); it is not counted as a missing wheel.

## Gaps and options

The one gap is Beancount, rather than a Fava distribution. The same scan without `--json`:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.15 \
  -t linux-x86_64,win-amd64,macos-arm64 --glibc 2.36 --no-dev --explain --suggest --no-cache
```

Trimmed output (the Linux and Windows `--explain` blocks, which read like the macOS one, are omitted; the first
line is a stderr hint):

```text
wheelgap: add --notes to show the tracker's notes for these packages (sends their names to wheelgap.github.io)
wheelgap 0.13.0 · uv.lock · 32 packages · Python 3.15

package    version  linux-x86_64  win-amd64  macos-arm64
beancount  3.2.3    ● source      ● source   ● source

31 packages with wheels for every target hidden (--all to show)

beancount 3.2.3 on macos-arm64: ● source
  via: fava → beancount
  beancount-3.2.3-cp314-cp314-macosx_11_0_arm64.whl     built for cp314-cp314, not CPython 3.15
  beancount-3.2.3-cp314-cp314t-macosx_11_0_arm64.whl    built for cp314-cp314t, not CPython 3.15
  beancount-3.2.3-cp313-cp313-macosx_11_0_arm64.whl     built for cp313-cp313, not CPython 3.15
  beancount-3.2.3-cp312-cp312-macosx_11_0_arm64.whl     built for cp312-cp312, not CPython 3.15
  beancount-3.2.3-cp311-cp311-macosx_11_0_arm64.whl     built for cp311-cp311, not CPython 3.15
  beancount-3.2.3-cp314-cp314-macosx_10_15_x86_64.whl   macosx_10_15_x86_64 doesn't match macos-arm64
  beancount-3.2.3-cp314-cp314t-macosx_10_15_x86_64.whl  macosx_10_15_x86_64 doesn't match macos-arm64
  beancount-3.2.3-cp313-cp313-macosx_10_13_x86_64.whl   macosx_10_13_x86_64 doesn't match macos-arm64
  … and 22 more (--json lists them all)

beancount 3.2.3: no newer release has a wheel for linux-x86_64, win-amd64, macos-arm64

skipped 1 non-index package: fava (editable)
linux-x86_64  1 from source
win-amd64     1 from source
macos-arm64   1 from source
1 of 32 packages has gaps: 1 will build from source.
```

Beancount 3.2.3 is the newest release on PyPI, and its wheels stop at CPython 3.14, so on these targets
installing it for 3.15 means building the [sdist](https://pypi.org/project/beancount/3.2.3/#files). Source builds
need their own build/interpreter checks; a future Beancount release with `cp315` wheels would close the gap.

### The test group

Adding the test job's group (`--no-dev --group test` instead of `--no-dev`) gives **50 packages**, and Beancount
is still the only gap on all three targets.

## Independent pip check

Pip **26.3** independently accepted every wheel pin in the runtime report: **31** on Linux, **30** on Windows and
**31** on macOS. For the **3 source cells**, single-pin `--only-binary=:all:` checks of `beancount==3.2.3` exited 1
with `No matching distribution found`. That confirms absence of an eligible wheel, not whether a source build works.

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
  --python-version 3.15 --implementation cp --abi cp315 \
  "${platform_flags[@]}" -r linux-x86_64-pins.txt --report pip-linux.json
```

For Windows, replace the platform array with `--platform win_amd64` and use `win-amd64-pins.txt` / `pip-win.json`.
For macOS, use `--platform macosx_14_0_arm64` (wheelgap's default `--macos 14.0`; pip widens macOS tags to older
versions itself) and `macos-arm64-pins.txt`.

For the gap, replace `-r ... --report ...` with `beancount==3.2.3`. The checks above compared
pip’s selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No Fava or Beancount code was run. New uploads can change these results.
