"""Check-digit schemes: a reference checker and an automaton for each.

`backwards` schemes are defined from the right end (Luhn and its relatives weight digits by their
distance from the check digit, which a left-to-right reader does not know). Their automaton reads
the string reversed; the compiler reverses the resulting regex.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .automata import DFA, explore

D = "0123456789"


@dataclass
class Scheme:
    name: str
    title: str
    alphabet: str
    check: Callable[[str], bool]
    automaton: Callable[[], DFA]
    backwards: bool = False
    lengths: tuple = ()            # lengths to test (fixed-length schemes: the one length)
    example: str = ""


# ------------------------------------------------------------------ Luhn
DOUBLE = [0, 2, 4, 6, 8, 1, 3, 5, 7, 9]


def luhn(s: str) -> bool:
    if not s or not s.isdigit():
        return False
    t = 0
    for i, c in enumerate(reversed(s)):
        d = int(c)
        t += DOUBLE[d] if i % 2 else d
    return t % 10 == 0


def luhn_rev() -> DFA:
    # reading right to left: (sum mod 10, next digit doubled?, seen a digit?)
    return explore((0, 0, False),
                   lambda q, c: ((q[0] + (DOUBLE[int(c)] if q[1] else int(c))) % 10, 1 - q[1], True),
                   lambda q: q[0] == 0 and q[2], D)


# ------------------------------------------------------------------ weighted sums, from the right
def weighted_rev(weights, mod) -> Callable[[], DFA]:
    """Digits weighted by position from the right (cycling through `weights`), sum = 0 mod `mod`."""
    k = len(weights)

    def build():
        return explore((0, 0, False),
                       lambda q, c: ((q[0] + weights[q[1]] * int(c)) % mod, (q[1] + 1) % k, True),
                       lambda q: q[0] == 0 and q[2], D)
    return build


def gtin(s: str) -> bool:
    if not s or not s.isdigit():
        return False
    return sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(reversed(s))) % 10 == 0


def layered(n, start, step, accept, alphabet) -> DFA:
    """Fixed length n: states (position, value)."""
    return explore((0, start),
                   lambda q, c: (q[0] + 1, step(q[0], q[1], c)) if q[0] < n and step(q[0], q[1], c) is not None else None,
                   lambda q: q[0] == n and accept(q[1]), alphabet)


def ean13(s: str) -> bool:
    return len(s) == 13 and gtin(s)


def ean13_dfa() -> DFA:
    # left to right, position 0 has weight 1, position 1 weight 3, ... (13 digits: check digit weight 1)
    return layered(13, 0, lambda i, v, c: (v + int(c) * (3 if i % 2 else 1)) % 10, lambda v: v == 0, D)


def isbn13(s: str) -> bool:
    return ean13(s) and s[:3] in ("978", "979")


def isbn13_dfa() -> DFA:
    def step(i, v, c):
        if (i == 0 and c != "9") or (i == 1 and c != "7") or (i == 2 and c not in "89"):
            return None
        return (v + int(c) * (3 if i % 2 else 1)) % 10
    return layered(13, 0, step, lambda v: v == 0, D)


# ------------------------------------------------------------------ ISBN-10
def isbn10(s: str) -> bool:
    if len(s) != 10 or not s[:9].isdigit() or not (s[9].isdigit() or s[9] == "X"):
        return False
    vals = [int(c) for c in s[:9]] + [10 if s[9] == "X" else int(s[9])]
    return sum((i + 1) * v for i, v in enumerate(vals)) % 11 == 0


def isbn10_dfa() -> DFA:
    def step(i, v, c):
        if c == "X" and i != 9:
            return None
        x = 10 if c == "X" else int(c)
        return (v + (i + 1) * x) % 11
    return layered(10, 0, step, lambda v: v == 0, D + "X")


# ------------------------------------------------------------------ ABA routing numbers
def aba(s: str) -> bool:
    if len(s) != 9 or not s.isdigit():
        return False
    w = [3, 7, 1] * 3
    return sum(a * int(c) for a, c in zip(w, s)) % 10 == 0


def aba_dfa() -> DFA:
    w = [3, 7, 1] * 3
    return layered(9, 0, lambda i, v, c: (v + w[i] * int(c)) % 10, lambda v: v == 0, D)


# ------------------------------------------------------------------ Dutch BSN (elfproef)
def bsn(s: str) -> bool:
    if len(s) != 9 or not s.isdigit():
        return False
    w = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    return sum(a * int(c) for a, c in zip(w, s)) % 11 == 0


def bsn_dfa() -> DFA:
    w = [9, 8, 7, 6, 5, 4, 3, 2, -1]
    return layered(9, 0, lambda i, v, c: (v + w[i] * int(c)) % 11, lambda v: v == 0, D)


# ------------------------------------------------------------------ Spanish DNI
DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def dni(s: str) -> bool:
    return len(s) == 9 and s[:8].isdigit() and s[8] == DNI[int(s[:8]) % 23]


def dni_dfa() -> DFA:
    def step(i, v, c):
        if i < 8:
            return (v * 10 + int(c)) % 23 if c.isdigit() else None
        return -1 if c.isalpha() and DNI[v] == c else None
    return layered(9, 0, step, lambda v: v == -1, D + "".join(sorted(set(DNI))))


# ------------------------------------------------------------------ Damm (quasigroup of order 10)
DAMM = [
    [0, 3, 1, 7, 5, 9, 8, 6, 4, 2], [7, 0, 9, 2, 1, 5, 4, 8, 6, 3], [4, 2, 0, 6, 8, 7, 1, 3, 5, 9],
    [1, 7, 5, 0, 9, 8, 3, 4, 2, 6], [6, 1, 2, 3, 0, 4, 5, 9, 7, 8], [3, 6, 7, 4, 2, 0, 9, 5, 8, 1],
    [5, 8, 6, 9, 7, 2, 0, 1, 3, 4], [8, 9, 4, 5, 3, 6, 2, 0, 1, 7], [9, 4, 3, 8, 6, 1, 7, 2, 0, 5],
    [2, 5, 8, 1, 4, 3, 6, 7, 9, 0]]


def damm(s: str) -> bool:
    if not s or not s.isdigit():
        return False
    v = 0
    for c in s:
        v = DAMM[v][int(c)]
    return v == 0


def damm_dfa() -> DFA:
    return explore((0, False), lambda q, c: (DAMM[q[0]][int(c)], True), lambda q: q[0] == 0 and q[1], D)


# ------------------------------------------------------------------ Verhoeff (dihedral group D5)
VD = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
VP = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def verhoeff(s: str) -> bool:
    if not s or not s.isdigit():
        return False
    c = 0
    for i, ch in enumerate(reversed(s)):
        c = VD[c][VP[i % 8][int(ch)]]
    return c == 0


def verhoeff_rev() -> DFA:
    return explore((0, 0, False), lambda q, ch: (VD[q[0]][VP[q[1]][int(ch)]], (q[1] + 1) % 8, True),
                   lambda q: q[0] == 0 and q[2], D)


# ------------------------------------------------------------------ divisibility (for the theory)
def divisible(n):
    def check(s):
        return bool(s) and s.isdigit() and int(s) % n == 0

    def build():
        return explore((0, False), lambda q, c: ((q[0] * 10 + int(c)) % n, True), lambda q: q[0] == 0 and q[1], D)
    return check, build


# ------------------------------------------------------------------ IBAN (mod 97), one country
def iban_country(cc: str, bban_len: int):
    """IBAN for a country whose BBAN is all digits: cc + 2 check digits + bban_len digits."""
    code = "".join(str(ord(c) - 55) for c in cc)

    def check(s):
        if len(s) != 4 + bban_len or s[:2] != cc or not s[2:].isdigit():
            return False
        return int(s[4:] + code + s[2:4]) % 97 == 1

    def build():
        n = 4 + bban_len
        # value of the BBAN mod 97 read left to right, then the check digits must complete it
        def step(i, v, c):
            if i < 2:
                return v if c == cc[i] else None
            if not c.isdigit():
                return None
            if i < 4:
                return v * 10 + int(c)          # the check digits, 0..99
            cd, r = (v, 0) if i == 4 else v
            return (cd, (r * 10 + int(c)) % 97)

        def accept(v):
            cd, r = v
            tail = int(code + "00")
            return (r * 10 ** (len(code) + 2) + tail + cd) % 97 == 1
        return layered(n, 0, step, accept, D + cc)
    return check, build


SCHEMES: dict = {}


def _add(s: Scheme):
    SCHEMES[s.name] = s


_add(Scheme("luhn", "Luhn (payment cards, IMEI, Canadian SIN)", D, luhn, luhn_rev, True, (), "79927398713"))
_add(Scheme("gtin", "GTIN check digit, any length (EAN-8, UPC-A, EAN-13, GTIN-14)", D, gtin,
            weighted_rev([1, 3], 10), True, (), "4006381333931"))
_add(Scheme("ean13", "EAN-13", D, ean13, ean13_dfa, False, (13,), "4006381333931"))
_add(Scheme("isbn13", "ISBN-13", D, isbn13, isbn13_dfa, False, (13,), "9780306406157"))
_add(Scheme("isbn10", "ISBN-10", D + "X", isbn10, isbn10_dfa, False, (10,), "0306406152"))
_add(Scheme("aba", "ABA routing number (US banks)", D, aba, aba_dfa, False, (9,), "011000015"))
_add(Scheme("bsn", "BSN (Dutch citizen service number, elfproef)", D, bsn, bsn_dfa, False, (9,), "111222333"))
_add(Scheme("dni", "DNI (Spanish national ID)", D + "".join(sorted(set(DNI))), dni, dni_dfa, False, (9,), "12345678Z"))
_add(Scheme("damm", "Damm check digit", D, damm, damm_dfa, False, (), "5724"))
_add(Scheme("verhoeff", "Verhoeff check digit (Aadhaar)", D, verhoeff, verhoeff_rev, True, (), "2363"))
for _n in (3, 7, 11, 13, 97):
    _c, _b = divisible(_n)
    _add(Scheme(f"div{_n}", f"Decimal numbers divisible by {_n}", D, _c, _b, False, (), str(_n * 12)))
_c, _b = iban_country("BE", 12)
_add(Scheme("iban-be", "IBAN, Belgium (mod 97)", D + "BE", _c, _b, False, (16,), "BE68539007547034"))
