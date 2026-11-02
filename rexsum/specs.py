"""The schemes the library ships, with reference checkers for testing."""
from __future__ import annotations

import re

from .pipeline import DIGITS, Spec
from .iban_registry import REGISTRY
from .registers import LEI_FORMAT, LETTERS, RF_FORMAT, layout_regex
from .schemes import DOUBLE, aba, bsn, digits, gtin, isbn10, luhn

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
    if len(s) != 8 or not digits(s[:7]) or not (digits(s[7]) or s[7] == "X"):
        return False
    v = [int(c) for c in s[:7]] + [10 if s[7] == "X" else int(s[7])]
    return sum(w * x for w, x in zip([8, 7, 6, 5, 4, 3, 2, 1], v)) % 11 == 0


# BBAN layouts from the IBAN registry: n a digit, a a capital letter, c either
IBAN_LAYOUTS = REGISTRY


def iban(cc, layout):
    """ISO 13616: the layout holds; moving the first four characters to the end and reading
    letters as numbers (A = 10) gives a number that is 1 mod 97."""
    kinds = "".join(k * int(n) for n, k in re.findall(r"(\d+)([nac])", layout))
    allowed = {"n": set(D), "a": set(LETTERS), "c": set(D + LETTERS)}

    def check(s):
        if len(s) != 4 + len(kinds) or s[:2] != cc or not set(s[2:4]) <= allowed["n"]:
            return False
        if not all(c in allowed[k] for k, c in zip(kinds, s[4:])):
            return False
        return int("".join(str(int(c, 36)) for c in s[4:] + s[:4])) % 97 == 1
    return check


_IBAN_CHECKS = {cc: iban(cc, lay) for cc, lay in REGISTRY.items()}


def iban_any(s):
    """An IBAN of any country in the registry."""
    return s[:2] in _IBAN_CHECKS and _IBAN_CHECKS[s[:2]](s)


def lei(s):
    """ISO 17442: 18 digits or capitals, then two check digits; reading letters as numbers
    (A = 10) gives a number that is 1 mod 97."""
    if len(s) != 20 or not all(c in D + LETTERS for c in s[:18]) or not digits(s[18:]):
        return False
    return int("".join(str(int(c, 36)) for c in s)) % 97 == 1


def rf(s):
    """ISO 11649: RF, two check digits, then 1 to 21 digits or capitals; moving the first four
    characters to the end and reading letters as numbers, the number is 1 mod 97."""
    if not 5 <= len(s) <= 25 or s[:2] != "RF" or not digits(s[2:4]) or not all(c in D + LETTERS for c in s[4:]):
        return False
    return int("".join(str(int(c, 36)) for c in s[4:] + s[:4])) % 97 == 1


# VIN (ISO 3779, with the check digit North America requires, 49 CFR 565): no I, O or Q; the
# letters stand for digits, and the 9th character is the weighted sum of the others mod 11 (X for 10)
VIN_FORMAT = "[0-9A-HJ-NPR-Z]{8}[0-9X][0-9A-HJ-NPR-Z]{8}"
VIN_VALUE = {**IDENT, **dict(zip("ABCDEFGH", range(1, 9))), **dict(zip("JKLMN", range(1, 6))), "P": 7, "R": 9,
             **dict(zip("STUVWXYZ", range(2, 10)))}
VIN_WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, -1, 9, 8, 7, 6, 5, 4, 3, 2]     # -1: the check digit itself


def _vin_value(i, c):
    if i == 8:
        return 10 if c == "X" else IDENT.get(c)
    return VIN_VALUE.get(c)


def vin(s):
    if not re.fullmatch(VIN_FORMAT, s):
        return False
    t = sum(w * VIN_VALUE[c] for i, (w, c) in enumerate(zip(VIN_WEIGHTS, s)) if i != 8) % 11
    return s[8] == ("X" if t == 10 else str(t))


# Check characters that name the remainder of a number: the number's digits are a weighted sum
# (powers of 10 mod m), and the input ends with check(sum mod m)

# DNI and NIE (Spain): 8 digits, or X, Y or Z (for 0, 1, 2) and 7; then the number mod 23 as a letter
DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
DNI_FORMAT = r"[0-9XYZ]\d{7}[A-HJ-NP-TV-Z]"


def _dni_value(i, c):
    if i == 8:                          # the letter counts minus the remainder it names
        return -DNI_LETTERS.index(c) if c in DNI_LETTERS else None
    if c in "XYZ":
        return "XYZ".index(c) if i == 0 else None
    return int(c) if c.isdigit() else None


