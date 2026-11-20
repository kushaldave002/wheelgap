# Poetry: test groups versus main on Python 3.15

[Poetry](https://github.com/python-poetry/poetry) is a Python dependency-management CLI. This study pins revision
[`406ff8932e8775e1a82cea9f7f85c4b4b651eec7`](https://github.com/python-poetry/poetry/tree/406ff8932e8775e1a82cea9f7f85c4b4b651eec7),
uses **wheelgap 0.13.0**, and records package availability checked on **20 November 2026**.

## Input, selection and targets

The input is the unchanged [poetry.lock](https://github.com/python-poetry/poetry/blob/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/poetry.lock), with its adjacent
[pyproject.toml](https://github.com/python-poetry/poetry/blob/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/pyproject.toml). The
[tests.yaml workflow](https://github.com/python-poetry/poetry/blob/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/.github/workflows/tests.yaml#L125-L140)
runs its test matrix on `ubuntu-24.04`, `windows-2025` and `macos-15` (named "macOS aarch64") for Python 3.11
through 3.15. This study checks the Python 3.15 jobs on:

- `linux-x86_64`, with wheelgap's default glibc floor **2.36**. This is an explicit floor, not a measurement of the hosted runner's libc.
- `win-amd64`.
- `macos-arm64`, with wheelgap's default minimum macOS **14.0**.

The scan drops the lock's `dev` group (`--no-dev`). The `test` and `typing` groups stay in; the optional
`github-actions` group is left out. Lock entries whose markers don't match a target, such as the
`sys_platform == "darwin"` dependency `xattr`, appear as `n/a` there.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/python-poetry/poetry/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/poetry.lock -o poetry.lock
curl -fL https://raw.githubusercontent.com/python-poetry/poetry/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock \
  -p 3.15 -t linux-x86_64,win-amd64,macos-arm64 --glibc 2.36 --no-dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. The report contains **67 packages**; per target:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 63 | 1 | 0 | 3 | 0 |
| `win-amd64` | 60 | 1 | 0 | 6 | 0 |
| `macos-arm64` | 60 | 2 | 0 | 5 | 0 |

## Gaps and options

The same scan without `--json` prints the table and the `--explain` details:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock -p 3.15 \
  -t linux-x86_64,win-amd64,macos-arm64 --glibc 2.36 --no-dev --explain --suggest --no-cache
```

Trimmed output (the Linux and macOS PyYAML blocks, which read like the Windows one, are omitted, and each
rejected-file list is cut to its first two lines; wheelgap itself lists eight and points to `--json` for the rest):

```text
wheelgap: note: --suggest didn't look up 2 packages whose index isn't known to be PyPI (pyyaml, xattr), so their names stay private
wheelgap 0.13.0 · poetry.lock · 67 packages · Python 3.15

package  version  linux-x86_64  win-amd64  macos-arm64
pyyaml   6.0.3    ● source      ● source   ● source
xattr    1.3.0    –             –          ● source

65 packages with wheels for every target hidden (--all to show)

pyyaml 6.0.3 on win-amd64: ● source
  pyyaml-6.0.3-cp314-cp314-win_amd64.whl   built for cp314-cp314, not CPython 3.15
  pyyaml-6.0.3-cp314-cp314t-win_amd64.whl  built for cp314-cp314t, not CPython 3.15

xattr 1.3.0 on macos-arm64: ● source
  xattr-1.3.0-cp314-cp314-macosx_10_15_universal2.whl   built for cp314-cp314, not CPython 3.15
  xattr-1.3.0-cp314-cp314-macosx_11_0_arm64.whl         built for cp314-cp314, not CPython 3.15

linux-x86_64  1 from source
win-amd64     1 from source
macos-arm64   2 from source
2 of 67 packages have gaps: 2 will build from source.
```

The lock records no package index for these entries, so `--suggest` printed no newer releases (see the note above).
Checked separately on PyPI:

| Locked pin | Lock groups | Affected targets | Newer release with a CPython 3.15 wheel |
| --- | --- | --- | --- |
| `pyyaml==6.0.3` | `dev`, `test` | all three (source) | none; 6.0.3 is the newest PyYAML release |
| `xattr==1.3.0` | `main` (macOS only) | `macos-arm64` (source) | [xattr 1.3.1](https://pypi.org/project/xattr/1.3.1/#files), uploaded 10 November 2026, has `cp315` macOS wheels |

PyYAML stays in the `--no-dev` selection because the `test` group also needs it. xattr is a main dependency on macOS
(`xattr (>=1.0.0,<2.0.0) ; sys_platform == 'darwin'` in `pyproject.toml`), so on that target the gap is not limited
to test tooling. xattr 1.3.1 is within that range, but a matching wheel is not proof of dependency or application
compatibility: re-resolve and test any upgrade. Source builds still need their own build/interpreter checks.

### A narrower group selection

Changing the selector to `--only-group main` (instead of `--no-dev`) produced **46 packages and no gaps** on
`linux-x86_64` and `win-amd64`. With `macos-arm64` added it reports **47 packages**, with xattr 1.3.0 as the one gap:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock -p 3.15 \
  -t linux-x86_64,win-amd64,macos-arm64 --glibc 2.36 --only-group main --json --explain --suggest --no-cache
```

Use that selection only when it describes what you intend to install; it omits the other groups, not just their gaps.

## Independent pip check

Pip **26.3** independently accepted every wheel pin in the `--no-dev` report: **63** on Linux, **60** on Windows
and **60** on macOS. For the gaps, single-pin `--only-binary=:all:` checks of `pyyaml==6.0.3` (all three
targets) and `xattr==1.3.0` (macOS) exited 1 with `No matching distribution found`, while `xattr==1.3.1` on
macOS exited 0. That confirms absence of an eligible wheel, not whether a source build works.

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

For a gap, replace `-r ... --report ...` with its single exact pin. The checks above compared
pip’s selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No Poetry code was run. New uploads can change these results.
