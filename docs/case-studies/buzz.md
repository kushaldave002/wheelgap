# Buzz: speech-to-text dependencies across three desktop targets

[Buzz](https://github.com/chidiwilliams/buzz) transcribes and translates audio locally, with several speech-model backends. This study checks revision [`9eb089a5f0f720a35bf1664c6e38f80fad6e3986`](https://github.com/chidiwilliams/buzz/tree/9eb089a5f0f720a35bf1664c6e38f80fad6e3986) with wheelgap **0.13.0**, using package files available on **18 November 2026**. It checks dependency artifacts without installing Buzz or its ML runtimes.

## Choose targets from the project

The pinned [desktop build matrix](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/.github/workflows/ci.yml#L119-L139) names Linux, Windows and macOS. The [wheel-build matrix](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/.github/workflows/ci.yml#L303-L312) pins Ubuntu 24.04 for Linux; the [build hook](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/hatch_build.py#L24-L50) supports Linux and Windows x86_64 and gives Apple-silicon wheels a `macosx_11_0_arm64` tag. The [installation notes](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/README.md#L36-L53) say current Buzz requires Apple silicon, so Intel macOS is left out.

This gives three artifact-check targets: `linux-x86_64` with glibc **2.39** (Ubuntu 24.04), `win-amd64`, and `macos-arm64` at **11.0**, the macOS floor named by the build hook. This does not equate `macos-latest`, a moving CI runner label, with macOS 11. A second scan at macOS 15.0 separates the older-OS gaps from packages that publish no wheels at all.

[`.python-version`](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/.python-version) selects **3.13**, [the project](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/pyproject.toml#L7) requires `>=3.13,<3.14`, and [the lockfile](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/uv.lock#L1-L13) records `==3.13.*`. The workflow's setup-python step still names 3.12; this study follows the project and lockfile's 3.13, rather than claiming to reproduce that workflow end to end.

## Reproduce the scan

Use an empty temporary directory and download **only the lockfile**, without an adjacent `pyproject.toml`:

```bash
cd "$(mktemp -d)"
curl -fL https://raw.githubusercontent.com/chidiwilliams/buzz/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/uv.lock -o uv.lock
uvx --from wheelgap==0.13.0 wheelgap uv.lock \
  -p 3.13 -t linux-x86_64,macos-arm64,win-amd64 \
  --glibc 2.39 --macos 11.0 --no-dev --explain --suggest
```

With only the lockfile, `--no-dev` checks the project's runtime dependency graph without development/build groups. This isolation matters: Buzz's [adjacent manifest](https://github.com/chidiwilliams/buzz/blob/9eb089a5f0f720a35bf1664c6e38f80fad6e3986/pyproject.toml#L108-L131) normally selects both `dev` and `build` by default; scanning inside a full checkout with only `--no-dev` would retain `build`. Packages declared in `[project.dependencies]`, even if they look like build tools, remain runtime roots in this study. The editable `buzz-captions` root itself is skipped.

Trimmed output (the complete report lists each package and its rejected wheels):

```text
wheelgap 0.13.0 · uv.lock · 256 packages · Python 3.13

package                                      version   linux-x86_64  macos-arm64  win-amd64
antlr4-python3-runtime (via nemo-toolkit-asr)  4.9.3     ● source      ● source     ● source
av (via faster-whisper)                      16.0.1    ✓             ● source     ✓
bitsandbytes                                 0.49.0    –             ✗ missing    –
onnxruntime                                  1.20.0    ✓             ✗ missing    ✓
openai-whisper                               20250625  ● source      ● source     ● source
torchcodec                                   0.16.0    ✓             ✗ missing    ✓
...
skipped 1 non-index package: buzz-captions (editable)
linux-x86_64  11 from source
macos-arm64   19 from source, 3 missing
win-amd64     11 from source
22 of 256 packages have gaps: 19 will build from source, 3 can't install at all.
```

The scan exits **1**, as expected when gaps exist. `–` means the locked package variant is not selected on that target; it does not mean a missing wheel. The lock records a separate bitsandbytes version for Linux/Windows.

## Eleven pins have no wheels on any of the targets

None of these pins has a CPython 3.13 wheel in the lock, and pip independently finds none for all three targets:

| Pin | One dependency path from Buzz |
| --- | --- |
| `antlr4-python3-runtime==4.9.3` | `nemo-toolkit-asr → hydra-core` |
| `docopt==0.6.2` | `nemo-toolkit-asr → pyannote-metrics` |
| `editdistance==0.8.1` | `nemo-toolkit-asr` (wheels on PyPI stop at cp312) |
| `intervaltree==3.1.0` | `lhotse` (also reached through NeMo) |
| `julius==0.2.7` | `demucs` |
| `kaldi-python-io==1.2.2` | `nemo-toolkit-asr` |
| `openai-whisper==20250625` | Direct dependency |
| `sox==1.5.0` | `nemo-toolkit-asr` |
| `srt==3.5.3` | `srt-equalizer` |
| `stable-ts==2.19.1` | Direct dependency |
| `wget==3.2` | `nemo-toolkit-asr` |

Most of these releases publish no wheels at all. editdistance 0.8.1 is the exception: it has wheels on PyPI up to CPython 3.12, but none for 3.13, and uv leaves wheels that can't serve the lock's `requires-python` out of `uv.lock`. It is also the one pin here with a C++ extension, so building it needs a compiler.

A `source` result means an sdist is available, not that native compilation is necessarily required or that a build will fail. Retaining these pins means validating the source-build path in packaging CI, including any system tools each package needs.

`--suggest` finds wheels on all three targets for **intervaltree 3.2.1**, **julius 0.2.8**, and **antlr4-python3-runtime 4.11.0**. pip confirms those nine candidate cells. These are artifact-availability suggestions, not a solved dependency update: in particular, [Hydra 1.3.2](https://pypi.org/pypi/hydra-core/1.3.2/json) and [omegaconf 2.3.0](https://pypi.org/pypi/omegaconf/2.3.0/json) both require `antlr4-python3-runtime==4.9.*` in their published metadata, so directly overriding it with 4.11.0 violates both requirements. Any change must go through the project's resolver and compatibility tests; a compatible upstream dependency update may be needed.

For the other eight pins, no newer release with a suitable wheel was found. The older wheels mentioned for `kaldi-python-io` and `sox` are not a reason to downgrade a working dependency graph blindly. Keeping the source build is a valid option; removing a backend would be a separate product decision, not an automatic wheelgap fix.

## Eleven more packages have macOS-version gaps

These pins have Apple-silicon wheels, but the closest compatible-Python wheel requires a newer macOS than 11.0:

| Pin | macOS 11 result | Wheel's macOS floor |
| --- | --- | --- |
| `av==16.0.1` | source | 14.0 |
| `bitsandbytes==0.49.0` | missing | 14.0 |
| `llvmlite==0.49.0` | source | 12.0 |
| `numba==0.67.0` | source | 12.0 |
| `onnx==1.20.0` | source | 12.0 |
| `onnxruntime==1.20.0` | missing | 13.0 |
| `pyarrow==22.0.0` | source | 12.0 |
| `scikit-learn==1.7.2` | source | 12.0 |
| `scipy==1.16.3` | source | 12.0 |
| `torchcodec==0.16.0` | missing | 14.0 |
| `wandb==0.23.1` | source | 12.0 |

For example, the report rejects:

```text
onnxruntime-1.20.0-cp313-cp313-macosx_13_0_universal2.whl
macosx_13_0_universal2 needs macOS 13.0, newer than 11.0 (--macos)
```

`missing` means the selected pin has neither a suitable wheel nor an sdist recorded for that target. The source-build fallback available for the other eight packages is therefore not an option for these three pins as recorded.

Repeating the scan with **`--macos 15.0`** leaves only the eleven common source-only packages: 11 source results per target, no missing or unknown results. This is evidence that the extra macOS gaps are OS-version gaps, not an absence of Apple-silicon wheels. Practical choices are to validate a newer deployment floor, resolve compatible releases that support the older floor, or maintain and test appropriate builds. This scan does not establish which choice is right for Buzz or prove the application's minimum supported macOS version.

## Independent pip verification and limits

pip **26.3** checked all **44 reported gap cells** (33 common-source cells plus 11 additional macOS cells) with no matching binary distribution; it also found wheels for the **nine newer-candidate cells** above. All **53 checks** fetched the public PyPI project page successfully, without retry/fetch errors. They used `--isolated --dry-run --ignore-installed --no-deps --only-binary=:all:`, `--python-version 3.13 --implementation cp --abi cp313`, and each target's platform tags.

For example:

```bash
uvx --from pip==26.3 python -m pip --isolated install \
  --dry-run --ignore-installed --no-deps --only-binary=:all: \
  --index-url https://pypi.org/simple \
  --python-version 3.13 --implementation cp --abi cp313 \
  --platform macosx_11_0_arm64 'onnxruntime==1.20.0'
```

That reports `No matching distribution found`. Changing the platform to `macosx_15_0_arm64` checks the newer-OS scenario. For Windows the platform is `win_amd64`. Linux checks pass every `manylinux_2_N_x86_64` tag from **2.39 down to 2.5**, plus `manylinux2014_x86_64`, `manylinux2010_x86_64`, `manylinux1_x86_64` and `linux_x86_64`; one modern manylinux tag alone would miss older compatible wheels. pip widens macOS tags itself.

These cross-platform checks ran on macOS ARM64; they did not install or compile the packages. The scan uses the lock's recorded file lists, including its explicit PyTorch CPU index on Linux/Windows; those non-PyPI packages were not sent to PyPI for this independent gap verification. An available wheel does not prove runtime compatibility, and wheelgap does not validate Buzz's bundled native extensions, FFmpeg, GPU setup or completed installers. New uploads and lockfile changes can change the results.
