"""Test strings for the browser checks: valid ones, one-digit errors and swaps of neighbours."""
import json
import random
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
from rexsum.check import candidates, complete  # noqa: E402
from rexsum.specs import SPECS  # noqa: E402

rng = random.Random(11)
cases = {}
for sp, check in SPECS:
    valid = []
    for s in candidates(sp, rng, 4000):
        t = complete(s, check, sp.alphabet)
        if t and t not in valid:
            valid.append(t)
        if len(valid) >= 150:
            break
    out = [(v, True) for v in valid]
    for v in valid:
        i = rng.randrange(len(v))
        typo = v[:i] + rng.choice([c for c in "0123456789" if c != v[i]]) + v[i + 1:]
        out.append((typo, check(typo)))
        if len(v) > 1:
            j = rng.randrange(len(v) - 1)
            sw = v[:j] + v[j + 1] + v[j] + v[j + 2:]
            out.append((sw, check(sw)))
    out += [(s, check(s)) for s in candidates(sp, rng, 300)]
    cases[sp.name] = out
json.dump(cases, open(sys.argv[1], "w"))
print({k: (len(v), sum(x[1] for x in v)) for k, v in cases.items()})
