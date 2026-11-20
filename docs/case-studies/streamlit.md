# Streamlit: core dependencies versus integration tests

[Streamlit](https://github.com/streamlit/streamlit) is a framework for data applications. This study pins revision
[`641d2d7d1c8c0681839f0e377cea9a615d1bab77`](https://github.com/streamlit/streamlit/tree/641d2d7d1c8c0681839f0e377cea9a615d1bab77),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/uv.lock), with its adjacent
[pyproject.toml](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/pyproject.toml). The [python-tests.yml workflow](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/.github/workflows/python-tests.yml)
runs two jobs that install this lock, both on `ubuntu-latest`:

- the [unit tests](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/.github/workflows/python-tests.yml#L59-L115) on Python 3.11, 3.12, 3.13, 3.14 and 3.15 (the list is set in
  [`.github/actions/build_info`](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/.github/actions/build_info/action.yml#L25-L27)), with the default `dev` group, which the
  [Makefile](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/Makefile#L163-L169) installs as `uv sync --locked --no-default-groups --group dev`;
- the [integration tests](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/.github/workflows/python-tests.yml#L117-L142) on Python 3.12, after `uv sync --locked --no-default-groups --group integration`.

The only Windows and macOS jobs at this revision, in [meta-skill-discovery.yml](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/.github/workflows/meta-skill-discovery.yml),
install just `pytest` rather than the lock, so this study models `linux-x86_64` only. Linux is modeled as x86_64 with
glibc **2.36**, wheelgap's default floor; this is not a measurement of the hosted runner’s libc.

The root `streamlit-dev` project is virtual and depends on the editable Streamlit package in `lib/`; local and editable
code is not a PyPI wheel gap. The main scan uses `--no-dev`, which drops the default `dev` group and leaves the
**core dependencies**: Streamlit's own runtime requirements as this lock resolves them, with no extras. It checks them on
Python 3.12; [Other CI installs](#other-ci-installs) covers the integration job's selection, the unit-test install and the other Pythons.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/streamlit/streamlit/641d2d7d1c8c0681839f0e377cea9a615d1bab77/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/streamlit/streamlit/641d2d7d1c8c0681839f0e377cea9a615d1bab77/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.12 -t linux-x86_64 --glibc 2.36 --no-dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **0**. Counts below are package/version rows, not necessarily unique names:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 33 | 0 | 0 | 0 | 0 |

The report contains **33 rows**.
It separately skips **2 non-index packages**, the editable `streamlit` and the virtual `streamlit-dev` root; they are not counted as missing wheels.

There were no source, missing or unknown cells and no gap-specific upgrade suggestions. No dependency change is proposed for the core dependencies.

## Other CI installs

The same lock, with the selections the two CI jobs install:

```bash
# The integration job: uv sync --no-default-groups --group integration, on 3.12
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.12 \
  -t linux-x86_64 --glibc 2.36 --no-dev --group integration --no-cache
# The core dependencies on every unit-test Python
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.11 -p 3.12 -p 3.13 -p 3.14 -p 3.15 \
  -t linux-x86_64 --glibc 2.36 --no-dev --no-cache
# The unit-test install (the dev group) on every unit-test Python
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.11 -p 3.12 -p 3.13 -p 3.14 -p 3.15 \
  -t linux-x86_64 --glibc 2.36 --group dev --no-cache
```

- The integration selection reports **153 packages**, all with a wheel on 3.12 (exit **0**), so the integration job installs
  its whole registry graph from wheels too.
- The core dependencies come to **35 package/version rows** across the five Pythons (some pins differ by Python), all with
  a wheel (exit **0**).
- The unit-test install reports **140 rows**, with wheels for every one on 3.11 to 3.14 and two source builds on 3.15
  (exit **1**):

```text
wheelgap 0.13.0 · uv.lock · 140 packages · Python 3.11, 3.12, 3.13, 3.14, 3.15

package                  version  3.11 linux-x86_64  3.12 linux-x86_64  3.13 linux-x86_64  3.14 linux-x86_64  3.15 linux-x86_64
orjson (via streamlit)   3.13.0   ✓                  ✓                  ✓                  ✓                  ● source
pyyaml (via pre-commit)  6.0.3    ✓                  ✓                  ✓                  ✓                  ● source

138 packages with wheels for every target hidden (--all to show)
skipped 2 non-index packages: streamlit (editable), streamlit-dev (virtual)
3.15 linux-x86_64  2 from source
2 of 140 packages have gaps: 2 will build from source.
Run with --explain to see which wheels were rejected and why.
```

With `--explain --suggest` on 3.15:

- **`orjson` 3.13.0**, reached through Streamlit's `charts` and `performance` extras, which the `test` group installs, has a
  CPython 3.15 x86_64 wheel, but it is tagged `manylinux_2_39`, newer than the 2.36 floor. With `--glibc 2.39` wheelgap
  reports a wheel and only `pyyaml` remains. Whether the unit-test runner gets the orjson wheel depends on its glibc, which
  this study doesn't measure.
- **`pyyaml` 6.0.3**, through `pre-commit`, has no CPython 3.15 wheel, and `--suggest` finds no newer release with one.

Neither gap touches the core dependencies, on any of the five Pythons, or the integration job, which runs on 3.12.

## Independent pip check

Pip **26.3** independently accepted **33 wheel pins across the targets**.
There were no source/missing cells requiring individual rejection checks.

The same batch check accepted all **153** wheel pins of the integration selection on 3.12 and the **130** wheel pins of
the unit-test install on 3.15. On 3.15, `orjson==3.13.0` and `pyyaml==6.0.3` each exited 1 with
`No matching distribution found`; adding `--platform manylinux_2_39_x86_64` lets pip pick the orjson wheel.

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
  --python-version 3.12 --implementation cp --abi cp312 \
  "${platform_flags[@]}" -r linux-x86_64-pins.txt --report pip-linux.json
```

For a gap, replace `-r ... --report ...` with its single exact pin from the table. The checks above compared
pip’s selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No project code, model, service, database, browser or hardware was run. New uploads can change these results.
