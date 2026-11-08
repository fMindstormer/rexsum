"""Deliberate edge cases for every shipped pattern, each with its expected answer written down
rather than taken from the reference checker: swaps that a check digit cannot catch, wrong
lengths, spaces, other scripts' digits, invalid characters, a final X, and IBANs and LEIs in
lowercase or printed with spaces, and VINs. make_cases.py adds them to tests/cases.json, so every engine checks them.

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
    "iban": [("DE89370400440532013000", True, "a German IBAN"),
             ("NO9386011117947", True, "the shortest: Norway, 15 characters"),
             ("RU0304452522540817810538091310419", True, "the longest: Russia, 33 characters"),
             ("US88370400440532013000", False, "right check digits, but no IBANs in the US"),
             ("AT71370400440532013000", False, "right check digits, German length under an Austrian code")],
    "lei": [("HWUPKR0MPOU8FGXBT394", True, "another valid LEI, mostly letters"),
            ("506700GE1G29325QX3A3", False, "a capital letter among the check digits")],
    "rf": [("RF185390075470Y", True, "a reference ending in a letter"), ("RF741", True, "the shortest: 5 characters"),
           ("RF09ZZZZZZZZZZZZZZZZZZZZZ", True, "the longest: 25 characters, all letters"),
           ("RF291111111111111111111111", False, "26 characters, too long, though the check digits fit"),
           ("XX18539007547034", False, "no RF in front")],
    "vin": [("11111111111111111", True, "all ones: the check digit is 1"),
            ("1HGCM82633A004352", True, "another valid VIN"),
            ("1M8GDM9AKXP042788", False, "the check digit swapped with its neighbour"),
            ("1M8GDM9AXKP04278O", False, "a letter O, which VINs never use"),
            ("WVWZZZ1JZXW000001", False, "a European VIN with Z in the check position")],
    "dni": [("X2482300W", True, "an NIE: X counts as 0"), ("Y2482300Q", True, "an NIE: Y counts as 1"),
            ("Y2482300W", False, "the same digits after Y need another letter"),
            ("A2482300W", False, "a letter other than X, Y or Z first"), ("54362315-K", False, "a dash before the letter")],
    "hetu": [("131052A308T", True, "the same code with A for the 2000s"),
             ("290200A1239", True, "29 February 2000, a leap year"),
             ("290200-1239", False, "29 February 1900, which did not exist"),
             ("310252-308Y", False, "31 February"), ("131052-001W", False, "number 001, below the first one issued"),
             ("131052-900W", False, "900 to 999 are temporary numbers"), ("131052-308t", False, "lowercase check character")],
    "ogm": [("000000000097", True, "all zeros, where the check is 97"), ("000000000000", False, "00 is never a check"),
            ("+++010/8068/17183+++", False, "the printed form, with +++ and slashes")],
    "nir": [("253072B07300470", True, "Corsica: department 2B counts as 18"),
            ("253072A07300443", True, "and 2A as 19"), ("253072C07300443", False, "there is no department 2C"),
            ("100000000004797", True, "a multiple of 97, where the key is 97")],
    "damm": [("5724", True, "Damm's example"), ("5742", False, "the check digit swapped with its neighbour"),
             ("0", True, "the shortest: one digit, 0"), ("05724", True, "a leading zero changes nothing"),
             ("12345671", True, "8 digits, the longest the pure part reads"),
             ("123456786", True, "9 digits, the shortest the registers read"),
             ("99999999999999999992", True, "the longest: 20 digits"),
             ("111111111111111111117", False, "21 digits, too long, though the check digit fits")],
    "verhoeff": [("2336", False, "the check digit swapped with its neighbour"),
                 ("02363", False, "a leading zero moves every digit's permutation"),
                 ("0", True, "the shortest: one digit, 0"),
                 ("12345679", True, "8 digits, the longest the pure part reads"),
                 ("123456784", True, "9 digits, the shortest the registers read"),
                 ("99999999999999999995", True, "the longest: 20 digits"),
                 ("111111111111111111115", False, "21 digits, too long, though the check digit fits")],
    "aadhaar": [("499173846154", True, "another valid number"),
                ("123412341234", False, "the check digit fits, but Aadhaar numbers never start with 1"),
                ("023412341233", False, "or with 0")],
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
        if name.startswith("iban") or name in ("lei", "rf", "vin", "dni", "hetu", "aadhaar"):
            rows += [(v.lower(), False, "lowercase"),
                     (" ".join(v[i:i + 4] for i in range(0, len(v), 4)), False, "printed with spaces")]
        rows += [(s, True, why) for s, why in KEPT_SWAPS.get(name, [])]
        rows += EXTRA.get(name, [])
        out[name] = [r for r in rows if r[0] != v or r[2] == "the valid sample"]
    return out
