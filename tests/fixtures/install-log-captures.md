# Poetry and PDM failure logs

Captured on macOS ARM64 for wheelgap issue #463, with `pyaudio==0.2.14`.
Poetry 2.5.1 (Python 3.14) and PDM 2.29.7 (Python 3.12) both exited 1 because
`portaudio.h` was missing. Commands: `poetry install --no-interaction --no-ansi`,
the same with `-v`, `pdm install --no-self`, and the same with `-v`.

These are trimmed captures: irrelevant warning text, internal traceback frames,
and compiler commands containing local paths were removed. Diagnostic lines are
unchanged. Complete sanitized captures are in
https://github.com/wheelgap/wheelgap/issues/463#issuecomment-6964534807.
PDM's normal log intentionally has no provenance; it must be refused.
