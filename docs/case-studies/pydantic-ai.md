# Pydantic AI: a whole-lock audit with online metadata

[Pydantic AI](https://github.com/pydantic/pydantic-ai) is a typed agent framework. This study pins revision
[`4df9988f5e54fac97223c0ad989400d04ca3b766`](https://github.com/pydantic/pydantic-ai/tree/4df9988f5e54fac97223c0ad989400d04ca3b766),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/uv.lock), with its adjacent
[pyproject.toml](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/pyproject.toml). In the [ci.yml workflow](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/.github/workflows/ci.yml),
the [`test`](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/.github/workflows/ci.yml#L747-L761) and
[`test-all-extras`](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/.github/workflows/ci.yml#L1040-L1052) jobs run Python 3.11 to 3.15
on Linux: the runner named by the repository variable `CI_LINUX_RUNNER`, or `ubuntu-latest` and `ubuntu-24.04`
respectively when it is unset. The macOS and Windows jobs
([clipboard](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/.github/workflows/ci.yml#L1740-L1769) and
[Windows workspace](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/.github/workflows/ci.yml#L1790-L1810) tests)
use Python 3.13 only. This study checks Python 3.15, so `linux-x86_64` is the only platform CI names for it. Linux is
modeled as x86_64 with glibc **2.36**, wheelgap's default floor; this is not a measurement of the runner's libc, and one
result below depends on it.

The scan uses no selection flags, so it checks the whole workspace lock: every extra and dependency group of the root
project and its eight workspace members. The nearest CI install is `test-all-extras`, which runs its tests with
[`uv run --all-packages --all-extras`](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/.github/workflows/ci.yml#L1230):
every member with every extra, plus the default `dev` and `lint` groups. wheelgap has no `--all-packages`, and the whole
lock also counts groups that job doesn't install, so this is close to that job's environment, not a reproduction of it.

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

The report contains **370 rows**. It separately skips **10 non-index packages**, the nine editable workspace projects
and the Git dependency `strict-no-cover`; they are not counted as missing wheels.

Without `--online` the same scan reports **363** wheels, 6 source and **1** missing. The only difference is
`agent-client-protocol`, explained [below](#online-and-offline-answers-for-agent-client-protocol).

## Gaps and options

| Locked pin | Status | `--explain` evidence |
| --- | --- | --- |
| `agent-client-protocol==0.11.1` | missing with `--online`, wheel without | "requires Python <3.15,>=3.10": pip's refusal; uv installs it (see below) |
| `forbiddenfruit==0.1.4` | source | no wheels published for this version |
| `numpy==2.2.6` | source | wheels up to cp313 only; no 3.15 install reaches this pin (see below) |
| `onnxruntime==1.30.0` | missing | wheels up to cp314 only, and no sdist; no 3.15 install reaches this pin (see below) |
| `orjson==3.12.0` | source | its cp315 wheel is tagged `manylinux_2_39`, newer than the 2.36 floor |
| `pandas==2.3.3` | source | wheels up to cp314 only: "built for cp314-cp314, not CPython 3.15" |
| `pymongo==4.18.3` | source | wheels up to cp314 only |
| `pyyaml==6.0.3` | source | wheels up to cp314 only |

Running the same scan without `--json` prints the human-readable `--explain --suggest` details; its `--suggest` lines are:

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

- **`orjson` 3.12.0** does publish a CPython 3.15 x86_64 wheel, tagged `manylinux_2_39`. With `--distro ubuntu-24.04`
  (glibc 2.39) wheelgap reports it as a wheel, so on a glibc 2.39 runner it isn't a gap; this study doesn't measure which
  runner `CI_LINUX_RUNNER` names.
- **`onnxruntime` 1.30.0** (and its dependency `flatbuffers`) reaches the lock only through `stackone-defender[onnx]`,
  which the `pydantic-ai-harness` extra `prompt-injection-defender-ml` requests with the marker
  `python_full_version < '3.15'`
  ([uv.lock line 7489](https://github.com/pydantic/pydantic-ai/blob/4df9988f5e54fac97223c0ad989400d04ca3b766/uv.lock#L7489)).
  **`numpy` 2.2.6** is also required by `pandas`, `gradio`, `datasets` and `pixeltable`, but the lock's resolution
  markers limit it to Python 3.11 to 3.13; on 3.14 and 3.15 the lock uses numpy 2.5.2.
  Following the lock's dependency markers from every workspace member, with all extras and groups, on CPython 3.15
  Linux reaches **367** registry packages: the report's 370 rows less these two and `flatbuffers` 25.12.19, a dependency
  of `onnxruntime` that has a wheel. wheelgap 0.13.0's whole-lock scan still lists the three, so these two gaps are not
  ones a 3.15 install of this lock meets.

## Online and offline answers for agent-client-protocol

`agent-client-protocol` 0.11.1 has one wheel, `agent_client_protocol-0.11.1-py3-none-any.whl`, and PyPI records
`Requires-Python >=3.10,<3.15` for it. The lock doesn't carry that per-file value, so without `--online` wheelgap reads
the file list and reports `wheel`. With `--online`, wheelgap 0.13.0 re-reads PyPI's metadata, drops the file as pip
would, and reports `missing`, as in the table.

**These are different installers' answers, and for this lock the offline one is right.** [uv deliberately ignores
dependency Requires-Python upper bounds](https://docs.astral.sh/uv/pip/compatibility/#requires-python-upper-bounds), and
Pydantic AI's CI installs with uv. The maintainer confirmed in [wheelgap #544](https://github.com/wheelgap/wheelgap/issues/544)
that uv 0.13.1 installs this pin on a real CPython 3.15 (`uv lock`, then `uv sync --locked --python 3.15`) with no
warning, and `uv pip compile`
with `--python-version 3.15 --no-deps --only-binary :all:` resolves it with uv 0.13.9. pip refuses it (see below).
So the `missing` in the online table is pip's answer: it is not a failed `uv sync` and not a Pydantic AI defect, and the
`--suggest` line naming 1.0.0 (`Requires-Python >=3.10,<3.16`) matters only to someone installing these pins with pip.

The maintainer decided in #544 that wheelgap answers a `uv.lock` the way `uv sync` installs it, online and offline, and
says separately where pip would refuse a file. The results on this page stay pinned to wheelgap 0.13.0, before that
change.

## What a 3.15 install meets

Taking the three points above together, a uv install of the whole lock on CPython 3.15 Linux with a glibc 2.36 floor builds
five pins from source (`forbiddenfruit`, `orjson`, `pandas`, `pymongo` and `pyyaml`), and on a glibc 2.39 runner four,
without `orjson`. Of those, `pandas` 2.3.3 and `pymongo` 4.18.3 have newer releases with CPython 3.15 wheels.

## Independent pip check

Pip **26.3** independently accepted **362 wheel pins across the targets**.
For the **8 source/missing cells**, individual `--only-binary=:all:` checks exited 1 with
`No matching distribution found`. That confirms absence of an eligible wheel, not whether a source build works. For
`agent-client-protocol==0.11.1`, pip also lists `0.11.1 Requires-Python >=3.10,<3.15` among the versions it ignored. With
`--platform manylinux_2_39_x86_64` added, pip picks the `orjson` 3.12.0 wheel.

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
