# Poetry: test groups versus main on Python 3.15

[Poetry](https://github.com/python-poetry/poetry) is a Python dependency-management CLI. This study pins revision
[`406ff8932e8775e1a82cea9f7f85c4b4b651eec7`](https://github.com/python-poetry/poetry/tree/406ff8932e8775e1a82cea9f7f85c4b4b651eec7),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [poetry.lock](https://github.com/python-poetry/poetry/blob/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/poetry.lock), with its adjacent
[pyproject.toml](https://github.com/python-poetry/poetry/blob/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/pyproject.toml). The [tests.yaml workflow](https://github.com/python-poetry/poetry/blob/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/.github/workflows/tests.yaml)
names Python 3.15 and the OS jobs modeled here: `linux-x86_64,win-amd64`. Linux is modeled as x86_64 with
glibc **2.36**; this is an explicit wheelgap floor, not a measurement of the hosted runner’s libc.

The PyYAML gap is in the lock’s `dev` and `test` groups. Removing `dev` does not remove the non-optional `test` group: this is not evidence that installing only Poetry’s main dependencies requires a source build.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/python-poetry/poetry/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/poetry.lock -o poetry.lock
curl -fL https://raw.githubusercontent.com/python-poetry/poetry/406ff8932e8775e1a82cea9f7f85c4b4b651eec7/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock \
  -p 3.15 -t linux-x86_64,win-amd64 --glibc 2.36 --no-dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **1**. Counts below are package/version rows, not necessarily unique names:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 63 | 1 | 0 | 2 | 0 |
| `win-amd64` | 60 | 1 | 0 | 5 | 0 |

The report contains **66 rows**.

## Gaps and options

| Locked pin | Affected targets | `--explain` evidence |
| --- | --- | --- |
| `pyyaml==6.0.3` | `linux-x86_64` (source), `win-amd64` (source) | built for cp314-cp314, not CPython 3.15 |

Running the same scan without `--json` exposes the human-readable `--explain --suggest` details:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock -p 3.15 \
  -t linux-x86_64,win-amd64 --glibc 2.36 --no-dev --explain --suggest --no-cache
```

- `pyyaml==6.0.3`: this scan printed no upgrade suggestion. A source build or a separately checked environment/selection change remains an option.

Every newer-version suggestion listed above was separately checked with pip on this Linux/Python target.
A matching wheel is not proof of dependency or application compatibility: re-resolve and test any upgrade.
Historical wheel versions printed by `--suggest` are not downgrade recommendations. Source builds still need
their own build/interpreter checks; a pure-Python sdist need not require a C compiler.

### A narrower group selection

Changing the selector to `--only-group main` (instead of the flags above) produced
**46 rows and no gaps** on the same two targets. Its wheel pins are a subset of the pip-verified set.
The command was `uvx --from wheelgap==0.13.0 python -m wheelgap poetry.lock -p 3.15 -t linux-x86_64,win-amd64 --only-group main --json --explain --suggest`.
Use that selection only when it describes what you intend to install; it omits the other groups, not just their gaps.

## Independent pip check

Pip **26.3** independently accepted **123 wheel pins across the targets**.
For the **2 source/missing cells**, individual `--only-binary=:all:` checks exited 1 with
`No matching distribution found`. That confirms absence of an eligible wheel, not whether a source build works.

To reproduce the wheel-only batches, extract pins by target from `report.json`:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64", "win-amd64"):
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

For a gap, replace `-r ... --report ...` with its single exact pin from the table. The checks above compared
pip’s selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No project code, model, service, database, browser or hardware was run. New uploads can change these results.
