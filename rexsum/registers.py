"""IBAN (ISO 7064 MOD 97-10) as a JavaScript regex that keeps its arithmetic in capture groups.

A pure regex for a German IBAN would need about 10^8 characters: 97 is prime, so nothing splits,
and a regex cannot reuse in one branch what another has computed. JavaScript regexes also have
backreferences, and a group captured inside a lookahead keeps its value (lookaheads never
backtrack). So a group can serve as a register: capturing the first v characters of the input
stores the number v, and (?=\\7(?<=^...)) tests whether group 7 holds 3. The pattern is a row
of lookaheads at position 0 that read characters at fixed positions and compute the remainder
one character at a time (Horner's rule). A repeated group is reset on every iteration, so each
step gets new groups and the steps are written out: the size grows linearly with the length.

The remainder u is held as (a, b) with u == 10a + b (mod 97), a in [0, 13], b in [0, 9], and is
never reduced. Since 100 == 3 (mod 97), reading a digit d gives
    10u + d == 3a + 10b + d,   so   a' = b + (3a + d) // 10,   b' = (3a + d) % 10,
and a' <= 9 + (3 * 13 + 9) // 10 = 13. A register holds at most the input's length; every IBAN
has at least 15 characters. A step writes the carry (3a + d) // 10, then a', then b'. A letter
counts as two digits (A = 10, ..., Z = 35) and takes two steps.
"""
from __future__ import annotations

import re
from itertools import groupby

DIGITS = "0123456789"
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
VALUE = {c: i for i, c in enumerate(DIGITS + LETTERS)}

