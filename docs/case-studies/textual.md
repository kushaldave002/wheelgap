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

The scan selects the runtime dependencies plus the `syntax` extra (the tree-sitter packages) and leaves out the
`dev` group that CI also installs. An all-wheel result says nothing about terminal rendering or screenshot-test behavior.

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

## Independent pip check

Pip **26.3** independently accepted all **25 wheel pins on each of the three targets** (75 in all).

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
For macOS, pass `macosx_<v>_arm64` and `macosx_<v>_universal2` for each `<v>` from `14_0` down to `11_0`, plus
`macosx_10_<n>_universal2` for `<n>` from 16 down to 9, and use `macos-arm64-pins.txt`.

Each dry run exited **0** and selected 25 wheels whose package names and versions matched the wheelgap rows.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No Textual code was run. New uploads can change these results.
