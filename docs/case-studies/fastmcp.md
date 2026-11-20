# FastMCP: optional and development pins on Python 3.15

[FastMCP](https://github.com/PrefectHQ/fastmcp) is a framework for MCP servers and clients. This study pins revision
[`12a2db1c612cc86e760d855e835035c8efd6321f`](https://github.com/PrefectHQ/fastmcp/tree/12a2db1c612cc86e760d855e835035c8efd6321f),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/PrefectHQ/fastmcp/blob/12a2db1c612cc86e760d855e835035c8efd6321f/uv.lock), with its adjacent
[pyproject.toml](https://github.com/PrefectHQ/fastmcp/blob/12a2db1c612cc86e760d855e835035c8efd6321f/pyproject.toml). The [run-tests.yml workflow](https://github.com/PrefectHQ/fastmcp/blob/12a2db1c612cc86e760d855e835035c8efd6321f/.github/workflows/run-tests.yml)
runs the tests on `ubuntu-latest` for Python 3.11, 3.12, 3.13, 3.14 and 3.15 ([`run_tests`](https://github.com/PrefectHQ/fastmcp/blob/12a2db1c612cc86e760d855e835035c8efd6321f/.github/workflows/run-tests.yml#L66-L88)),
and on `windows-latest` for 3.11 and 3.14 only ([`run_windows_tests`](https://github.com/PrefectHQ/fastmcp/blob/12a2db1c612cc86e760d855e835035c8efd6321f/.github/workflows/run-tests.yml#L116-L124)). This
study checks Python 3.15, so `linux-x86_64` is the only platform CI names for it; [Other CI legs](#other-ci-legs) covers
the rest. Linux is modeled as x86_64 with glibc **2.36**, wheelgap's default floor; this is not a measurement of the
hosted runner’s libc.

The scan uses no selection flags, so it checks the whole lock: every extra and group of the root project and the three
workspace members. Here that is also what CI installs. The jobs install with
[`uv sync --locked`](https://github.com/PrefectHQ/fastmcp/blob/12a2db1c612cc86e760d855e835035c8efd6321f/.github/actions/setup-uv/action.yml#L30), which adds the default
[`dev` group](https://github.com/PrefectHQ/fastmcp/blob/12a2db1c612cc86e760d855e835035c8efd6321f/pyproject.toml#L86), and that group requests `fastmcp` with all of its extras and `fastmcp-remote`.
On 3.15 the CI selection (`--group dev`) reports the same 151 rows with the same results as the whole-lock scan below.
The runtime dependencies of the root `fastmcp` project alone (`--no-dev`, 60 rows) include only one of the five source
builds, `pyyaml`.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/PrefectHQ/fastmcp/12a2db1c612cc86e760d855e835035c8efd6321f/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/PrefectHQ/fastmcp/12a2db1c612cc86e760d855e835035c8efd6321f/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.15 -t linux-x86_64 --glibc 2.36 \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. Counts below are package/version rows, not necessarily unique names:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 146 | 5 | 0 | 0 | 0 |

The report contains **151 rows**.
It separately skips **4 non-index packages**, the editable workspace projects `fastmcp`, `fastmcp-remote`, `fastmcp-slim`
and `fastmcp-tasks`; they are not counted as missing wheels.

## Gaps and options

| Locked pin | Affected targets | `--explain` evidence |
| --- | --- | --- |
| `jiter==0.16.0` | `linux-x86_64` (source) | wheels up to cp314 only: "built for cp314-cp314, not CPython 3.15" |
| `msgspec==0.21.1` | `linux-x86_64` (source) | wheels up to cp314 only: "built for cp314-cp314, not CPython 3.15" |
| `pyinstrument==5.1.2` | `linux-x86_64` (source) | wheels up to cp314 only: "built for cp314-cp314, not CPython 3.15" |
| `pytest-report==0.2.1` | `linux-x86_64` (source) | no wheels published for this version |
| `pyyaml==6.0.3` | `linux-x86_64` (source) | wheels up to cp314 only: "built for cp314-cp314, not CPython 3.15" |

Running the same scan without `--json` prints the human-readable `--explain --suggest` details; its `--suggest` lines are:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.15 \
  -t linux-x86_64 --glibc 2.36 --explain --suggest --no-cache
```

- `jiter 0.16.0 -> 0.17.0 has wheels for linux-x86_64`
- `msgspec 0.21.1 -> 0.22.0 has wheels for linux-x86_64`
- `pyinstrument 5.1.2: no newer release has a wheel for linux-x86_64; the last one that did is 3.4.2`
- `pytest-report 0.2.1: no newer release has a wheel for linux-x86_64`
- `pyyaml 6.0.3: no newer release has a wheel for linux-x86_64`

Every newer-version suggestion listed above was separately checked with pip on this Linux/Python target.
A matching wheel is not proof of dependency or application compatibility: re-resolve and test any upgrade.
Historical wheel versions printed by `--suggest` are not downgrade recommendations. Source builds still need
their own build/interpreter checks; a pure-Python sdist need not require a C compiler.

## Other CI legs

The CI selection on the other Pythons the workflow names:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.11 -p 3.12 -p 3.13 -p 3.14 \
  -t linux-x86_64 --glibc 2.36 --group dev --no-cache
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.11 -p 3.14 \
  -t win-amd64 --group dev --no-cache
```

Both exit **1** with one source build on every leg, `pytest-report` 0.2.1, which publishes only an sdist. The other four
gaps above are specific to CPython 3.15. pip agrees for Windows: `pytest-report==0.2.1` with `--platform win_amd64`
exited 1 with `No matching distribution found` on 3.11 and on 3.14.

## Independent pip check

Pip **26.3** independently accepted **146 wheel pins across the targets**.
For the **5 source/missing cells**, individual `--only-binary=:all:` checks exited 1 with
`No matching distribution found`. That confirms absence of an eligible wheel, not whether a source build works.

To reproduce the wheel-only batches, extract pins by target from `report.json`:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64",):
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

For a gap, replace `-r ... --report ...` with its single exact pin from the table. The checks above compared
pip’s selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No project code, model, service, database, browser or hardware was run. New uploads can change these results.
