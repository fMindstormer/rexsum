"""Deliberate edge cases for every shipped pattern, each with its expected answer written down
rather than taken from the reference checker: swaps that a check digit cannot catch, wrong
lengths, spaces, other scripts' digits, invalid characters, a final X, and IBANs and LEIs in
lowercase or printed with spaces. make_cases.py adds them to tests/cases.json, so every engine checks them.

The empty string is not here: a browser never tests an empty value against the pattern, so
whether it is accepted depends on `required`, not on the checksum. tests/browser.py checks that
separately."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rexsum.meta import SCHEMES  # noqa: E402
from rexsum.specs import FIXED  # noqa: E402

FULLWIDTH = str.maketrans("0123456789", "０１２３４５６７８９")
ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")

# swaps of neighbours that leave the check digit right: a checksum cannot catch these
KEPT_SWAPS = {
    "card": [("4009000000000003", "Luhn passes 09"), ("4090000000000003", "and the same number with 09 swapped to 90")],
    "luhn": [("4009000000000003", "Luhn passes 09"), ("4090000000000003", "and 90")],
    "isbn13": [("9780306401657", "9780306406157 with 61 swapped: digits 5 apart")],
    "ean8": [("96835074", "96385074 with 38 swapped: digits 5 apart")],
}

EXTRA = {
    "card": [("41111111111", False, "11 digits, too short"), ("41111111111111111113", False, "20 digits, too long"),
             ("4111-1111-1111-1111", False, "dashes")],
    "isbn10": [("080442957x", False, "lowercase x")],
    "issn": [("1000002X", True, "ends in X"), ("1000002x", False, "lowercase x")],
    "lei": [("HWUPKR0MPOU8FGXBT394", True, "another valid LEI, mostly letters"),
            ("506700GE1G29325QX3A3", False, "a capital letter among the check digits")],
}


def cases():
    out = {}
    for name, m in SCHEMES.items():
        v, n = m["valid"], FIXED.get(name)
        rows = [(v, True, "the valid sample"), (m["invalid"], False, "last character changed"),
                (v[:4] + " " + v[4:], False, "a space inside"), (" " + v, False, "leading space"),
                (v + " ", False, "trailing space"),
                (v.translate(FULLWIDTH), False, "fullwidth digits"),
                (v.translate(ARABIC_INDIC), False, "Arabic-Indic digits"),
                (v[:-2] + "a" + v[-1], False, "a letter where a digit belongs")]
        if n:
            rows += [(v[:-1], False, "one character short"), (v + v[-1], False, "one character too many")]
        if name.startswith("iban") or name == "lei":
            rows += [(v.lower(), False, "lowercase"),
                     (" ".join(v[i:i + 4] for i in range(0, len(v), 4)), False, "printed with spaces")]
        rows += [(s, True, why) for s, why in KEPT_SWAPS.get(name, [])]
        rows += EXTRA.get(name, [])
        out[name] = [r for r in rows if r[0] != v or r[2] == "the valid sample"]
    return out