def dni(s):
    if len(s) != 9 or not (digits(s[:8]) or (s[0] in "XYZ" and digits(s[1:8]))) or not s[8].isupper():
        return False
    return DNI_LETTERS[int(str("XYZ".index(s[0])) + s[1:8] if s[0] in "XYZ" else s[:8]) % 23] == s[8]


# HETU (Finland): DDMMYY, a sign for the century, a 3-digit number, then the 9 digits mod 31 as
# a character. The date must exist (29 February only in leap years: 1800 and 1900 were not), and
# the number runs from 002 to 899 (900 to 999 are temporary)
HETU_CHECK = "0123456789ABCDEFHJKLMNPRSTUVWXY"
_HETU_DM = r"(?:(?:0[1-9]|1\d|2[0-8])(?:0[1-9]|1[0-2])|(?:29|30)(?:0[13-9]|1[0-2])|31(?:0[13578]|1[02]))"
HETU_FORMAT = (rf"(?:{_HETU_DM}\d\d[\-+A-FU-Y]|2902(?:(?:0[48]|[2468][048]|[13579][26])[\-+A-FU-Y]|00[A-F]))"
               r"(?!00[01])[0-8]\d\d[0-9A-FHJ-NPR-Y]")
_HETU_CENTURY = {"+": 1800, **dict.fromkeys("-YXWVU", 1900), **dict.fromkeys("ABCDEF", 2000)}


def hetu(s):
    import datetime
    if len(s) != 11 or not digits(s[:6] + s[7:10]) or s[6] not in _HETU_CENTURY:
        return False
    try:
        datetime.date(_HETU_CENTURY[s[6]] + int(s[4:6]), int(s[2:4]), int(s[:2]))
    except ValueError:
        return False
    return 2 <= int(s[7:10]) <= 899 and HETU_CHECK[int(s[:6] + s[7:10]) % 31] == s[10]


# OGM-VCS, the Belgian structured communication: 10 digits, then the number mod 97 (97 for 0)
def ogm(s):
    return len(s) == 12 and digits(s) and int(s[10:]) == (int(s[:10]) % 97 or 97)


# NIR (France): 13 digits, then 97 minus the number mod 97. Corsica's departments 2A and 2B count
# as 19 and 18
NIR_FORMAT = r"\d{5}(?:\d\d|2[AB])\d{8}"


def _nir_value(i, c):
    w = pow(10, 12 - i, 97)
    if i >= 13:
        return None
    if c in "AB":                       # 2A is 19: the 2 before it counts 1, and A counts 9
        return ("BA".index(c) + 8) * w - pow(10, 7, 97) if i == 6 else None
    return int(c) * w if c.isdigit() else None


def nir(s):
    if len(s) != 15 or not digits(s[:5] + s[7:]) or not (digits(s[5:7]) or s[5:7] in ("2A", "2B")):
        return False
    n = s[:5] + {"2A": "19", "2B": "18"}.get(s[5:7], s[5:7]) + s[7:13]
    return int(s[13:]) == 97 - int(n) % 97


def iban_spec(cc, title):
    layout = IBAN_LAYOUTS[cc]
    return (Spec(f"iban_{cc.lower()}", title, cc + layout_regex("2n" + layout), "registers", 97,
                 alphabet=D + LETTERS, cc=cc, layout=layout), iban(cc, layout))


