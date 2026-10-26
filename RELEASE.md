rexsum: check-digit validation in the HTML `pattern` attribute, with no JavaScript.

## In this release

- `rexsum-<version>.tar.gz`: the source at this tag, with `LICENSE`, `patterns.json`, the
  standalone examples (`site/examples/`), the test cases (`tests/cases.json`, edge cases in
  `tests/boundary.py`), the V8 benchmark snapshot (`speed.json`, with Node and V8 versions,
  hardware and date) and the native Safari report (`reports/safari.txt`).
- `patterns.json`: every pattern, with its size, its parts and how it was tested.
- `rexsum-examples-<version>.zip`: one HTML page per scheme. Open one from disk, turn JavaScript
  off, and change the last character: the field turns invalid. No script, no external files.
- `browser-report.json`: the browser checks below, run on the files extracted from the bundle.
- `SHA256SUMS`: for all of the above.

## Setup

The compiler and the patterns need nothing but Python 3.10 or later. Verification needs pytest
(`pip install pytest`), Node 20 or later for the V8 check, and Playwright for the browser check
(`pip install playwright && python -m playwright install chromium firefox webkit`). The
JavaScriptCore and native Safari checks run on macOS.
