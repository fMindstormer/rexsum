"""Test a compiled pattern against its reference checker."""
from __future__ import annotations

import random
import re


def candidates(sp, rng, k):
    """Random strings shaped like the format (about a tenth valid), strings with one character
    changed, and strings of other lengths."""
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


def verify(sp, check, pattern, k=20000, seed=7):
    rng = random.Random(seed)
    rx = re.compile(pattern, re.ASCII)
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
