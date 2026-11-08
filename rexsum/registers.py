"""IBAN and LEI (ISO 7064 MOD 97-10) as JavaScript regexes that keep their arithmetic in capture
groups.

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
has at least 15 characters, and an LEI has 20. A step writes the carry (3a + d) // 10, then a', then b'. A letter
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

    def __init__(self, n, fixed=True):
        self.n = n                      # the input's length, or the shortest input's if not fixed
        self.fixed = fixed
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
        if not self.fixed:              # test the position from the start, in runs of values
            runs = []
            for x in xs:
                if runs and runs[-1][1] == x - 1:
                    runs[-1][1] = x
                else:
                    runs.append([x, x])
            alts = [("^" if lo == 0 else f"(?<=^{dots(lo)})") if lo == hi else
                    (f"(?<={dots(lo)})" if lo else "") + f"(?<!{dots(hi + 1)})" for lo, hi in runs]
            return f"(?=\\{g}" + (alts[0] if len(alts) == 1 else "(?:" + "|".join(alts) + ")") + ")"
        tails = [dots(self.n - x) for x in xs]
        out = f"(?=\\{g}" + (tails[0] if len(tails) == 1 else "(?:" + "|".join(tails) + ")") + "$)"
        if len(xs) == 1:                # or test the position from the start, if shorter
            back = f"(?=\\{g}^)" if xs[0] == 0 else f"(?=\\{g}(?<=^{dots(xs[0])}))"
            out = min(out, back, key=len)
        return out

    def within(self, g, xs, every):
        """Group g holds a value in xs, given that it holds one in `every`: the shortest test, of
        the values or of bounds on them."""
        xs, every = set(xs) & set(every), set(every)
        if xs == every:
            return ""
        if not xs:
            return "(?!)"
        best = self.test(g, xs, every)
        lo, hi = min(xs), max(xs)
        if all(v in xs for v in every if lo <= v <= hi):
            below, above = [v for v in every if v < lo], [v for v in every if v > hi]
            low = up = ""
            if below:                   # g >= lo, or anything down to max(below) + 1
                low = min([f"(?<={dots(max(below) + 1)})"] + ([f"(?!{dots(self.n - lo + 1)})"] if self.fixed else []),
                          key=len)
            if above:                   # g <= hi, or anything up to min(above) - 1
                up = min([f"(?<!{dots(hi + 1)})"] + ([dots(self.n - min(above) + 1)] if self.fixed else []), key=len)
            best = min(best, f"(?=\\{g}{low}{up})", key=len)
        return best

    def at(self, j, chars):
        """The character at position j is one of `chars` (counted from the end if that is shorter)."""
        front = f"(?={dots(j)}{cls(chars)})"
        if not self.fixed:
            return front
        return min(front, f"(?=.*{cls(chars)}{dots(self.n - 1 - j)}$)", key=len)

    def ends(self, text):
        """The input ends with `text` (letters and digits)."""
        if self.fixed and self.n - len(text) <= 2:
            return f"(?={dots(self.n - len(text))}{text})"
        return f"(?=.*{text}$)"

    def write(self, alts):
        """A new group, set by the first alternative that matches (a lookahead does not backtrack,
        so the choice is final). Each alternative consumes from position 0."""
        self.groups += 1
        self.parts.append("(?=(" + "|".join(alts) + "))")
        return self.groups

    def step(self, j, by, skip="", end=False):
        """Read one digit: u <- 10u + d. `by` maps each digit d to the characters that mean d at
        position j, or is the digit itself if it is known. Characters in `skip` leave u as it is,
        and so does the end of the input if `end` is set."""
        A, B = self.a, self.b
        keep = skip or end
        known = isinstance(by, int)
        ds = [by] if known else sorted(by)

        def at(chars):
            return f"(?={dots(j)}{cls(chars)})"

        def ref(g):
            return "" if g is None else f"\\{g}"

        def kept():
            """u stays as it is: the character at j is in `skip`, or (with `end`) there is none."""
            if not end:
                return at(skip)
            rest = sorted(set(DIGITS + LETTERS) - set(skip))
            return f"(?!{dots(j)}{cls(''.join(rest)) if skip else '.'})"

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
        if B is None and cs == {0} and not keep:
            A2 = None
        else:
            alts = [kept() + ref(A)] if keep else []
            alts += [self.test(C, {c}, cs) + ref(B) + dots(c) for c in sorted(cs)]
            A2 = self.write(alts)
        # b' = (3a + d) % 10, with the a's grouped by 3a % 10
        byr = {}
        for a in sorted(self.arange):
            byr.setdefault(3 * a % 10, set()).add(a)
        alts = [kept() + ref(B)] if keep else []
        for r, as_ in sorted(byr.items()):
            if known:
                body = dots((r + by) % 10)
            else:                       # the last digit needs no test
                body = "(?:" + "|".join((at(by[d]) if i < len(ds) - 1 else "") + dots((r + d) % 10)
                                        for i, d in enumerate(ds)) + ")"
            alts.append(self.test(A, as_, self.arange) + body)
        B2 = self.write(alts)
        arange = {b + c for b in self.brange for c in cs} | (self.arange if keep else set())
        brange = {(3 * a + d) % 10 for a in self.arange for d in ds} | (self.brange if keep else set())
        self.a, self.b, self.arange, self.brange = A2, B2, arange, brange

    def accept(self, target):
        """The remainder is `target`."""
        alts = [self.test(self.a, {a}, self.arange) + self.test(self.b, {b}, self.brange)
                for a in sorted(self.arange) for b in sorted(self.brange) if (10 * a + b) % 97 == target]
        return "(?:" + "|".join(alts) + ")" if alts else "(?!)"


def read(m, j, kind, end=False):
    """Read the character at position j into the remainder: kind n a digit, a a capital letter,
    c either. With `end`, the input may stop before j, and then nothing is read."""
    if kind == "n":
        m.step(j, DIGIT, end=end)
    elif kind == "a":
        m.step(j, TENS, end=end)
        m.step(j, UNITS, end=end)
    else:                               # a digit takes one step and a letter two
        m.step(j, TENS, skip=DIGITS, end=end)
        m.step(j, UNITS_OR_DIGIT, end=end)


def iban(cc, layout):
    """The pattern for one country's IBANs, in electronic form (capitals, no spaces): cc, two
    check digits, then the BBAN laid out as in the IBAN registry ("8n10n": 18 digits). Returns
    the pattern and its number of groups."""
    bban = positions(layout)
    m = Machine(4 + len(bban))
    # ISO 13616: move the country code and check digits to the end, read each letter as two
    # digits (A = 10), and the number must be 1 mod 97
    for j, kind in enumerate(bban, start=4):
        read(m, j, kind)
    for c in cc:
        m.step(None, VALUE[c] // 10)
        m.step(None, VALUE[c] % 10)
    m.step(2, DIGIT)
    m.step(3, DIGIT)
    fmt = cc + layout_regex("2n" + layout)
    return f"(?={fmt}$)" + "".join(m.parts) + m.accept(1) + fmt, m.groups


LEI_FORMAT = r"[0-9A-Z]{18}\d{2}"


def lei():
    """The pattern for Legal Entity Identifiers (ISO 17442): 18 digits or capitals, then two check
    digits. Read with each letter as two digits (A = 10), the whole number must be 1 mod 97: the
    IBAN rule, without moving anything. Returns the pattern and its number of groups."""
    m = Machine(20)
    for j in range(18):
        read(m, j, "c")
    read(m, 18, "n")
    read(m, 19, "n")
    return f"(?={LEI_FORMAT}$)" + "".join(m.parts) + m.accept(1) + LEI_FORMAT, m.groups


def country_codes(ccs):
    """Two-letter codes as a short alternation: DE|DK|... -> D[EK]|..."""
    by = {}
    for cc in sorted(ccs):
        by.setdefault(cc[0], []).append(cc[1])
    alts = [first + cls("".join(seconds)) for first, seconds in by.items()]
    return alts[0] if len(alts) == 1 else "(?:" + "|".join(alts) + ")"


def iban_any(layouts):
    """One pattern for the IBANs of every country in `layouts` ({country code: BBAN layout}).
    A lookahead checks the country's layout, and one register machine computes the remainder for
    all of them: it reads every position that some country uses, a letter or a digit wherever any
    country allows one, and leaves the remainder alone past the end of a shorter IBAN. Registers
    are tested from the start of the input, since its length varies. Returns the pattern and its
    number of groups."""
    kinds = {cc: positions(lay) for cc, lay in layouts.items()}
    shortest = 4 + min(map(len, kinds.values()))
    longest = 4 + max(map(len, kinds.values()))
    by_layout = {}
    for cc, lay in layouts.items():
        by_layout.setdefault(layout_regex(lay), []).append(cc)
    fmt = "(?=(?:" + "|".join(country_codes(ccs) + r"\d{2}" + rx
                              for rx, ccs in sorted(by_layout.items(), key=lambda x: sorted(x[1]))) + ")$)"
    m = Machine(shortest, fixed=False)
    for j in range(4, longest):
        ks = {k[j - 4] for k in kinds.values() if len(k) > j - 4}
        kind = "n" if ks == {"n"} else "a" if ks == {"a"} else "c"
        read(m, j, kind, end=j >= shortest)
    for j in (0, 1):                    # the country code, then the check digits
        read(m, j, "a")
    read(m, 2, "n")
    read(m, 3, "n")
    return fmt + "".join(m.parts) + m.accept(1) + "[0-9A-Z]+", m.groups


class Split(Machine):
    """The same arithmetic with each register split in two, a = 5 a1 + a0 and b = 5 b1 + b0, so
    that no register holds more than 4 and an input of 5 characters is long enough. With
    x = 3a + d, the step above is a' = b + c, b' = x mod 10, c = x // 10. Since 15 a1 is a
    multiple of 5, x // 5 = 3 a1 + z with z = (3 a0 + d) // 5, so
        c = (3 a1 + z) // 2,   b1' = (a1 + z) mod 2,   b0' = (3 a0 + d) mod 5,
        a0' = (b0 + c) mod 5,  a1' = b1 + [b0 + c >= 5],
    and z and c stay at most 4 as well. Positions are given by a test for the character read
    (head), so the input can be read from either end."""

    def __init__(self, n, fixed=False):
        super().__init__(n, fixed)
        self.reg = {"a1": None, "a0": None, "b1": None, "b0": None}
        self.states = {(0, 0)}          # the values (a, b) can have

    def table(self, g, every, body):
        """Alternatives choosing body(v) by the value v of group g (one of `every`): values with
        the same body share a test, and the last needs none."""
        by = {}
        for v in sorted(every):
            by.setdefault(body(v), set()).add(v)
        items = sorted(by.items(), key=lambda x: len(self.within(g, x[1], every)))
        alts = [self.within(g, vs, every) + text for text, vs in items[:-1]] + [items[-1][0]]
        return alts[0] if len(alts) == 1 else "(?:" + "|".join(alts) + ")"

    def put(self, alts, old):
        """A new group from alternatives; where `kept` holds, the old register's value instead."""
        if self.kept:
            alts = [self.kept + ("" if old is None else f"\\{old}")] + alts
        return None if alts == [""] else self.write(alts)

    def step(self, head, by, kept=None):
        """u <- 10u + d. `by` is the digit if it is known, or a list of (d, characters meaning d):
        the last class is never tested, so it also covers anything else (a missing character read
        as 0). head(chars) tests the character read; where the lookahead `kept` holds, u stays."""
        R, S = self.reg, self.states
        self.kept = kept
        ds = [by] if isinstance(by, int) else [d for d, _ in by]
        chars = {} if isinstance(by, int) else dict(by)

        def ref(name):
            return "" if R[name] is None else f"\\{R[name]}"

        def pick(f):
            """f(d) by the digit read."""
            vals = {}
            for d in ds:
                vals.setdefault(f(d), []).append(d)
            if len(vals) == 1:
                return next(iter(vals))
            last = f(ds[-1])
            items = [(t, v) for t, v in vals.items() if t != last] + [(last, vals[last])]
            alts = [head("".join(chars[d] for d in v)) + t for t, v in items[:-1]] + [last]
            return "(?:" + "|".join(alts) + ")"

        def adder(g, vals, x, rest):
            """(g + x) mod 5 as in Adder, for g (a backreference, or "" for 0) holding one of vals;
            `rest` stands for the group holding the input after g. A single result is written
            out, if that is shorter."""
            wrap = [v for v in vals if v + x >= 5]
            opts = ([f".*?(?={dots(5 - x)}{rest}$)"] if wrap else []) + ([g + dots(x)] if len(wrap) < len(vals) else [])
            text = opts[0] if len(opts) == 1 else "(?:" + "|".join(opts) + ")"
            news = {(v + x) % 5 for v in vals}
            return min(text, dots(min(news)), key=len) if len(news) == 1 else text

        def rest_of(g, text):
            """Capture the input after g, if `text` needs it, and fill it in."""
            if REST not in text:
                return text
            self.groups += 1
            self.parts.append(f"(?={g}(.*))")
            return text.replace(REST, f"\\{self.groups}")

        trans = []                      # one row per (state, digit)
        for a, b in S:
            for d in ds:
                x = 3 * a + d
                trans.append(dict(a1=a // 5, a0=a % 5, b1=b // 5, b0=b % 5, z=(3 * (a % 5) + d) // 5, c=x // 10, x=x))

        def vals(key, **cond):
            return {t[key] for t in trans if all(t[k] == v for k, v in cond.items())}

        REST, D5 = "\0r", "\0d"         # groups not yet numbered
        # z = (3 a0 + d) // 5
        z_g = None
        if vals("z") != {0}:
            z_g = self.write([self.table(R["a0"], vals("a0"), lambda v: pick(lambda d: dots((3 * v + d) // 5)))])
        # c = (3 a1 + z) // 2, and b1' = (a1 + z) mod 2
        c_g = None
        if vals("c") != {0}:
            c_g = self.write([self.table(R["a1"], vals("a1"), lambda w: self.table(
                z_g, vals("z", a1=w), lambda z: dots((3 * w + z) // 2)))])
        b1 = self.put([self.table(R["a1"], vals("a1"), lambda w: self.table(
            z_g, vals("z", a1=w), lambda z: dots((w + z) % 2)))], R["b1"])
        # b0' = (3 a0 + d) mod 5: by the digit for each a0, or, if shorter, from a group holding
        # d mod 5, by the adder
        b0_text = self.table(R["a0"], vals("a0"), lambda v: pick(lambda d: dots((3 * v + d) % 5)))
        d5s = {d % 5 for d in ds}
        if len(d5s) > 1:
            d5_text = "(?=(" + pick(lambda d: dots(d % 5)) + "))"
            via = self.table(R["a0"], vals("a0"), lambda v: adder(D5, d5s, 3 * v % 5, REST))
            if len(d5_text) + len(via) + (12 if REST in via else 0) < len(b0_text):
                self.parts.append(d5_text)
                self.groups += 1
                d5 = f"\\{self.groups}"
                b0_text = rest_of(d5, via.replace(D5, d5))
        b0 = self.put([b0_text], R["b0"])
        # a0' = (b0 + c) mod 5 and a1' = b1 + [b0 + c >= 5]
        a0_text = self.table(c_g, vals("c"), lambda c: adder(ref("b0"), vals("b0", c=c), c, REST))
        a0 = self.put([rest_of(ref("b0"), a0_text)], R["a0"])

        def high(c):
            b0s = vals("b0", c=c)
            carry = {v for v in b0s if v + c >= 5}
            if not carry:
                return ref("b1")
            if carry == b0s:
                return ref("b1") + "."
            return f"(?:{self.within(R['b0'], carry, b0s)}{ref('b1')}.|{ref('b1')})"
        a1 = self.put([self.table(c_g, vals("c"), high)], R["a1"])
        self.reg = {"a1": a1, "a0": a0, "b1": b1, "b0": b0}
        self.states = {(t["b1"] * 5 + t["b0"] + t["c"], t["x"] % 10) for t in trans} | (S if kept else set())
        self.kept = None

    def accept(self, target):
        """u is `target` mod 97."""
        R, S = self.reg, self.states
        every = {k: {f(a, b) for a, b in S} for k, f in (("a1", lambda a, b: a // 5), ("a0", lambda a, b: a % 5),
                                                          ("b1", lambda a, b: b // 5), ("b0", lambda a, b: b % 5))}
        alts = ["".join(self.within(R[k], {f}, every[k]) for k, f in zip(("a1", "a0", "b1", "b0"),
                                                                         (a // 5, a % 5, b // 5, b % 5)))
                for a, b in sorted(S) if (10 * a + b) % 97 == target]
        return "(?:" + "|".join(alts) + ")" if alts else "(?!)"


RF_FORMAT = r"RF\d{2}[0-9A-Z]{1,21}"


def rf():
    """The pattern for RF creditor references (ISO 11649): RF, two check digits, then 1 to 21
    digits or capitals. Moving the first four characters to the end and reading letters as two
    digits (A = 10), the number must be 1 mod 97, as for an IBAN. The reference is read from its
    end, right-aligned, so that a shorter one just has leading zeros. Returns the pattern and its
    number of groups."""
    m = Split(5)
    for k in range(20, -1, -1):
        pre = "...." if k else ""       # the reference starts at position 4

        def head(chars, k=k, pre=pre):
            return f"(?={pre}.*{cls(chars)}{dots(k)}$)"
        m.step(head, [(t, TENS[t]) for t in (1, 2, 3)], kept=f"(?!{pre}.*[A-Z]{dots(k)}$)")
        m.step(head, [(d, UNITS_OR_DIGIT[d]) for d in range(1, 10)] + [(0, "")])
    for c in "RF":
        m.step(None, VALUE[c] // 10)
        m.step(None, VALUE[c] % 10)
    for j in (2, 3):
        m.step(lambda chars, j=j: f"(?={dots(j)}{cls(chars)})", [(d, str(d)) for d in range(1, 10)] + [(0, "")])
    return f"(?={RF_FORMAT}$)" + "".join(m.parts) + m.accept(1) + "[0-9A-Z]+", m.groups


# ------------------------------------------------------------- weighted sums
class Adder(Machine):
    """A weighted sum mod m in one register, for check digits that are not Horner's rule (VIN,
    ORCID): s <- (s + t) mod m, where t depends on the position and the character. Adding is
    \\s followed by t characters. Wrapping past m means subtracting, s + t - m = s - (m - t),
    and a backreference cannot be shortened; so the step first captures r, the rest of the input
    after s, and the new register is the prefix that m - t characters and then r complete:
    .*?(?=.{m - t}\\r$). Where s < m - t that fails, and the next alternative adds instead.
    Every value up to m - 1 must fit in a register, so m - 1 must not exceed the shortest input's
    length."""

    def __init__(self, n, m, fixed=True):
        super().__init__(n, fixed)
        assert m - 1 <= n, f"mod {m} does not fit in {n} characters"
        self.m = m
        self.s, self.srange = None, {0}     # the group holding s (None holds 0), and its values

    def add(self, j, by):
        """s <- s + t for the character at position j, where `by` maps each t to the characters
        that add t. The format must allow only those characters at j."""
        m, S, sr = self.m, self.s, self.srange
        merged = {}
        for t, cs in by.items():
            merged[t % m] = merged.get(t % m, "") + cs
        if set(merged) == {0}:
            return
        ts = sorted(merged, key=lambda t: (len(merged[t]), t))    # the largest class goes last, untested
        R = None
        if S is not None and len(sr) > 1 and any(s + t >= m for s in sr for t in ts):
            self.groups += 1
            self.parts.append(f"(?=\\{S}(.*))")
            R = self.groups
        alts = []
        for i, t in enumerate(ts):
            head = self.at(j, merged[t]) if i < len(ts) - 1 else ""
            if len(sr) == 1:
                body = dots((min(sr) + t) % m)
            else:
                opts = [f".*?(?={dots(m - t)}\\{R}$)"] if any(s + t >= m for s in sr) else []
                opts += [f"\\{S}{dots(t)}"] if any(s + t < m for s in sr) else []
                body = opts[0] if len(opts) == 1 else "(?:" + "|".join(opts) + ")"
            alts.append(head + body)
        self.s = self.write(alts)
        self.srange = {(s + t) % m for s in sr for t in ts}

    def accept(self, target):
        """The sum is `target` mod m."""
        target %= self.m
        return self.test(self.s, {target}, self.srange) if target in self.srange else "(?!)"

    def accept_table(self, frag):
        """The sum is some r for which frag(r), a lookahead (None: no input), holds."""
        alts = [self.test(self.s, {r}, self.srange) + frag(r) for r in sorted(self.srange) if frag(r) is not None]
        return "(?:" + "|".join(alts) + ")" if alts else "(?!)"


class Pair(Machine):
    """A weighted sum mod m in two registers, for moduli too large for one: s = K a + b with
    0 <= b < K and s < m, so a register holds at most max(K - 1, (m - 1) // K) (for m = 97 and
    K = 10, 9). Adding t wraps when s >= d = m - t, and then s' = s - d; otherwise s' = s + t.
    With t = K ta + tb and d = K da + db (tb, db < K):
        no wrap:  b' = (b + tb) mod K,  a' = a + ta + [b + tb >= K]
        wrap:     b' = (b - db) mod K,  a' = a - da - [b < db]
    Where the character leaves open whether s wraps, a group W says (empty: no wrap). Subtracting
    is done as in Adder: the new register is the prefix that x characters and then the rest
    after the old one complete."""

    def __init__(self, n, m, K, fixed=True):
        super().__init__(n, fixed)
        assert 2 <= K <= n + 1 and (m - 1) // K <= n, f"mod {m} does not fit in {n} characters with K = {K}"
        self.m, self.K = m, K
        self.A = self.B = None          # the groups holding a and b (None holds 0)
        self.vals = {0}                 # the values s can have

    def add(self, j, by):
        """s <- s + t for the character at position j, where `by` maps each t to the characters
        that add t. The format must allow only those characters at j."""
        m, K, A, B, S = self.m, self.K, self.A, self.B, self.vals
        merged = {}
        for t, cs in by.items():
            merged[t % m] = merged.get(t % m, "") + cs
        if set(merged) == {0}:
            return
        ref = {A: "" if A is None else f"\\{A}", B: "" if B is None else f"\\{B}"}
        arange = {s // K for s in S}
        # placeholders for groups not yet numbered: W, and the rests after a and b
        W, RA, RB = "\0w", "\0a", "\0b"

        def bs(ss):
            return {s % K for s in ss}

        def shortest(news, text):
            """The register can only become one value: write it out, if that is shorter."""
            if len(news) == 1 and len(dots(min(news))) <= len(text):
                return dots(min(news))
            return text

        def sub(g, x, rest):
            return ref[g] if x == 0 else f".*?(?={dots(x)}{rest}$)"

        def b_body(ss, x):              # b' = (b + x) mod K, for the values in ss
            if x == 0:
                return ref[B]
            wrap = [b for b in bs(ss) if b + x >= K]
            opts = ([sub(B, K - x, RB)] if wrap else []) + ([ref[B] + dots(x)] if len(wrap) < len(bs(ss)) else [])
            text = opts[0] if len(opts) == 1 else "(?:" + "|".join(opts) + ")"
            return shortest({(b + x) % K for b in bs(ss)}, text)

        def wrapped(t):
            d = m - t if t else m
            return {s for s in S if s >= d}

        def cond(t):
            """A test for s >= m - t, among the values in S."""
            da, db = divmod(m - t, K)
            want = wrapped(t)
            at_da = {s % K for s in S if s // K == da}
            more = self.within(A, {a for a in arange if a > da}, arange)
            here = self.within(A, {da}, arange) + self.within(B, {b for b in at_da if b >= db}, at_da)
            cands = [(more, lambda s: s // K > da), (self.within(A, {a for a in arange if a >= da}, arange),
                                                     lambda s: s // K >= da),
                     (here, lambda s: s // K == da and s % K >= db),
                     (f"(?:{more}|{here})", lambda s: s >= m - t)]
            return min((c for c, f in cands if {s for s in S if f(s)} == want), key=len)

        mixed, bodies_b, bodies_a = {}, {}, {}
        for t in merged:
            sw = wrapped(t)
            sn = S - sw
            ta, tb = divmod(t, K)
            da, db = divmod(m - t, K) if t else (0, 0)
            nb = b_body(sn, tb) if sn else None
            wb = b_body(sw, (K - db) % K) if sw else None
            na = wa = None
            if sn:
                carry = {s % K for s in sn if s % K + tb >= K}
                if not carry or carry == bs(sn):
                    na = ref[A] + dots(ta + bool(carry))
                else:
                    na = f"(?:{self.within(B, carry, bs(sn))}{ref[A]}{dots(ta + 1)}|{ref[A]}{dots(ta)})"
                na = shortest({s // K + ta + (s % K + tb >= K) for s in sn}, na)
            if sw:
                borrow = {s % K for s in sw if s % K < db}
                if not borrow or borrow == bs(sw):
                    wa = sub(A, da + bool(borrow), RA)
                else:
                    wa = f"(?:{self.within(B, borrow, bs(sw))}{sub(A, da + 1, RA)}|{sub(A, da, RA)})"
                wa = shortest({s // K - da - (s % K < db) for s in sw}, wa)
            if sn and sw:
                mixed[t] = cond(t)
                bodies_b[t] = f"(?:{W}{wb}|{nb})"
                bodies_a[t] = f"(?:{W}{wa}|{na})"
            else:
                bodies_b[t], bodies_a[t] = (nb, na) if sn else (wb, wa)

        def alts(bodies):
            """One alternative per body, for the characters that call for it; the largest class
            goes last, untested."""
            by = {}
            for t, body in bodies.items():
                by.setdefault(body, "")
                by[body] += merged[t]
            if len(by) == 1:
                return [next(iter(by))]
            items = sorted(by.items(), key=lambda x: (len(self.at(j, x[1])), x[1]))
            return [self.at(j, cs) + body for body, cs in items[:-1]] + [items[-1][0]]

        def wraps(ts):                  # W: one character if the class's test passes
            return [self.at(j, merged[t]) + mixed[t] + "." for t in sorted(ts)] + [""]

        ab, aa = alts(bodies_b), alts(bodies_a)
        text = "".join(ab + aa)
        nums = {}
        if mixed:
            nums[W] = self.write(wraps(mixed))
        for tok, g in ((RA, A), (RB, B)):
            if tok in text:
                self.groups += 1
                self.parts.append(f"(?=\\{g}(.*))")
                nums[tok] = self.groups

        def fill(xs):
            out = []
            for x in xs:
                for tok, g in nums.items():
                    x = x.replace(tok, f"(?!\\{g}^)" if tok == W else f"\\{g}")
                out.append(x)
            return out

        def put(xs, old):
            if len(xs) == 1 and xs[0] == "":
                return None
            if len(xs) == 1 and old is not None and xs[0] == f"\\{old}":
                return old
            return self.write(fill(xs))

        self.B = put(ab, B)
        self.A = put(aa, A)
        self.vals = {(s + t) % m for s in S for t in merged}

    def accept(self, target):
        """The sum is `target` mod m."""
        target %= self.m
        if target not in self.vals:
            return "(?!)"
        a, b = divmod(target, self.K)
        return (self.within(self.A, {a}, {s // self.K for s in self.vals})
                + self.within(self.B, {b}, {s % self.K for s in self.vals if s // self.K == a}))

    def accept_table(self, frag):
        """The sum is some r for which frag(r), a lookahead (None: no input), holds: tested by a,
        then b, or the other way round, whichever is shorter."""
        K, S = self.K, sorted(self.vals)
        regs = {"a": (self.A, lambda s: s // K), "b": (self.B, lambda s: s % K)}
        best = None
        for outer, inner in (("a", "b"), ("b", "a")):
            (go, fo), (gi, fi) = regs[outer], regs[inner]
            every = {fo(s) for s in S}
            alts = []
            for v in sorted(every):
                here = [s for s in S if fo(s) == v]
                rest = {fi(s) for s in here}
                ins = [self.within(gi, {fi(s)}, rest) + frag(s) for s in here if frag(s) is not None]
                if ins:
                    alts.append(self.within(go, {v}, every) + (ins[0] if len(ins) == 1 else "(?:" + "|".join(ins) + ")"))
            text = "(?:" + "|".join(alts) + ")" if len(alts) > 1 else alts[0] if alts else "(?!)"
            if best is None or len(text) < len(best):
                best = text
        return best


def weighted(n, m, contrib, alphabet, target=0, check=None):
    """Lookaheads for: the sum over positions j < n of contrib(j, c) is `target` mod m, for a
    fixed length n (contrib gives None for a character not allowed at j). With `check`, the sum
    is free and the input must end with check(sum) instead (None: no input has that sum). A
    format lookahead must come first. Every machine that fits is tried: one register if m - 1 <= n,
    two for each K. Returns the shortest text and its number of groups."""
    machines = ([Adder(n, m)] if m - 1 <= n else []) + [Pair(n, m, K) for K in range(2, min(n + 1, m - 1) + 1)
                                                        if (m - 1) // K <= n]
    best = None
    for a in machines:
        for j in range(n):
            by = {}
            for c in alphabet:
                v = contrib(j, c)
                if v is not None:
                    by.setdefault(v % m, []).append(c)
            if by:
                a.add(j, {t: "".join(cs) for t, cs in by.items()})
        if check is None:
            tail = a.accept(target)
        else:
            tail = a.accept_table(lambda r: None if check(r) is None else a.ends(check(r)))
        text = "".join(a.parts) + tail
        if best is None or len(text) < len(best[0]):
            best = (text, a.groups)
    return best


# ------------------------------------------------------------- automata in one register
def _alts(xs):
    return xs[0] if len(xs) == 1 else "(?:" + "|".join(xs) + ")"


class Table(Machine):
    """A finite automaton in one register, for check digits that are no sum (Damm, Verhoeff):
    the register holds the state, and each step sets a new group from the table state ->
    character -> state. The length varies, so a state is tested from the start of the input."""

    def __init__(self, n):
        super().__init__(n, fixed=False)
        self.s, self.srange = None, {0}

    def step(self, head, table, last, missing=None):
        """Read one character: head(chars) is the lookahead that it is one of `chars`, and
        table[v][c] the state after c. The characters that act like `last` are not tested, so
        they stand for any other input too. With `missing` (the lookahead that there is no
        character), the state is kept then. The alternatives go by character, each testing the
        state, or by state, each testing the character, whichever is shorter."""
        S, vs = self.s, sorted(self.srange)
        acts = {}
        for c in sorted({c for v in vs for c in table[v]}):
            acts.setdefault(tuple(table[v][c] for v in vs), []).append(c)
        acts = sorted(acts.items(), key=lambda a: last in a[1])

        def state(i):
            return "" if i == len(vs) - 1 else self.test(S, {vs[i]}, self.srange)

        def char(j):
            return "" if j == len(acts) - 1 else head("".join(acts[j][1]))
        by_char = [char(j) + _alts([state(i) + dots(ts[i]) for i in range(len(vs))]) for j, (ts, _) in enumerate(acts)]
        by_state = [state(i) + _alts([char(j) + dots(ts[i]) for j, (ts, _) in enumerate(acts)]) for i in range(len(vs))]
        alts = min(by_char, by_state, key=lambda a: len("|".join(a)))
        new = {t for ts, _ in acts for t in ts}
        if missing is not None:
            alts = [missing + ("" if S is None else f"\\{S}")] + alts
            new |= self.srange
        self.s, self.srange = self.write(alts), new

    def accept(self, target):
        return self.test(self.s, {target}, self.srange)


def automaton(fmt, step, k, longest, alphabet, backwards):
    """The pattern for inputs of `fmt`, 1 to `longest` characters, accepted by an automaton with
    states 0 to k - 1 (step as for pipeline.table_dp, the start and accepting state 0), read from
    the right if `backwards`, else from the left, then without regard to position. The input is
    read right-aligned: a character at a fixed distance from the end, if there is one. A register
    holds at most the input's length, so inputs of k - 1 characters or more go to the registers,
    and shorter ones to a pure regex in which the missing characters are empty strings. Returns
    the pattern, its number of groups, and the length of the pure part."""
    from .pipeline import table_dp
    from .regex import reverse
    short = k - 2                       # the longest input for the pure part
    m = Table(k - 1)
    table = lambda i: {v: {c: step(i, v, c) for c in alphabet} for v in range(k)}  # noqa: E731
    if backwards:                       # the character at distance i from the end has index i
        for i in range(longest):
            m.step(lambda cs, i=i: f"(?=.*{cls(cs)}{dots(i)}$)", table(i), alphabet[-1],
                   missing=f"(?!{dots(i + 1)})" if i > short else None)

        def padded(i, s, c):            # the reversed input, padded at its end
            v, ended = s
            if not c:
                return (v, True)
            return None if ended else (step(i, v, c), False)
        r = reverse(table_dp(short, padded, alphabet, (0, False), [(0, False), (0, True)]))
    else:
        assert all(step(0, v, c) == step(i, v, c) for i in range(longest) for v in range(k) for c in alphabet)
        idle = [c for c in alphabet if step(0, 0, c) == 0]
        for d in range(longest - 1, -1, -1):
            # before the input starts the state is 0, so a character that keeps 0 can stand for none
            m.step(lambda cs, d=d: f"(?=.*{cls(cs)}{dots(d)}$)", table(0), idle[0] if idle else alphabet[-1],
                   missing=None if idle or d <= short else f"(?!{dots(d + 1)})")

        if idle:                        # then nothing changes where the state is 0: pad there
            r = table_dp(short, lambda i, v, c: (v if v == 0 else None) if not c else step(0, v, c), alphabet)
        else:                           # or only at the start
            def padded(i, s, c):
                v, started = s
                if not c:
                    return None if started else s
                return (step(0, v, c), True)
            r = table_dp(short, padded, alphabet, (0, False), [(0, True)])
    regs = "".join(m.parts) + m.accept(0)
    return f"(?={fmt}$)(?:{r.text}|(?={dots(k - 1)}){regs}{fmt})", m.groups, len(r.text)
