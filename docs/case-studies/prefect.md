# Prefect: a Python 3.14 Linux wheel-only check

[Prefect](https://github.com/PrefectHQ/prefect) is a workflow orchestration framework. This study pins revision
[`ed96dafb35df5b7e09ef38c5a037d6f280fb5517`](https://github.com/PrefectHQ/prefect/tree/ed96dafb35df5b7e09ef38c5a037d6f280fb5517),
uses **wheelgap 0.13.0**, and records package availability checked on **20 November 2026**.

## Input, selection and targets

The input is the unchanged [uv.lock](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/uv.lock), with its adjacent
[pyproject.toml](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/pyproject.toml).
Among the pinned workflows that name Python 3.14 are:

- the [python-tests.yaml workflow](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/.github/workflows/python-tests.yaml#L98-L107),
  which runs the test suite on `ubuntu-latest` for Python 3.11 through 3.15, after `uv sync --locked`;
- the [docker-images.yaml workflow](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/.github/workflows/docker-images.yaml#L131),
  which builds images for Python 3.11 through 3.15 on `linux/amd64` and `linux/arm64`.

This study checks Python 3.14 on `linux-x86_64` and `linux-aarch64`, with wheelgap's default glibc floor **2.36**;
that is an explicit floor, not a measurement of the hosted runner's or the image's libc. The
[windows-tests.yaml workflow](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/.github/workflows/windows-tests.yaml#L47-L50)
tests Python 3.11, 3.12 and 3.15 on Windows, not 3.14, so Windows is outside this study, as are the other Python
versions in these matrices.

The main scan selects Prefect's runtime dependencies (`--no-dev`). The test job's `uv sync --locked` also installs
the `dev` group; that wider selection is checked [below](#the-dev-group). Prefect's database, services, workers and
integrations, and the image build itself, are outside this wheel-only check.

## Reproduce

Download both pinned input files into an empty directory:

```bash
curl -fL https://raw.githubusercontent.com/PrefectHQ/prefect/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/uv.lock -o uv.lock
curl -fL https://raw.githubusercontent.com/PrefectHQ/prefect/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/pyproject.toml -o pyproject.toml
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.14 -t linux-x86_64,linux-aarch64 --glibc 2.36 --no-dev \
  --json --explain --suggest --no-cache > report.json
```

The scan exited **0**. Its JSON summary, one row per target, was:

| Target | Wheel | Source | Missing | N/A | Unknown |
| --- | ---: | ---: | ---: | ---: | ---: |
| `linux-x86_64` | 103 | 0 | 0 | 0 | 0 |
| `linux-aarch64` | 103 | 0 | 0 | 0 | 0 |

The report contains **103 packages**. It also lists Prefect itself under `skipped` (an editable install, not an
index package); it is not counted as a missing wheel. Without `--json`, the same scan prints:

```text
wheelgap 0.13.0 · uv.lock · 103 packages · Python 3.14

skipped 1 non-index package: prefect (editable)
✓ All 103 packages have a wheel for every one of 2 targets.
```

There were no source, missing or unknown cells and no gap-specific upgrade suggestions. No dependency change is proposed.

The [Dockerfile](https://github.com/PrefectHQ/prefect/blob/ed96dafb35df5b7e09ef38c5a037d6f280fb5517/Dockerfile#L200)
installs Prefect with `PREFECT_EXTRAS=[redis,client,otel]` by default. `redis` and `otel` are extras in
`pyproject.toml` (`client` is not, so wheelgap rejects `--extra client`); adding `--extra redis --extra otel` gives
**124 packages**, again all wheels on both targets. The image
installs from an exported constraints file rather than from `uv.lock` directly, so this is an approximation of
the image's package set, not a check of the image.

### The dev group

The test job's `uv sync --locked` installs the runtime dependencies plus uv's default `dev` group. Replacing
`--no-dev` with `--group dev` gives that selection: **211 packages** on `linux-x86_64`, the test job's platform, and
the scan exited **1** with one gap:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.14 -t linux-x86_64 --glibc 2.36 \
  --group dev --explain --suggest --no-cache
```

```text
wheelgap: add --notes to show the tracker's notes for these packages (sends their names to wheelgap.github.io)
wheelgap 0.13.0 · uv.lock · 211 packages · Python 3.14

package                 version  linux-x86_64
testslide (via typsht)  2.7.1    ● source

210 packages with wheels for every target hidden (--all to show)

testslide 2.7.1 on linux-x86_64: ● source
  via: (dev group) → typsht → pyre-check → testslide
  no wheels published for this version

testslide 2.7.1: no newer release has a wheel for linux-x86_64

skipped 1 non-index package: prefect (editable)
1 of 211 packages has gaps: 1 will build from source.
```

TestSlide 2.7.1 publishes only an sdist, so uv builds it locally on any target and Python; this is not specific to
Python 3.14. It comes from the `dev` group, not from Prefect's runtime requirements.

## Independent pip check

Pip **26.3** independently accepted all **103 wheel pins on each of the two targets**, all 124 pins of the
extras selection on each target, and the 210 wheel pins of the dev-group selection on `linux-x86_64`. For the
dev-group gap, a single-pin `--only-binary=:all:` check of `testslide==2.7.1` exited 1 with
`No matching distribution found`. That confirms absence of an eligible wheel, not whether a source build works.

To reproduce the wheel-only batches, extract pins by target from `report.json`:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text(encoding="utf-8"))
for target in ("linux-x86_64", "linux-aarch64"):
    pins = [f"{p['name']}=={p['version']}" for p in report["packages"] if p["results"].get(target) == "wheel"]
    Path(f"{target}-pins.txt").write_text("\n".join(pins) + "\n", encoding="utf-8")
```

For x86_64, pass every accepted manylinux tag, including the legacy aliases:

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

For aarch64, change the architecture, stop the loop at 17 (`{36..17}`), and follow it with only
`manylinux2014_aarch64` and `linux_aarch64`, since there are no older manylinux tags for that architecture; use
`linux-aarch64-pins.txt`.

For a gap, replace `-r ... --report ...` with its single exact pin. The checks above compared
pip’s selected package names and versions with the wheelgap rows and confirmed that every selected file was a wheel.
`--no-deps` deliberately does not validate consistency of the whole environment or activate project extras/groups.
No Prefect code was run. New uploads can change these results.
