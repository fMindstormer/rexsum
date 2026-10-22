"""rexsum: check-digit validation as one regular expression.

    python -m rexsum --list                  the schemes and their pattern sizes
    python -m rexsum card                    print the pattern for a scheme (from patterns.json)
    python -m rexsum card --html             as an <input> element
    python -m rexsum custom --weights 1,3 --mod 10 --from right [--length 13]
                                             compile a weighted check-digit sum of your own
    python -m rexsum iban DE [--layout 8n10n]
                                             an IBAN pattern for one country (built-in layouts
                                             for some; --layout as in the IBAN registry)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from .pipeline import DIGITS, Spec, compile_spec
from .registers import iban, positions
from .specs import IBAN_LAYOUTS

ROOT = Path(__file__).resolve().parent.parent


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rexsum", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scheme", nargs="?", help="a scheme name (see --list), 'custom' or 'iban'")
    ap.add_argument("country", nargs="?", help="iban: the country code, e.g. DE")
    ap.add_argument("--list", action="store_true", help="list the schemes")
    ap.add_argument("--html", action="store_true", help="print an <input> element instead of the bare pattern")
    ap.add_argument("--weights", help="custom: weights, comma-separated, repeating (e.g. 1,3)")
    ap.add_argument("--mod", type=int, default=10, help="custom: the sum must be 0 modulo this (default 10)")
    ap.add_argument("--from", dest="side", choices=["left", "right"], default="right",
                    help="custom: the first weight applies to the leftmost or the rightmost digit (default right)")
    ap.add_argument("--length", type=int, help="custom: a fixed number of digits")
    ap.add_argument("--layout", help="iban: the BBAN layout, e.g. 4a14n (n digit, a capital letter, c either)")
    a = ap.parse_args(argv)
    lib = json.loads((ROOT / "patterns.json").read_text()) if (ROOT / "patterns.json").exists() else {}
    if a.list or not a.scheme:
        for name, r in lib.items():
            print(f"{name:8s} {r['length']:>8,} chars  {r['title']}")
        print(f"iban CC  compiled on request; built-in layouts for {' '.join(sorted(IBAN_LAYOUTS))}")
        return 0
    if a.scheme == "iban":
        cc = (a.country or "").upper()
        layout = a.layout or IBAN_LAYOUTS.get(cc)
        if len(cc) != 2 or not cc.isalpha() or not layout:
            ap.error("iban needs a country code, and --layout for countries without a built-in one")
        if not re.fullmatch(r"(\d+[nac])+", layout) or not 11 <= len(positions(layout)) <= 30:
            ap.error("--layout takes runs like 4a14n, for a BBAN of 11 to 30 characters")
        pattern, groups = iban(cc, layout)
        print(f"{len(pattern):,} characters, {groups} groups", file=sys.stderr)
        print(f'<input autocapitalize="characters" pattern="{html.escape(pattern, quote=True)}">' if a.html else pattern)
        return 0
    if a.scheme == "custom":
        if not a.weights:
            ap.error("custom needs --weights")
        ws = [int(x) for x in a.weights.split(",")]
        maps = [{c: w * int(c) for c in DIGITS} for w in ws]
        k = len(ws)
        n = a.length
        fmt = rf"\d{{{n}}}" if n else r"\d+"
        sp = Spec("custom", "custom", fmt, "cyclic", a.mod, maps=maps, backwards=a.side == "right",
                  parity=(n % k) if n else None, n=n)
        r = compile_spec(sp)
        pattern = r["pattern"]
        print(f"{r['length']:,} characters", file=sys.stderr)
    else:
        if a.scheme not in lib:
            ap.error(f"unknown scheme {a.scheme!r}; try --list")
        pattern = lib[a.scheme]["pattern"]
    print(f'<input inputmode="numeric" pattern="{html.escape(pattern, quote=True)}">' if a.html else pattern)
    return 0


if __name__ == "__main__":
    sys.exit(main())
