"""Compile every scheme, test it, and write patterns.json."""
import json
import sys
import time

from rexsum.check import verify
from rexsum.pipeline import compile_spec
from rexsum.specs import SPECS

only = set(sys.argv[1:])
out = {}
for sp, check in SPECS:
    if only and sp.name not in only:
        continue
    t = time.time()
    r = compile_spec(sp)
    secs = time.time() - t
    v = verify(sp, check, r["pattern"])
    r.update(tested=v["tested"], valid=v["valid"], mismatches=v["bad"])
    out[sp.name] = r
    comp = {q: (c["length"], c["construction"]) for q, c in r["components"].items()}
    print(f"{sp.name:7s} {r['length']:>9,} chars  components {comp}  {secs:5.1f}s  "
          f"tested {v['tested']} ({v['valid']} valid), mismatches {v['bad']} {v['examples']}", flush=True)
json.dump(out, open("patterns.json" if not only else "patterns-partial.json", "w"), indent=1)
