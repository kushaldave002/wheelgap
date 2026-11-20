# HERD: a 136-package service platform on ARM, Alpine and Windows on ARM

[HERD](https://github.com/vendrabuck/HERD) (Hardware Environment Replication and Deployment) is a lab reservation and topology platform: twelve FastAPI services and a shared `herd-common` package in one `uv` workspace, each service built into its own image, plus a React frontend. This case study checks its locked dependency set at revision [`9a4b4f6852f44eeffe258d7a5b836e88d0e88353`](https://github.com/vendrabuck/HERD/tree/9a4b4f6852f44eeffe258d7a5b836e88d0e88353) (merged 19 November 2026). The scan used **wheelgap 0.13.0** and the package files available on **19 November 2026** (UTC−03).

The result: 136 registry packages checked (the lock has 137; `httpx2-jsfetch` only applies on Emscripten), **4 with gaps**, none missing. Three of the four are in the `dev` group, so they affect a developer machine or CI runner on those targets, not the running images. The fourth is a runtime dependency, and it is the interesting one.

## Targets and selection

HERD's [CI](https://github.com/vendrabuck/HERD/blob/9a4b4f6852f44eeffe258d7a5b836e88d0e88353/.github/workflows/ci.yml#L28) runs on `ubuntu-latest` and pins Python **3.12**, and every service's image is built from `python:3.12.16-slim` ([`services/auth/Dockerfile`](https://github.com/vendrabuck/HERD/blob/9a4b4f6852f44eeffe258d7a5b836e88d0e88353/services/auth/Dockerfile)) with no multi-platform build. HERD builds and tests only on Linux x86_64. The scan uses 3.12 to match.

On that configured platform the lock is clean: the baseline run below reports a wheel for every package on `linux-x86_64`. So this study is a portability check beyond HERD's configured platform. It asks what happens if the stack moves to platforms it doesn't target yet:

- `linux-aarch64` — ARM Linux hosts.
- `musl-x86_64` — Alpine. HERD already runs Alpine images for its infrastructure containers (`postgres:16.15-alpine`, `nats:2.10.29-alpine` in [`docker-compose.yml`](https://github.com/vendrabuck/HERD/blob/9a4b4f6852f44eeffe258d7a5b836e88d0e88353/docker-compose.yml)), but not for its Python services.
- `win-arm64` — Windows on ARM, running a service natively.

Linux uses wheelgap's default glibc floor **2.36**; the service images are Debian slim, so that floor is conservative for them.

## Reproduce the scan

In an empty folder, take the pinned lockfile and check it on HERD's configured platform first:

```bash
curl -fL https://raw.githubusercontent.com/vendrabuck/HERD/9a4b4f6852f44eeffe258d7a5b836e88d0e88353/uv.lock -o uv.lock
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock -p 3.12 -t linux-x86_64 --no-cache
```

Output (the skipped line is shortened):

```text
wheelgap 0.13.0 · uv.lock · 134 packages · Python 3.12

skipped 13 non-index packages: herd-acl (editable), herd-ai-orchestrator (editable), herd-auth (editable), …, herd-user-profile (editable)
✓ All 134 packages have a wheel for 1 target.
```

The command exits **0**. It checks two packages fewer than the scan below because `colorama` and `pywin32` apply only on Windows.

Then check the three targets HERD doesn't build for:

```bash
uvx --from wheelgap==0.13.0 python -m wheelgap uv.lock \
  -p 3.12 -t linux-aarch64,musl-x86_64,win-arm64 \
  --explain --suggest --no-cache
```

Output:

```text
wheelgap 0.13.0 · uv.lock · 136 packages · Python 3.12

package                      version  linux-aarch64  musl-x86_64  win-arm64
cryptography                 50.0.2   ✓              ✓            ● source
gevent (via locust)          25.9.1   ✓              ✓            ● source
playwright                   1.65.0   ✓              ● source     ✓
zope-interface (via locust)  8.3      ✓              ● source     ● source

132 packages with wheels for every target hidden (--all to show)

skipped 13 non-index packages: herd-acl (editable), herd-ai-orchestrator (editable), herd-auth (editable), …, herd-user-profile (editable)
musl-x86_64  2 from source
win-arm64    3 from source
4 of 136 packages have gaps: 4 will build from source.
```

The output above is trimmed: the full run also prints a one-line hint about `--notes` before the header, the `--explain` reasons and `--suggest` lines between the table and the summary (the ones that matter are quoted below), and the skipped line is shortened. The command exits **1**. The 13 skipped packages are HERD's own workspace members, installed editable; they are not on any index, and wheelgap says so rather than guessing.

## The runtime gap: `cryptography` on Windows on ARM

`cryptography` is the one gap in a runtime dependency. wheelgap's `via` line shows it arriving through `herd-secrets`, and the lock also reaches it from `herd-auth` (`pyjwt[crypto]`), `herd-execution` (`netmiko` → `paramiko`) and `herd-ai-orchestrator` (`pdfplumber` → `pdfminer-six`). It has a wheel for `linux-aarch64` and `musl-x86_64` but not for `win-arm64`, so the gap doesn't affect the Linux service images; it matters only when a service runs natively on a Windows on ARM machine. Every candidate is rejected because it is an x64 or a non-Windows build:

```text
cryptography 50.0.2 on win-arm64: ● source
  via: herd-secrets → cryptography
  cryptography-50.0.2-cp311-abi3-win_amd64.whl                                     win_amd64 doesn't match win-arm64
  cryptography-50.0.2-cp314-cp314t-win_amd64.whl                                   win_amd64 doesn't match win-arm64
  cryptography-50.0.2-cp315-abi3.abi3t-win_amd64.whl                               win_amd64 doesn't match win-arm64
  cryptography-50.0.2-cp39-abi3-win_amd64.whl                                      win_amd64 doesn't match win-arm64
  cryptography-50.0.2-cp311-abi3-macosx_11_0_arm64.whl                             macosx_11_0_arm64 doesn't match win-arm64
  cryptography-50.0.2-cp311-abi3-manylinux2014_aarch64.manylinux_2_17_aarch64.whl  manylinux_2_17_aarch64 doesn't match win-arm64
  cryptography-50.0.2-cp311-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl    manylinux_2_17_x86_64 doesn't match win-arm64
  cryptography-50.0.2-cp311-abi3-manylinux_2_28_aarch64.whl                        manylinux_2_28_aarch64 doesn't match win-arm64
  … and 44 more (--json lists them all)

cryptography 50.0.2: no newer release has a wheel for win-arm64; the last one that did is 46.0.3
```

This one isn't a package that never had the wheel: `cryptography` published `win_arm64` wheels for 46.0.0 through 46.0.3 and stopped with 46.0.4, and 50.0.2 ships `win_amd64` as its only Windows build. wheelgap's `--suggest` finds no newer release that closes it, so the options are the ones the flag exists to present:

- hold `cryptography` at 46.0.3, the last release with a `win_arm64` wheel, which means lowering herd-secrets' own `cryptography>=50.0.0` floor ([`services/secrets/pyproject.toml`](https://github.com/vendrabuck/HERD/blob/9a4b4f6852f44eeffe258d7a5b836e88d0e88353/services/secrets/pyproject.toml#L12)) and giving up every fix released since;
- build it in CI for `win-arm64` and install the result, which is what a locked image build does when no wheel exists;
- run the Windows node under x64 emulation, where the published wheel applies;
- or accept the source build on that one target.

The other three gaps are all in the `dev` group, so they never reach an image:

- `gevent` and `zope-interface` come through `locust`, the load-test tool. `--suggest` names **gevent 26.5.0** and **zope-interface 8.4** as releases with a `win-arm64` wheel, so a lock refresh closes `win-arm64`. It doesn't close `musl-x86_64`: no `zope-interface` release has ever published a musllinux wheel, so on Alpine it stays a source build.
- `playwright` has no musllinux wheel at all — it ships `manylinux` (glibc) and `win`/`macosx` builds. That is a property of the package, not of HERD: an Alpine-based developer image that installs Playwright has to build it, and the service images avoid the question by being Debian.

## Why this is a good lockfile

The thirteen packages wheelgap skips are the workspace itself, and every package it checks installs from a wheel on `linux-aarch64` as well as on the configured `linux-x86_64`, so a move to ARM Linux needs no source builds at all. HERD's images are built lock-faithful: `uv export --frozen --package herd-<service> --no-hashes --no-emit-workspace --no-default-groups --no-header -o requirements.txt` turns `uv.lock` into a plain `requirements.txt` per service, so every version an image installs is one the scan above checked. An image installs less than the scan covers, though: one service's runtime dependencies, without the `dev` group.

The four gaps are also honestly placed. Nothing is missing, so no target fails outright; the one runtime gap is on Windows on ARM only, where `cryptography` stopped publishing wheels, and the rest are developer tooling. For a project that runs in containers, that is the profile the tool is meant to confirm rather than to alarm about.
