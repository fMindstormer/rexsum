"""Compile a scheme to a regex and check it."""
from __future__ import annotations

import random
import re
import time

from .elim import best, graph_of
from .regex import reverse
from .schemes import SCHEMES


def compile_scheme(name, randoms=0):
    s = SCHEMES[name]
    t = time.time()
    d = s.automaton()
    r, rule, sizes = best(graph_of(d), randoms=randoms)
    if s.backwards:
        r = reverse(r)
    return {"scheme": name, "states": d.n, "regex": r.text, "length": len(r.text), "rule": rule,
            "sizes": sizes, "seconds": round(time.time() - t, 2)}


def random_strings(s, rng, k):
    """Strings to test: valid ones (mutations of valid strings) and random ones."""
    lens = s.lengths or tuple(range(1, 21))
    out = []
    for _ in range(k):
        n = rng.choice(lens)
        out.append("".join(rng.choice(s.alphabet) for _ in range(n)))
    return out


def valid_strings(s, rng, k):
    """Valid strings found by fixing the last character (or searching) for random prefixes."""
    lens = s.lengths or tuple(range(1, 21))
    out = []
    tries = 0
    while len(out) < k and tries < k * 200:
        tries += 1
        n = rng.choice(lens)
        pre = "".join(rng.choice(s.alphabet) for _ in range(n - 1))
        for c in s.alphabet:
            if s.check(pre + c):
                out.append(pre + c)
                break
            if s.backwards and s.check(c + pre):
                out.append(c + pre)
                break
    return out


def verify(name, regex, k=20000, seed=1):
    s = SCHEMES[name]
    rx = re.compile(regex, re.ASCII)
    rng = random.Random(seed)
    bad = []
    cands = random_strings(s, rng, k) + valid_strings(s, rng, k // 4)
    if s.example:
        cands.append(s.example)
    n_valid = 0
    for w in cands:
        want = s.check(w)
        n_valid += want
        got = rx.fullmatch(w) is not None
        if want != got:
            bad.append((w, want, got))
    return {"tested": len(cands), "valid": n_valid, "mismatches": bad[:5], "n_bad": len(bad)}
