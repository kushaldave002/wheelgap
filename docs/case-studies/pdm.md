# PDM: default dependencies versus documentation and optional groups

[PDM](https://github.com/pdm-project/pdm) is a Python package and dependency manager. This case study checks the locked **test environment** its CI installs, and compares it with its runtime dependencies and with the whole lockfile, at revision [`9af22ebcd76e966f4cbdddd2d50f2ebcf8b727bd`](https://github.com/pdm-project/pdm/tree/9af22ebcd76e966f4cbdddd2d50f2ebcf8b727bd). The scan used **wheelgap 0.13.0** and package files available on **20 November 2026**.

On CPython 3.15, the test environment has one gap on all three CI platforms: the locked MarkupSafe 3.0.3 has no CPython 3.15 wheel, so it would build from source, while MarkupSafe 3.0.4 has one. PDM's runtime dependencies have wheels everywhere. The rest of the lockfile, mostly the documentation toolchain, adds three more gaps.

## Targets and selection

The pinned [CI matrix](https://github.com/pdm-project/pdm/blob/9af22ebcd76e966f4cbdddd2d50f2ebcf8b727bd/.github/workflows/ci.yml#L32-L44) runs the tests on `ubuntu-latest`, `windows-latest` and `macos-latest` for CPython 3.10 through 3.15, plus PyPy 3.11 and a script-install job on Ubuntu. This study checks the CPython 3.15 jobs on:

- `linux-x86_64` and `win-amd64`, the x64 Linux and Windows runners.
- `macos-arm64`, the Apple-silicon runner. The workflow's `macos-latest` label alone doesn't establish the runner's architecture; across GitHub-hosted images it is ARM today, and this study says so rather than assuming it for every reader.

Linux uses wheelgap's default glibc floor **2.36**; it doesn't measure the runner's installed libc.

Each job installs PDM from the checkout with `python -m pip install -U .`, which resolves its runtime dependencies from PyPI, and then installs the development environment from the lockfile with `pdm install -v -Gtest` ([ci.yml:77-86](https://github.com/pdm-project/pdm/blob/9af22ebcd76e966f4cbdddd2d50f2ebcf8b727bd/.github/workflows/ci.yml#L77-L86)): the `default` group plus the `test` group. The wheelgap command below selects the same two groups from the [pinned `pdm.lock`](https://github.com/pdm-project/pdm/blob/9af22ebcd76e966f4cbdddd2d50f2ebcf8b727bd/pdm.lock). The `test` group pulls in PDM's own `pytest` extra (`pdm[pytest]`); adding `--only-group pytest` selects the same 50 packages.

## Reproduce the scan

In an empty folder, download the pinned lockfile and check it:

```bash
curl -fL https://raw.githubusercontent.com/pdm-project/pdm/9af22ebcd76e966f4cbdddd2d50f2ebcf8b727bd/pdm.lock -o pdm.lock
uvx --from wheelgap==0.13.0 python -m wheelgap pdm.lock \
  -p 3.15 -t linux-x86_64,win-amd64,macos-arm64 \
  --only-group default --only-group test --explain --suggest --no-cache
```

Trimmed output (each `--explain` block lists 8 of its 77 rejected wheels before `… and 69 more`; one line is kept here, and the Windows and macOS blocks, which read the same, are omitted):

```text
wheelgap: note: --suggest didn't look up 1 package whose index isn't known to be PyPI (markupsafe), so their names stay private
wheelgap 0.13.0 · pdm.lock · 50 packages · Python 3.15

package     version  linux-x86_64  win-amd64  macos-arm64
markupsafe  3.0.3    ● source      ● source   ● source

49 packages with wheels for every target hidden (--all to show)

markupsafe 3.0.3 on linux-x86_64: ● source
  markupsafe-3.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl   built for cp314-cp314, not CPython 3.15
  … and 69 more (--json lists them all)

linux-x86_64  1 from source
win-amd64     1 from source
macos-arm64   1 from source
1 of 50 packages has gaps: 1 will build from source.
```

The scan exits **1**, which wheelgap uses to report a wheel gap, not a command failure.

## MarkupSafe 3.0.3: a Python-version gap

MarkupSafe 3.0.3 publishes wheels for CPython 3.10 through 3.14 (and 3.13t and 3.14t), but none tagged for 3.15, and a `cp314` wheel can't be used by `cp315`. It has an sdist, so wheelgap says `source`, not `missing`. In the `test` group it comes in through `werkzeug` 3.1.8 (`markupsafe>=2.1.1`), which `pytest-httpserver` needs.

`--suggest` printed no upgrade here, and the note at the top says why: at this pin, `pdm.lock` lists each package's file names and hashes but not the index they came from, so wheelgap doesn't send the names to PyPI. Checking the name on its own, as a package spec, does look it up:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap markupsafe==3.0.3 \
  -p 3.15 -t linux-x86_64,win-amd64,macos-arm64 --explain --suggest --no-cache
```

That run prints, among the same `--explain` lines:

```text
markupsafe 3.0.3 -> 3.0.4 has wheels for linux-x86_64, win-amd64, macos-arm64
```

MarkupSafe 3.0.4 (2 October 2026) publishes `cp315` and `cp315t` wheels, and `werkzeug`'s requirement allows it, so re-locking with 3.0.4 would close the gap on all three targets; as with any upgrade, the tests are what show it works. Until then, the 3.15 jobs need MarkupSafe to build from its sdist.

## The runtime dependencies on their own

`--only-group default` narrows the check to what installing PDM pulls in:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap pdm.lock \
  -p 3.15 -t linux-x86_64,win-amd64,macos-arm64 --only-group default --explain --suggest --no-cache
```

```text
wheelgap 0.13.0 · pdm.lock · 37 packages · Python 3.15

✓ All 37 packages have a wheel for every one of 3 targets.
```

This exits **0**. It describes the locked versions; CI's `pip install -U .` step resolves the same requirements from PyPI and can pick newer ones.

## What the whole lockfile also reports

With no selection flags, wheelgap checks every group in the lockfile (`default`, `all`, `doc`, `keyring`, `pytest`, `test`, `tox` and `workflow`). `--no-dev` changes nothing here, because the lockfile has no group named `dev`; it selects the same 91 packages.

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap pdm.lock \
  -p 3.15 -t linux-x86_64,win-amd64,macos-arm64 --explain --suggest --no-cache
```

Trimmed output (the gap table and summary; the `--explain` blocks are omitted):

```text
wheelgap 0.13.0 · pdm.lock · 91 packages · Python 3.15

package     version  linux-x86_64  win-amd64  macos-arm64
cffi        2.0.0    ● source      –          –
markupsafe  3.0.3    ● source      ● source   ● source
pyyaml      6.0.3    ● source      ● source   ● source
watchdog    6.0.0    ✓             ✓          ● source

87 packages with wheels for every target hidden (--all to show)

linux-x86_64  3 from source
win-amd64     2 from source
macos-arm64   3 from source
4 of 91 packages have gaps: 4 will build from source.
```

This run exits **1**, and its note says `--suggest` didn't look up the four names, for the reason above. Package-spec checks like the MarkupSafe one give the rest:

- **`cffi` 2.0.0** is locked only for Linux, through `cryptography` in the `keyring` extra (and `all`), so the other targets show `–`. It has no `cp315` wheel; `--suggest` names **2.1.0** as the first release with Linux and Windows wheels for 3.15.
- **`pyyaml` 6.0.3**, in the `doc` group, has no `cp315` wheel, and `--suggest` finds no newer release with one.
- **`watchdog` 6.0.0**, in the `doc` group through `mkdocs`, has `py3-none` Linux and Windows wheels, but its macOS wheels are tagged for specific CPython versions up to 3.13; `--suggest` names **7.0.0** for `macos-arm64`.

None of these is in what the CI test job installs.

## Independent pip checks

The cells were checked against public PyPI with pip **26.3**, using `--dry-run --no-deps --only-binary=:all: --python-version 3.15 --implementation cp --abi cp315`. Windows used `--platform win_amd64`; macOS used `macosx_*_arm64` and `universal2` tags from 14.0 down; Linux used every `manylinux_2_*` tag from 2.36 down to 2.5 plus `manylinux2014`, `manylinux2010`, `manylinux1` and `linux` for `x86_64`.

- The wheel cells, one batch per target: for the CI selection, pip selected a wheel for all 49 pins on each target; for the whole lockfile, for all 87 on Linux, 84 on Windows and 82 on macOS, each time with the names and versions wheelgap reported.
- The eight `source` cells of the whole-lockfile scan, one pin at a time: each returned **No matching distribution found**. That confirms there is no usable wheel; it doesn't show whether a source build works.
- The suggested releases: `markupsafe==3.0.4` selected the `cp315-cp315` wheel on all three targets, `cffi==2.1.0` the `cp315-cp315-manylinux2014_x86_64` wheel on Linux and a `win_amd64` one on Windows, and `watchdog==7.0.0` `cp315-cp315-macosx_11_0_arm64`. `pyyaml>6.0.3` found no distribution.

For example, the Windows check of the locked MarkupSafe:

```bash
uvx --from pip==26.3 python -m pip --isolated --disable-pip-version-check install \
  --dry-run --ignore-installed --no-deps --only-binary=:all: --index-url https://pypi.org/simple \
  --python-version 3.15 --implementation cp --abi cp315 \
  --platform win_amd64 "markupsafe==3.0.3"
```

`--no-deps` checks each pin's files on its own; it doesn't check that the set resolves together. None of this runs PDM's tests or any dependency's build.
