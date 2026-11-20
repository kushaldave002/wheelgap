# Streamlit: core dependencies versus integration tests

[Streamlit](https://github.com/streamlit/streamlit) is a framework for data applications. This study pins revision
[`641d2d7d1c8c0681839f0e377cea9a615d1bab77`](https://github.com/streamlit/streamlit/tree/641d2d7d1c8c0681839f0e377cea9a615d1bab77),
uses **wheelgap 0.13.0**, and records package availability checked on **19 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/uv.lock), with its adjacent
[pyproject.toml](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/pyproject.toml). The [python-tests.yml workflow](https://github.com/streamlit/streamlit/blob/641d2d7d1c8c0681839f0e377cea9a615d1bab77/.github/workflows/python-tests.yml)
names Python 3.12 and the OS jobs modeled here: `linux-x86_64`. Linux is modeled as x86_64 with
glibc **2.36**; this is an explicit wheelgap floor, not a measurement of the hosted runner’s libc.

The repository’s `streamlit-dev` project depends on the local Streamlit package. Local/editable code is not a PyPI wheel gap. This audits the selected third-party graph, not the browser application, integration group or full test installation.

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
It separately skips **2 non-index packages** (editable/local/Git inputs); they are not counted as missing wheels.

There were no source, missing or unknown cells and no gap-specific upgrade suggestions. No dependency change is proposed.

## Independent pip check

Pip **26.3** independently accepted **33 wheel pins across the targets**.
There were no source/missing cells requiring individual rejection checks.

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
