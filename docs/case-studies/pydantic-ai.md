# Pydantic AI: a whole-lock audit with online metadata

[Pydantic AI](https://github.com/pydantic/pydantic-ai) is a typed agent framework. This study pins revision
[`4df9988f5e54fac97223c0ad989400d04ca3b766`](https://github.com/pydantic/pydantic-ai/tree/4df9988f5e54fac97223c0ad989400d04ca3b766),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/uv.lock), with its adjacent
[pyproject.toml](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/pyproject.toml). The [ci.yml workflow](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/.github/workflows/ci.yml)
names Python 3.15 and the OS jobs modeled here: `linux-x86_64`. Linux is modeled as x86_64 with
glibc **2.36**; this is an explicit wheelgap floor, not a measurement of the hosted runner’s libc.

This checks the whole workspace lock, including optional integrations and development tooling. It does not reproduce one `uv sync --package ...` CI installation or establish that every locked pin belongs in the same environment.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/pydantic/pydantic-ai/4df9988f5e54fac97223c0ad989400d04ca3b766/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/pydantic/pydantic-ai/4df9988f5e54fac97223c0ad989400d04ca3b766/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.15 -t linux-x86_64 --glibc 2.36 --online \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. Counts below are package/version rows, not necessarily unique names:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 362 | 6 | 2 | 0 | 0 |

The report contains **370 rows**.
It separately skips **10 non-index packages** (editable/local/Git inputs); they are not counted as missing wheels.

## Gaps and options

| Locked pin | Affected targets | `--explain` evidence |
| --- | --- | --- |
| `agent-client-protocol==0.11.1` | `linux-x86_64` (missing) | requires Python <3.15,>=3.10 |
| `forbiddenfruit==0.1.4` | `linux-x86_64` (source) | No compatible wheel in the checked artifact list. |
| `numpy==2.2.6` | `linux-x86_64` (source) | built for cp313-cp313, not CPython 3.15 |
| `onnxruntime==1.30.0` | `linux-x86_64` (missing) | built for cp314-cp314, not CPython 3.15 |
| `orjson==3.12.0` | `linux-x86_64` (source) | built for cp314-cp314, not CPython 3.15 |
| `pandas==2.3.3` | `linux-x86_64` (source) | built for cp314-cp314, not CPython 3.15 |
| `pymongo==4.18.3` | `linux-x86_64` (source) | built for cp314-cp314, not CPython 3.15 |
| `pyyaml==6.0.3` | `linux-x86_64` (source) | built for cp314-cp314, not CPython 3.15 |

Running the same scan without `--json` exposes the human-readable `--explain --suggest` details:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.15 \
  -t linux-x86_64 --glibc 2.36 --online --explain --suggest --no-cache
```

- `agent-client-protocol 0.11.1 -> 1.0.0 has wheels for linux-x86_64`
- `forbiddenfruit 0.1.4: no newer release has a wheel for linux-x86_64`
- `numpy 2.2.6 -> 2.5.2 has wheels for linux-x86_64`
- `onnxruntime 1.30.0: no newer release has a wheel for linux-x86_64`
- `orjson 3.12.0: no newer release has a wheel for linux-x86_64`
- `pandas 2.3.3 -> 3.0.6 has wheels for linux-x86_64`
- `pymongo 4.18.3 -> 4.19.0 has wheels for linux-x86_64`
- `pyyaml 6.0.3: no newer release has a wheel for linux-x86_64`

Every newer-version suggestion listed above was separately checked with pip on this Linux/Python target.
A matching wheel is not proof of dependency or application compatibility: re-resolve and test any upgrade.
Historical wheel versions printed by `--suggest` are not downgrade recommendations. Source builds still need
their own build/interpreter checks; a pure-Python sdist need not require a C compiler.

### Why this audit uses `--online`

The initial offline-file scan labeled `agent-client-protocol==0.11.1` as `wheel` because its filename is universal.
Pip rejected that pin on Python 3.15: its file metadata requires `>=3.10,<3.15`. In wheelgap **0.13.0**,
`--online` refreshes index metadata and reports `missing`, as in the table.

**These are different installer interpretations.** [uv deliberately ignores dependency Requires-Python upper
bounds](https://docs.astral.sh/uv/pip/compatibility/#requires-python-upper-bounds).
The maintainer independently confirmed uv 0.13.1 installs this pin on Python 3.15 in
[wheelgap #544](https://github.com/wheelgap/wheelgap/issues/544). The offline `wheel` is therefore valid for uv;
the 0.13.0 online snapshot above agrees with **pip**, and must not be read as a failed `uv sync` or a Pydantic AI defect.
Issue #544 tracks making online/offline uv-lock answers consistent while exposing pip-specific refusals.
The version and results here remain pinned to 0.13.0, rather than describing that planned change.

## Independent pip check

Pip **26.3** independently accepted **362 wheel pins across the targets**.
For the **8 source/missing cells**, individual `--only-binary=:all:` checks exited 1 with
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
