"""Check-digit sums as an intersection of small automata.

A sum mod 10 is zero exactly when it is zero mod 2 and mod 5 (Chinese remainder theorem), and a
JavaScript regex can intersect with a lookahead: (?=A$)B matches what both A and B match. Each
component is a group automaton over (partial sum mod q, position mod k); eliminating the
positions first turns it into q states whose edges read one whole period of digits.
"""
from __future__ import annotations

from itertools import permutations

from .elim import SRC, SNK, remove, _adj
from .regex import EPS, alt, chars, reverse


def prime_powers(m):
    out, p = [], 2
    while m > 1:
        if m % p == 0:
            q = 1
            while m % p == 0:
                m //= p
                q *= p
            out.append(q)
        p += 1
    return out


def component_graph(maps, q, alphabet):
    """Reading digits (from the right, for a backwards scheme), position j cycles through the k
    maps; state (sum mod q, j). Every state with sum 0 is final; the empty string is accepted
    (the caller requires a digit separately)."""
    k = len(maps)
    E = {}
    for s in range(q):
        for j in range(k):
            by = {}
            for c in alphabet:
                if c not in maps[j]:
                    continue
                t = ((s + maps[j][c]) % q, (j + 1) % k)
                by.setdefault(t, set()).add(c)
            for t, cs in by.items():
                E[((s, j), t)] = chars(cs)
    E[(SRC, (0, 0))] = EPS
    for j in range(k):
        E[((0, j), SNK)] = EPS
    return E


def eliminate_structured(E, exhaustive=7):
    """Positions j != 0 first, then the q remaining states in the best of all orders (or a
    greedy one when there are too many)."""
    E = dict(E)
    out, inn = _adj(E)
    states = sorted({x for e in E for x in e} - {SRC, SNK})
    for st in states:
        if st[1] != 0:
            remove(E, out, inn, st)
    rest = [st for st in states if st[1] == 0]
    best = None
    orders = permutations(rest) if len(rest) <= exhaustive else [tuple(rest)]
    for order in orders:
        E2 = dict(E)
        o2, i2 = _adj(E2)
        for st in order:
            remove(E2, o2, i2, st)
        r = E2.get((SRC, SNK))
        if r is not None and (best is None or len(r) < len(best)):
            best = r
    return best


def weighted(maps, m, alphabet="0123456789", backwards=True):
    """Regex text for: the sum of maps[j % k][c] over the characters (j counted from the right
    when `backwards`) is 0 mod m, with at least one character."""
    parts = []
    for q in prime_powers(m):
        mq = [{c: v % q for c, v in mp.items()} for mp in maps]
        r = eliminate_structured(component_graph(mq, q, alphabet))
        if backwards:
            r = reverse(r)
        parts.append((q, r))
    parts.sort(key=lambda x: len(x[1]))
    texts = [r.text for _, r in parts]
    body = "".join(f"(?=(?:{t})$)" for t in texts[:-1]) + f"(?:{texts[-1]})" if len(texts) > 1 else texts[0]
    return {"pattern": f"(?=[{alphabet[0]}-{alphabet[-1]}])" * 0 + "(?=.)" + body,
            "components": {q: len(r) for q, r in parts}}