SPECS = [
    (Spec("luhn", "Luhn, any length", r"\d+", "cyclic", 10, maps=[IDENT, DOUBLED]), luhn),
    (Spec("card", "Payment card number (Luhn, 12 to 19 digits)", r"\d{12,19}", "cyclic", 10, maps=[IDENT, DOUBLED]),
     lambda s: digits(s) and 12 <= len(s) <= 19 and luhn(s)),
    (Spec("card16", "Payment card number, 16 digits", r"\d{16}", "cyclic", 10, maps=[IDENT, DOUBLED], parity=0),
     lambda s: digits(s) and len(s) == 16 and luhn(s)),
    (Spec("imei", "IMEI (15 digits, Luhn)", r"\d{15}", "cyclic", 10, maps=[IDENT, DOUBLED], parity=1),
     lambda s: digits(s) and len(s) == 15 and luhn(s)),
    (Spec("sin", "Canadian SIN (9 digits, Luhn)", r"\d{9}", "cyclic", 10, maps=[IDENT, DOUBLED], parity=1),
     lambda s: digits(s) and len(s) == 9 and luhn(s)),
    (Spec("gtin", "GTIN check digit, any length", r"\d+", "cyclic", 10, maps=[IDENT, TRIPLE]), gtin),
    (Spec("ean8", "EAN-8", r"\d{8}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=0),
     lambda s: digits(s) and len(s) == 8 and gtin(s)),
    (Spec("upca", "UPC-A (12 digits)", r"\d{12}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=0),
     lambda s: digits(s) and len(s) == 12 and gtin(s)),
    (Spec("ean13", "EAN-13", r"\d{13}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=1),
     lambda s: digits(s) and len(s) == 13 and gtin(s)),
    (Spec("isbn13", "ISBN-13", r"97[89]\d{10}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=1),
     lambda s: digits(s) and len(s) == 13 and s[:3] in ("978", "979") and gtin(s)),
    (Spec("gtin14", "GTIN-14", r"\d{14}", "cyclic", 10, maps=[IDENT, TRIPLE], parity=0),
     lambda s: digits(s) and len(s) == 14 and gtin(s)),
    (Spec("aba", "ABA routing number (9 digits)", r"\d{9}", "cyclic", 10, backwards=False, parity=0,
          maps=[{c: 3 * int(c) for c in D}, {c: 7 * int(c) for c in D}, IDENT]), aba),
    (Spec("isbn10", "ISBN-10", r"\d{9}[\dX]", "layered", 11, alphabet=D + "X",
          weights=list(range(1, 11)), value=_digit_or_x(9)), isbn10),
    (Spec("issn", "ISSN (8 characters)", r"\d{7}[\dX]", "layered", 11, alphabet=D + "X",
          weights=[8, 7, 6, 5, 4, 3, 2, 1], value=_digit_or_x(7)), issn),
    (Spec("bsn", "BSN (Dutch citizen service number)", r"\d{9}", "layered", 11,
          weights=[9, 8, 7, 6, 5, 4, 3, 2, -1], value=lambda i, c: int(c) if c.isdigit() else None), bsn),
    iban_spec("DE", "IBAN, Germany"),
    iban_spec("NL", "IBAN, Netherlands"),
    iban_spec("GB", "IBAN, United Kingdom"),
    iban_spec("FR", "IBAN, France"),
    (Spec("iban", "IBAN, any country", r"[A-Z]{2}\d{2}[0-9A-Z]{11,30}", "registers", 97,
          alphabet=D + LETTERS), iban_any),
    (Spec("lei", "LEI (Legal Entity Identifier)", LEI_FORMAT, "registers", 97, alphabet=D + LETTERS), lei),
    (Spec("rf", "RF creditor reference (ISO 11649)", RF_FORMAT, "registers", 97, alphabet=D + LETTERS), rf),
    (Spec("vin", "VIN (Vehicle Identification Number)", VIN_FORMAT, "sums", 11, alphabet=D + LETTERS,
          weights=VIN_WEIGHTS, value=_vin_value), vin),
    (Spec("dni", "DNI or NIE (Spanish identity number)", DNI_FORMAT, "layered", 23,
          alphabet=D + "".join(sorted(set(DNI_LETTERS))), weights=[10 ** (7 - i) for i in range(8)] + [1],
          value=_dni_value, check=lambda r: DNI_LETTERS[r]), dni),
    (Spec("hetu", "HETU (Finnish personal identity code)", HETU_FORMAT, "sums", 31,
          weights=[10 ** (8 - i) for i in range(6)] + [0] + [10 ** (9 - i) for i in range(7, 10)] + [0],
          value=lambda i, c: int(c) if c.isdigit() else None, check=lambda r: HETU_CHECK[r]), hetu),
    (Spec("ogm", "Belgian structured communication (OGM-VCS)", r"\d{12}", "sums", 97,
          weights=[10 ** (9 - i) for i in range(10)] + [0, 0], value=lambda i, c: int(c),
          check=lambda r: f"{r or 97:02d}"), ogm),
    (Spec("nir", "NIR (French social security number)", NIR_FORMAT, "sums", 97, alphabet=D + "AB",
          weights=[1] * 15, value=_nir_value, check=lambda r: f"{97 - r:02d}"), nir),
]

FIXED = {"card16": 16, "imei": 15, "sin": 9, "ean8": 8, "upca": 12, "ean13": 13, "isbn13": 13, "gtin14": 14,
         "aba": 9, "isbn10": 10, "issn": 8, "bsn": 9, "lei": 20, "vin": 17,
         "dni": 9, "hetu": 11, "ogm": 12, "nir": 15}
for _sp, _ in SPECS:
    _sp.n = FIXED.get(_sp.name)
