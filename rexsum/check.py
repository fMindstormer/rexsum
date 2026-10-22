"""Test a compiled pattern against its reference checker."""
from __future__ import annotations

import random
import re

from .registers import DIGITS, LETTERS, positions


def iban_candidates(sp, rng, k):
    """IBANs shaped like the layout, about a tenth with the right check digits, and strings of
    other shapes."""
    pick = {"n": DIGITS, "a": LETTERS, "c": DIGITS + LETTERS}
    out = []
    for _ in range(k):
        bban = "".join(rng.choice(pick[t]) for t in positions(sp.layout))
        if rng.random() < 0.1:
            kk = 98 - int("".join(str(int(c, 36)) for c in bban + sp.cc + "00")) % 97
        else:
            kk = rng.randrange(100)
        out.append(f"{sp.cc}{kk:02d}{bban}")
    for _ in range(k // 10):
        out.append("".join(rng.choice(sp.alphabet) for _ in range(rng.randrange(4, 35))))
    return out


def candidates(sp, rng, k):
    """Random strings shaped like the format (about a tenth valid), strings with one character
    changed, and strings of other lengths."""
    if sp.kind == "registers":
        return iban_candidates(sp, rng, k)
    alpha = sp.alphabet
    fixed = re.fullmatch(r"\\d\{(\d+)\}", sp.fmt) or re.fullmatch(r"\\d\{(\d+)\}\[\\dX\]", sp.fmt)
    lens = list(range(1, 25))
    out = []
    for _ in range(k):
        if sp.fmt.startswith("97[89]"):
            n, pre = 10, rng.choice(["978", "979"])
        else:
            n, pre = (int(fixed.group(1)) + (1 if "X" in sp.fmt else 0) if fixed else rng.choice(lens)), ""
        if sp.fmt.startswith(r"\d{12,19}"):
            n = rng.choice(lens)
        s = pre + "".join(rng.choice("0123456789") for _ in range(n))
        if "X" in alpha and rng.random() < 0.2:
            s = s[:-1] + "X"
        out.append(s)
    for _ in range(k // 10):
        n = rng.choice(lens)
        out.append("".join(rng.choice(alpha) for _ in range(n)))
    return out


def complete(s, check, alpha):
    """Make s valid by changing its last character, if possible."""
    for c in alpha:
        t = s[:-1] + c
        if check(t):
            return t
    return None


def python_pattern(p):
    """The pattern in Python's syntax: Python reads a backreference past \\99 as an octal escape,
    so every group gets a name."""
    out, groups, i = [], 0, 0
    while i < len(p):
        c = p[i]
        if c == "\\" and p[i + 1].isdigit():
            j = i + 1
            while j < len(p) and p[j].isdigit():
                j += 1
            out.append(f"(?P=g{p[i + 1:j]})")
            i = j
        elif c == "\\":
            out.append(p[i:i + 2])
            i += 2
        elif c == "[":
            j = p.index("]", i + 1)
            out.append(p[i:j + 1])
            i = j + 1
        elif c == "(" and p[i + 1] != "?":
            groups += 1
            out.append(f"(?P<g{groups}>")
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def verify(sp, check, pattern, k=20000, seed=7):
    rng = random.Random(seed)
    rx = re.compile(python_pattern(pattern), re.ASCII)
    cands = candidates(sp, rng, k)
    cands += [t for t in (complete(s, check, sp.alphabet) for s in cands[:k // 4]) if t]
    valid = bad = 0
    examples = []
    for s in cands:
        want = check(s)
        got = rx.fullmatch(s) is not None
        valid += want
        if want != got:
            bad += 1
            if len(examples) < 3:
                examples.append((s, want, got))
    return {"tested": len(cands), "valid": valid, "bad": bad, "examples": examples}
