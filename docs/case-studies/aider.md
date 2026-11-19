# Aider: Python 3.14 wheels on Linux and Windows

[Aider](https://github.com/Aider-AI/aider) is a terminal-based coding assistant. This study checks revision
[`5dc9490bb35f9729ef2c95d00a19ccd30c26339c`](https://github.com/Aider-AI/aider/tree/5dc9490bb35f9729ef2c95d00a19ccd30c26339c),
using wheelgap **0.13.0** and package files available on **17 November 2026** (US Eastern time).

The result is an example of an all-wheel dependency list that still needs system libraries. No dependency change
is suggested: the checked requirements have wheels on both selected targets.

## Input and target evidence

The pinned [project metadata](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/pyproject.toml)
requires Python `>=3.10,<3.15` and takes its dependencies from the root `requirements.txt`. Its
[Ubuntu](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/.github/workflows/ubuntu-tests.yml)
and [Windows](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/.github/workflows/windows-tests.yml)
test workflows each include Python 3.14 on hosted x86_64 runners. This study checks those two Python 3.14 cells,
not the entire CI matrix. Linux uses wheelgap's default glibc floor **2.36**; it does not measure the runner's
installed libc or claim compatibility with every Linux distribution.

The unchanged [requirements file](https://github.com/Aider-AI/aider/blob/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/requirements.txt)
is mostly pinned, with Python-specific ranges for NumPy, SciPy and audioop-lts. On Python 3.14, this scan selected
**numpy 2.4.6**, **scipy 1.17.1** and **audioop-lts 0.2.2**. These range selections can change without an Aider commit.
The result covers the packages listed in that compiled requirements file. It does not resolve a fresh dependency
tree, validate dependency constraints or install Aider itself.

## Reproduce the scan

In an empty folder, download the pinned file and check it:

```bash
curl -fL https://raw.githubusercontent.com/Aider-AI/aider/5dc9490bb35f9729ef2c95d00a19ccd30c26339c/requirements.txt -o requirements.txt
uvx --from wheelgap==0.13.0 python -m wheelgap requirements.txt \
  -p 3.14 -t linux-x86_64,win-amd64 --glibc 2.36 \
  --json --explain --suggest --no-cache > report.json
```

The command exited **0**. Its JSON summary, one row per target, was:

| Python | Packages | Target | Source | Missing | Unknown |
| --- | ---: | --- | ---: | ---: | ---: |
| 3.14 | 107 | linux-x86_64 | 0 | 0 | 0 |
| 3.14 | 107 | win-amd64 | 0 | 0 | 0 |

All 214 package/target cells were `wheel`. Native-code dependencies such as **cffi 2.0.0**,
**pydantic-core 2.41.5**, **tokenizers 0.22.2**, NumPy and SciPy also had wheels on both targets.
There were no rejected gap cells to explain and no wheel-gap upgrade to recommend. stderr noted the three
unpinned packages and that the newest matching releases had been checked.

## Independent check with pip

To keep the range selections fixed, extract each target's exact versions from the JSON snapshot:

```python
import json
from pathlib import Path

report = json.loads(Path("report.json").read_text())
for target in ("linux-x86_64", "win-amd64"):
    pins = [
        f"{package['name']}=={package['version']}"
        for package in report["packages"]
        if package["results"].get(target) == "wheel"
    ]
    Path(f"{target}-pins.txt").write_text("\n".join(pins) + "\n")
```

The pins files list only `wheel` cells, so if a re-run reports any `source` or `missing` package, it is left out of the pip check: compare the pip count with the wheelgap package count, as below.

This verification used pip **26.3**. Windows needs one platform tag:

```bash
uvx --from pip==26.3 python -m pip --isolated --disable-pip-version-check install \
  --dry-run --ignore-installed --no-deps --only-binary=:all: \
  --index-url https://pypi.org/simple --python-version 3.14 --implementation cp --abi cp314 \
  --platform win_amd64 --report pip-win-amd64.json -r win-amd64-pins.txt
```

For glibc 2.36, pip's explicit cross-platform check needs the full accepted manylinux platform list, including
the older aliases. In Bash:

```bash
platform_flags=()
for minor in {36..5}; do
  platform_flags+=(--platform "manylinux_2_${minor}_x86_64")
done
platform_flags+=(--platform manylinux2014_x86_64 --platform manylinux2010_x86_64)
platform_flags+=(--platform manylinux1_x86_64 --platform linux_x86_64)
uvx --from pip==26.3 python -m pip --isolated --disable-pip-version-check install \
  --dry-run --ignore-installed --no-deps --only-binary=:all: \
  --index-url https://pypi.org/simple --python-version 3.14 --implementation cp --abi cp314 \
  "${platform_flags[@]}" --report pip-linux-x86_64.json -r linux-x86_64-pins.txt
```

Both dry runs exited **0** and selected **107 wheels**. Their reports matched the package names and exact
versions in the corresponding wheelgap snapshot. `--no-deps` intentionally checks these recorded package files;
it does not prove the pins form a consistent environment. No Aider code or model was run.

## What an all-wheel result does not promise

The Ubuntu test workflow still installs `libportaudio2` through apt before installing the Python package.
A `sounddevice` wheel does not remove that system-library step. Wheelgap checks Python distribution availability,
not audio hardware, native-library loading, external programs, model access or application behavior.

Keep the project's system-dependency setup and test suite. To repeat this availability check after an update,
use the new requirements file and record its revision and any range selections again. A different Python,
architecture or glibc floor needs its own check; these results are not evidence for Windows on ARM,
free-threaded Python or older Linux images.