# the characters that mean digit d in each kind of step
DIGIT = {d: str(d) for d in range(10)}
TENS = {t: "".join(c for c in LETTERS if VALUE[c] // 10 == t) for t in (1, 2, 3)}    # a letter's first digit
UNITS = {d: "".join(c for c in LETTERS if VALUE[c] % 10 == d) for d in range(10)}   # and its second
UNITS_OR_DIGIT = {d: str(d) + UNITS[d] for d in range(10)}


def dots(k):
    # written out: V8 gives every counted repeat {k} a loop register, and a pattern with
    # thousands of them compiles about ten times slower
    return "." * k


def cls(chars):
    if len(chars) == 1:
        return chars
    cs = sorted(set(chars))
    out, i = "", 0
    while i < len(cs):
        j = i
        while j + 1 < len(cs) and ord(cs[j + 1]) == ord(cs[j]) + 1:
            j += 1
        out += cs[i] + ("-" + cs[j] if j - i >= 2 else "".join(cs[i + 1:j + 1]))
        i = j + 1
    return f"[{out}]"


def positions(layout):
    """'4a14n' -> 'aaaannnnnnnnnnnnnn': a BBAN layout as the IBAN registry writes it, one letter
    per position (n a digit, a a capital letter, c either)."""
    return "".join(kind * int(k) for k, kind in re.findall(r"(\d+)([nac])", layout))


def layout_regex(layout):
    char = {"n": r"\d", "a": "[A-Z]", "c": "[0-9A-Z]"}
    runs = [(k, len(list(g))) for k, g in groupby(positions(layout))]
    return "".join(char[k] + (f"{{{n}}}" if n > 1 else "") for k, n in runs)


class Machine:
    """Writes the steps. Groups are numbered in the order they appear in the text."""

    def __init__(self, n):
        self.n = n                      # the input's length
        self.groups = 0
        self.parts = []
        self.a = self.b = None          # the groups holding a and b; None holds 0
        self.arange, self.brange = {0}, {0}

    def test(self, g, xs, every=None):
        """Group g holds a value in xs (nothing to test if xs covers `every` possible value)."""
        if g is None:
            return "" if 0 in xs else "(?!)"
        if every is not None and set(xs) >= set(every):
            return ""
        xs = sorted(xs)
        assert xs[-1] <= self.n, f"{xs[-1]} does not fit in {self.n} characters"
        tails = [dots(self.n - x) for x in xs]
        out = f"(?=\\{g}" + (tails[0] if len(tails) == 1 else "(?:" + "|".join(tails) + ")") + "$)"
        if len(xs) == 1:                # or test the position from the start, if shorter
            back = f"(?=\\{g}^)" if xs[0] == 0 else f"(?=\\{g}(?<=^{dots(xs[0])}))"
            out = min(out, back, key=len)
        return out

    def write(self, alts):
        """A new group, set by the first alternative that matches (a lookahead does not backtrack,
        so the choice is final). Each alternative consumes from position 0."""
        self.groups += 1
        self.parts.append("(?=(" + "|".join(alts) + "))")
        return self.groups

    def step(self, j, by, skip=""):
        """Read one digit: u <- 10u + d. `by` maps each digit d to the characters that mean d at
        position j, or is the digit itself if it is known. Characters in `skip` leave u as it is."""
        A, B = self.a, self.b
        known = isinstance(by, int)
        ds = [by] if known else sorted(by)

        def at(chars):
            return f"(?={dots(j)}{cls(chars)})"

        def ref(g):
            return "" if g is None else f"\\{g}"

        # the carry (3a + d) // 10, which is q or q + 1 where 3a = 10q + r
        alts, cs = [], set()
        for a in sorted(self.arange):
            q, r = divmod(3 * a, 10)
            hi = [d for d in ds if r + d >= 10]
            if not hi:
                body = dots(q)
            elif len(hi) == len(ds):
                body = dots(q + 1)
            else:
                body = f"(?:{at(''.join(by[d] for d in hi))}{dots(q + 1)}|{dots(q)})"
            cs |= ({q + 1} if hi else set()) | ({q} if len(hi) < len(ds) else set())
            alts.append(self.test(A, {a}, self.arange) + body)
        C = self.write(alts) if len(cs) > 1 else None
        # a' = b + carry
        if B is None and cs == {0} and not skip:
            A2 = None
        else:
            alts = [at(skip) + ref(A)] if skip else []
            alts += [self.test(C, {c}, cs) + ref(B) + dots(c) for c in sorted(cs)]
            A2 = self.write(alts)
        # b' = (3a + d) % 10, with the a's grouped by 3a % 10
        byr = {}
        for a in sorted(self.arange):
            byr.setdefault(3 * a % 10, set()).add(a)
        alts = [at(skip) + ref(B)] if skip else []
        for r, as_ in sorted(byr.items()):
            if known:
                body = dots((r + by) % 10)
            else:                       # the last digit needs no test
                body = "(?:" + "|".join((at(by[d]) if i < len(ds) - 1 else "") + dots((r + d) % 10)
                                        for i, d in enumerate(ds)) + ")"
            alts.append(self.test(A, as_, self.arange) + body)
        B2 = self.write(alts)
        arange = {b + c for b in self.brange for c in cs} | (self.arange if skip else set())
        brange = {(3 * a + d) % 10 for a in self.arange for d in ds} | (self.brange if skip else set())
        self.a, self.b, self.arange, self.brange = A2, B2, arange, brange

    def accept(self, target):
        """The remainder is `target`."""
        alts = [self.test(self.a, {a}, self.arange) + self.test(self.b, {b}, self.brange)
                for a in sorted(self.arange) for b in sorted(self.brange) if (10 * a + b) % 97 == target]
        return "(?:" + "|".join(alts) + ")" if alts else "(?!)"


def iban(cc, layout):
    """The pattern for one country's IBANs, in electronic form (capitals, no spaces): cc, two
    check digits, then the BBAN laid out as in the IBAN registry ("8n10n": 18 digits). Returns
    the pattern and its number of groups."""
    bban = positions(layout)
    m = Machine(4 + len(bban))
    # ISO 13616: move the country code and check digits to the end, read each letter as two
    # digits (A = 10), and the number must be 1 mod 97
    for j, kind in enumerate(bban, start=4):
        if kind == "n":
            m.step(j, DIGIT)
        elif kind == "a":
            m.step(j, TENS)
            m.step(j, UNITS)
        else:                           # a digit takes one step and a letter two
            m.step(j, TENS, skip=DIGITS)
            m.step(j, UNITS_OR_DIGIT)
    for c in cc:
        m.step(None, VALUE[c] // 10)
        m.step(None, VALUE[c] % 10)
    m.step(2, DIGIT)
    m.step(3, DIGIT)
    fmt = cc + layout_regex("2n" + layout)
    return f"(?={fmt}$)" + "".join(m.parts) + m.accept(1) + fmt, m.groups
