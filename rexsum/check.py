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


def iban_any_candidates(sp, rng, k):
    """IBANs of random registry countries, about a tenth with the right check digits, a fifth of
    them relabelled with another country's code, and strings of other shapes."""
    from .iban_registry import REGISTRY
    pick = {"n": DIGITS, "a": LETTERS, "c": DIGITS + LETTERS}
    ccs = sorted(REGISTRY)
    out = []
    for _ in range(k):
        cc = rng.choice(ccs)
        bban = "".join(rng.choice(pick[t]) for t in positions(REGISTRY[cc]))
        if rng.random() < 0.1:
            kk = 98 - int("".join(str(int(c, 36)) for c in bban + cc + "00")) % 97
        else:
            kk = rng.randrange(100)
        if rng.random() < 0.2:
            cc = rng.choice(ccs)
        out.append(f"{cc}{kk:02d}{bban}")
    for _ in range(k // 10):
        out.append("".join(rng.choice(sp.alphabet) for _ in range(rng.randrange(4, 35))))
    return out


def lei_candidates(sp, rng, k):
    """LEIs, about a tenth with the right check digits, and strings of other shapes."""
    out = []
    for _ in range(k):
        base = "".join(rng.choice(DIGITS + LETTERS) for _ in range(18))
        if rng.random() < 0.1:
            kk = 98 - int("".join(str(int(c, 36)) for c in base + "00")) % 97
        else:
            kk = rng.randrange(100)
        out.append(f"{base}{kk:02d}")
    for _ in range(k // 10):
        out.append("".join(rng.choice(sp.alphabet) for _ in range(rng.randrange(4, 35))))
    return out


def rf_candidates(sp, rng, k):
    """RF creditor references of every length (and one too long), half of them digits only,
    about a fifth with the right check digits, and strings of other shapes."""
    out = []
    for _ in range(k):
        alpha = DIGITS if rng.random() < 0.5 else DIGITS + LETTERS
        ref = "".join(rng.choice(alpha) for _ in range(rng.randint(1, 22)))
        if rng.random() < 0.2:
            kk = 98 - int("".join(str(int(c, 36)) for c in ref + "RF00")) % 97
        else:
            kk = rng.randrange(100)
        out.append(f"RF{kk:02d}{ref}")
    for _ in range(k // 10):
        out.append("".join(rng.choice(sp.alphabet) for _ in range(rng.randrange(4, 27))))
    return out


def vin_candidates(sp, rng, k):
    """VINs, about a tenth with the right check digit, some with I, O or Q, and strings of other
    shapes."""
    from .specs import VIN_VALUE, VIN_WEIGHTS
    chars = "".join(VIN_VALUE)
    out = []
    for _ in range(k):
        s = [rng.choice(chars) for _ in range(17)]
        if rng.random() < 0.1:
            t = sum(w * VIN_VALUE[c] for i, (w, c) in enumerate(zip(VIN_WEIGHTS, s)) if i != 8) % 11
            s[8] = "X" if t == 10 else str(t)
        else:
            s[8] = rng.choice(DIGITS + "X")
        if rng.random() < 0.05:
            s[rng.randrange(17)] = rng.choice("IOQ")
        out.append("".join(s))
    for _ in range(k // 10):
        out.append("".join(rng.choice(sp.alphabet) for _ in range(rng.randrange(4, 25))))
    return out


def _dni(rng):
    return rng.choice(DIGITS + "XYZ") + "".join(rng.choice(DIGITS) for _ in range(7)) + rng.choice(LETTERS)


def _hetu(rng):
    day, month = (rng.randint(1, 31), rng.randint(1, 12)) if rng.random() < 0.9 else (rng.randint(0, 39), rng.randint(0, 19))
    if rng.random() < 0.1:
        day, month = 29, 2
    return (f"{day:02d}{month:02d}{rng.randrange(100):02d}{rng.choice('+-YXWVUABCDEFGZ')}{rng.randrange(1000):03d}"
            + rng.choice(DIGITS + LETTERS))


def _nir(rng):
    s = [rng.choice(DIGITS) for _ in range(15)]
    if rng.random() < 0.15:
        s[5:7] = [rng.choice("2223"), rng.choice("AABC")]
    return "".join(s)


SAMPLES = {"dni": _dni, "hetu": _hetu, "ogm": lambda rng: "".join(rng.choice(DIGITS) for _ in range(12)),
           "nir": _nir}


def check_candidates(sp, rng, k):
    """Strings shaped like the format, about a fifth given the right check characters, some
    with one character changed, and strings of other shapes."""
    from .pipeline import contribution
    f = contribution(sp)
    out = []
    for _ in range(k):
        s = SAMPLES[sp.name](rng)
        if rng.random() < 0.2:
            want = sp.check(sum(f(i, c) or 0 for i, c in enumerate(s)) % sp.m)
            s = s[:-len(want)] + want
        if rng.random() < 0.05:
            i = rng.randrange(len(s))
            s = s[:i] + rng.choice(DIGITS + LETTERS + "-+") + s[i + 1:]
        out.append(s)
    for _ in range(k // 10):
        out.append("".join(rng.choice(DIGITS + LETTERS) for _ in range(rng.randrange(4, 20))))
    return out


def candidates(sp, rng, k):
    """Random strings shaped like the format (about a tenth valid), strings with one character
    changed, and strings of other lengths."""
    if sp.kind == "registers":
        if sp.cc:
            return iban_candidates(sp, rng, k)
        return {"iban": iban_any_candidates, "lei": lei_candidates, "rf": rf_candidates}[sp.name](sp, rng, k)
    if sp.name == "vin":
        return vin_candidates(sp, rng, k)
    if sp.check:
        return check_candidates(sp, rng, k)
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
