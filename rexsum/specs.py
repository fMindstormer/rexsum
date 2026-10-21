"""The schemes the library ships, with reference checkers for testing."""
from __future__ import annotations

from .pipeline import DIGITS, Spec
from .schemes import DOUBLE, aba, bsn, gtin, isbn10, luhn

D = DIGITS
IDENT = {c: int(c) for c in D}
DOUBLED = {c: DOUBLE[int(c)] for c in D}
TRIPLE = {c: 3 * int(c) for c in D}


def _digit_or_x(last):
    def value(i, c):
        if c == "X":
            return 10 if i == last else None
        return int(c)
    return value


def issn(s):
    if len(s) != 8 or not s[:7].isdigit() or not (s[7].isdigit() or s[7] == "X"):
        return False
    v = [int(c) for c in s[:7]] + [10 if s[7] == "X" else int(s[7])]
    return sum(w * x for w, x in zip([8, 7, 6, 5, 4, 3, 2, 1], v)) % 11 == 0


SPECS = [
    (Spec("luhn", "Luhn, any length", r"\d+", "cyclic", 10, maps=[IDENT, DOUBLED]), luhn),
    (Spec("card", "Payment card number (Luhn, 12 to 19 digits)", r"\d{12,19}", "cyclic", 10, maps=[IDENT, DOUBLED]),
     lambda s: s.isdigit() and 12 <= len(s) <= 19 and luhn(s)),
    (Spec("card16", "Payment card number, 16 digits", r"\d{16}", "cyclic", 10, maps=[IDENT, DOUBLED], parity=0),
     lambda s: s.isdigit() and len(s) == 16 and luhn(s)),
    (Spec("imei", "IMEI (15 digits, Luhn)", r"\d{15}", "cyclic", 10, maps=[IDENT, DOUBLED], parity=1),
     lambda s: s.isdigit() and len(s) == 15 and luhn(s)),
    (Spec("sin", "Canadian SIN (9 digits, Luhn)", r"\d{9}", "cyclic", 10, maps=[IDENT, DOUBLED], parity=1),
     lambda s: s.isdigit() and len(s) == 9 and luhn(s)),
    (Spec("gtin", "GTIN check digit, any length", r"\d+", "cyclic", 10, maps=[IDENT, TRIPLE]), gtin),
    (Spec("ean8", "EAN-8", r"\d{8}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=0),
     lambda s: s.isdigit() and len(s) == 8 and gtin(s)),
    (Spec("upca", "UPC-A (12 digits)", r"\d{12}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=0),
     lambda s: s.isdigit() and len(s) == 12 and gtin(s)),
    (Spec("ean13", "EAN-13", r"\d{13}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=1),
     lambda s: s.isdigit() and len(s) == 13 and gtin(s)),
    (Spec("isbn13", "ISBN-13", r"97[89]\d{10}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=1),
     lambda s: s.isdigit() and len(s) == 13 and s[:3] in ("978", "979") and gtin(s)),
    (Spec("gtin14", "GTIN-14", r"\d{14}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=0),
     lambda s: s.isdigit() and len(s) == 14 and gtin(s)),
    (Spec("aba", "ABA routing number (9 digits)", r"\d{9}", "cyclic", 10, backwards=False, parity=0,
          maps=[{c: 3 * int(c) for c in D}, {c: 7 * int(c) for c in D}, IDENT]), aba),
    (Spec("isbn10", "ISBN-10", r"\d{9}[\dX]", "layered", 11, alphabet=D + "X",
          weights=list(range(1, 11)), value=_digit_or_x(9)), isbn10),
    (Spec("issn", "ISSN (8 characters)", r"\d{7}[\dX]", "layered", 11, alphabet=D + "X",
          weights=[8, 7, 6, 5, 4, 3, 2, 1], value=_digit_or_x(7)), issn),
    (Spec("bsn", "BSN (Dutch citizen service number)", r"\d{9}", "layered", 11,
          weights=[9, 8, 7, 6, 5, 4, 3, 2, -1], value=lambda i, c: int(c) if c.isdigit() else None), bsn),
]

FIXED = {"card16": 16, "imei": 15, "sin": 9, "ean8": 8, "upca": 12, "ean13": 13, "isbn13": 13, "gtin14": 14,
         "aba": 9, "isbn10": 10, "issn": 8, "bsn": 9}
for _sp, _ in SPECS:
    _sp.n = FIXED.get(_sp.name)
