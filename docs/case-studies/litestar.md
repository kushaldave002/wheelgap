# Litestar: documentation groups behind two source builds

[Litestar](https://github.com/litestar-org/litestar) is an ASGI application framework. This study pins revision
[`df860951b3ab08da7a0aaf3711b9b796e966642b`](https://github.com/litestar-org/litestar/tree/df860951b3ab08da7a0aaf3711b9b796e966642b),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/uv.lock), with its adjacent
[pyproject.toml](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/pyproject.toml). The [ci.yml workflow](https://github.com/litestar-org/litestar/blob/df860951b3ab08da7a0aaf3711b9b796e966642b/.github/workflows/ci.yml)
names Python 3.14 and the OS jobs modeled here: `linux-x86_64`. Linux is modeled as x86_64 with
glibc **2.36**; this is an explicit wheelgap floor, not a measurement of the hosted runner’s libc.

Its uv defaults name `dev`, `linting`, `test` and `docs`. `--no-dev` removes only `dev`, so the docs groups still count. Both source gaps are documentation dependencies, not proof of a runtime deployment gap.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/litestar-org/litestar/df860951b3ab08da7a0aaf3711b9b796e966642b/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/litestar-org/litestar/df860951b3ab08da7a0aaf3711b9b796e966642b/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.14 -t linux-x86_64 --glibc 2.36 --no-dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. Counts below are package/version rows, not necessarily unique names:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 135 | 2 | 0 | 0 | 0 |

The report contains **137 rows**.
It separately skips **2 non-index packages** (editable/local/Git inputs); they are not counted as missing wheels.

## Gaps and options

| Locked pin | Affected targets | `--explain` evidence |
| --- | --- | --- |
| `autodocsumm==0.2.6` | `linux-x86_64` (source) | No compatible wheel in the checked artifact list. |
| `sphinx-paramlinks==0.6.0` | `linux-x86_64` (source) | No compatible wheel in the checked artifact list. |

Running the same scan without `--json` exposes the human-readable `--explain --suggest` details:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.14 \
  -t linux-x86_64 --glibc 2.36 --no-dev --explain --suggest --no-cache
```

- `autodocsumm 0.2.6 -> 0.2.8 has wheels for linux-x86_64`
- `sphinx-paramlinks 0.6.0: no newer release has a wheel for linux-x86_64; the last one that did is 0.5.1`

Every newer-version suggestion listed above was separately checked with pip on this Linux/Python target.
A matching wheel is not proof of dependency or application compatibility: re-resolve and test any upgrade.
Historical wheel versions printed by `--suggest` are not downgrade recommendations. Source builds still need
their own build/interpreter checks; a pure-Python sdist need not require a C compiler.

## Independent pip check

Pip **26.3** independently accepted **135 wheel pins across the targets**.
For the **2 source/missing cells**, individual `--only-binary=:all:` checks exited 1 with
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
  --python-version 3.14 --implementation cp --abi cp314 \
  "${platform_flags[@]}" -r linux-x86_64-pins.txt --report pip-linux.json
```

For a gap, replace `-r ... --report ...` with its single exact pin from the table. The checks above compared
pip’s selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No project code, model, service, database, browser or hardware was run. New uploads can change these results.
