"""Check-digit schemes compiled to one JavaScript regex.

A scheme is a weighted sum of its characters that must be 0 mod m, plus a format (length, fixed
characters). The pattern is built as

    (?=format$)(?=component_1$)...(?:component_k)

where the components check the sum modulo each prime power of m (Chinese remainder theorem:
mod 10 = mod 2 and mod 5). A component is an automaton over (partial sum, position); it is turned
into a regex by state elimination in a structured order:

- cyclic weights (any length, Luhn, GTIN): the positions inside one period first, so the q
  remaining states read a whole period at a time, then those q states in the best of all orders;
- fixed positions (ISBN-10): nested dissection of the layers, so the regex is a union over the
  partial sum at the middle position of (left half)(right half), recursively.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from itertools import permutations

from .automata import explore
from .elim import SNK, SRC, _adj, eliminate, graph_of, remove
from .regex import EPS, chars, reverse, _interned

DIGITS = "0123456789"


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


# ------------------------------------------------------------- cyclic components
def cyclic_graph(maps, q, alphabet, parity=None):
    """States (sum mod q, j), j = position mod k (k = len(maps)); accept sum 0, and, if
    `parity` is given, only after a number of characters = parity mod k."""
    k = len(maps)
    E = {}
    for s in range(q):
        for j in range(k):
            by = {}
            for c in alphabet:
                if c in maps[j]:
                    by.setdefault(((s + maps[j][c]) % q, (j + 1) % k), set()).add(c)
            for t, cs in by.items():
                E[((s, j), t)] = chars(cs)
    E[(SRC, (0, 0))] = EPS
    for j in range(k):
        if parity is None or j == parity:
            E[((0, j), SNK)] = EPS
    return E


def structured(E, exhaustive=6):
    E = dict(E)
    out, inn = _adj(E)
    states = sorted({x for e in E for x in e} - {SRC, SNK})
    for st in states:
        if st[1] != 0:
            remove(E, out, inn, st)
    rest = [st for st in states if st[1] == 0]
    best = None
    for order in (permutations(rest) if len(rest) <= exhaustive else [tuple(rest)]):
        E2 = dict(E)
        o2, i2 = _adj(E2)
        for st in order:
            remove(E2, o2, i2, st)
        r = E2.get((SRC, SNK))
        if r is not None and (best is None or len(r) < len(best)):
            best = r
    return best


def cyclic_component(maps, q, alphabet, backwards, parity=None):
    """Shortest regex found for: sum of maps[j mod k](c) = 0 mod q (j from the right if
    `backwards`)."""
    cands = [structured(cyclic_graph(maps, q, alphabet, parity))]
    # a tiny component may minimize to fewer states (GTIN mod 2 is just "digit sum even")
    k = len(maps)
    d = explore((0, 0), lambda st, c: ((st[0] + maps[st[1]][c]) % q, (st[1] + 1) % k) if c in maps[st[1]] else None,
                lambda st: st[0] == 0 and (parity is None or st[1] == parity), alphabet)
    if d.n <= 8:
        cands.append(eliminate(graph_of(d), rule="cost"))
    r = min((c for c in cands if c is not None), key=len)
    return reverse(r) if backwards else r


# ------------------------------------------------------------- fixed-length components
def layered_component(weights, q, alphabet, value):
    """Fixed length n = len(weights): sum of weights[i] * value(c) over positions = 0 mod q.
    `weights[i]` may be None for a position that does not count (any character of `alphabet`
    is accepted there; use the format lookahead to restrict it)."""
    n = len(weights)

    def step(st, c):
        i, s = st
        if i >= n:
            return None
        w = weights[i]
        v = value(i, c)
        if v is None:
            return None
        return (i + 1, (s + (w * v if w is not None else 0)) % q)
    d = explore((0, 0), step, lambda st: st[0] == n and st[1] == 0, alphabet)
    depth = _depths(d)
    E = graph_of(d)
    order = _dissection(sorted(set(depth.values())), depth)
    return eliminate(E, order=order)


def _depths(d):
    dep = {d.start: 0}
    todo = deque([d.start])
    while todo:
        q = todo.popleft()
        for r in d.delta[q].values():
            if r not in dep:
                dep[r] = dep[q] + 1
                todo.append(r)
    return dep


def _dissection(layers, depth):
    """Elimination order: each half first (recursively), the middle layer last."""
    by = {}
    for st, l in depth.items():
        by.setdefault(l, []).append(st)

    def rec(ls):
        if not ls:
            return []
        m = len(ls) // 2
        return rec(ls[:m]) + rec(ls[m + 1:]) + by[ls[m]]
    return rec(layers)


# ------------------------------------------------------------- schemes
@dataclass
class Spec:
    name: str
    title: str
    fmt: str                         # regex for the format, checked by a lookahead
    kind: str                        # "cyclic" or "layered"
    m: int
    alphabet: str = DIGITS
    maps: list = field(default_factory=list)       # cyclic: digit maps by position
    backwards: bool = True
    parity: int | None = None        # cyclic: number of characters mod period, if fixed
    weights: list = field(default_factory=list)    # layered
    value: object = None             # layered: (position, char) -> number or None
    n: int | None = None             # fixed length, if the format fixes it


def contribution(sp: Spec):
    """(position from the left, char) -> contribution to the sum, for a fixed length."""
    if sp.kind == "layered":
        def f(i, c):
            v = sp.value(i, c)
            return None if v is None else (sp.weights[i] or 0) * v
        return f
    k = len(sp.maps)

    def g(i, c):
        j = sp.n - 1 - i if sp.backwards else i
        return sp.maps[j % k].get(c)
    return g


def component(sp: Spec, q: int):
    """The shortest regex found for the sum mod q, over the constructions that apply."""
    cands = []
    if sp.kind == "cyclic":
        mq = [{c: v % q for c, v in mp.items()} for mp in sp.maps]
        cands.append(("cyclic", cyclic_component(mq, q, sp.alphabet, sp.backwards, sp.parity)))
        if sp.parity is not None:      # the format fixes the length: the parity check is optional
            cands.append(("cyclic, any length", cyclic_component(mq, q, sp.alphabet, sp.backwards, None)))
    if sp.n:
        f = contribution(sp)
        cands.append(("intervals", layered_dp(sp.n, q, sp.alphabet, lambda i, c: None if f(i, c) is None else f(i, c) % q)))
    how, r = min(cands, key=lambda x: len(x[1]))
    return how, r, {h: len(x) for h, x in cands}


def compile_spec(sp: Spec) -> dict:
    _interned.clear()
    parts = []
    for q in prime_powers(sp.m):
        how, r, tried = component(sp, q)
        parts.append((q, r.text, how, tried))
    parts.sort(key=lambda x: len(x[1]))
    texts = [p[1] for p in parts]
    look = "".join(f"(?=(?:{t})$)" for t in texts[:-1])
    pattern = f"(?={sp.fmt}$){look}(?:{texts[-1]})" if sp.fmt else look + f"(?:{texts[-1]})"
    return {"name": sp.name, "title": sp.title, "pattern": pattern, "length": len(pattern),
            "components": {p[0]: {"length": len(p[1]), "construction": p[2], "tried": p[3]} for p in parts}}


# ------------------------------------------------------------- fixed length, by intervals
def layered_dp(n, q, alphabet, contrib):
    """Fixed length n, character c at position i adding contrib(i, c) (None: not allowed).
    R[a, b][d] = strings of positions a..b-1 whose weighted sum is d mod q
    (the sum is translation invariant, so q regexes per interval suffice). An interval is split
    at the position that makes its regexes shortest:
        R[a, b][d] = alt over u of R[a, m][u] R[m, b][d - u]."""
    from .regex import alt, cat
    memo = {}

    def base(i):
        by = {}
        for c in alphabet:
            d = contrib(i, c)
            if d is not None:
                by.setdefault(d % q, set()).add(c)
        return {d: chars(cs) for d, cs in by.items()}

    def R(a, b):
        if (a, b) in memo:
            return memo[(a, b)]
        if b - a == 1:
            res = base(a)
        else:
            best, best_len = None, None
            for m in range(a + 1, b):
                L, Rr = R(a, m), R(m, b)
                res_m = {}
                for d in range(q):
                    parts = [cat(L[u], Rr[(d - u) % q]) for u in L if (d - u) % q in Rr]
                    if parts:
                        res_m[d] = alt(*parts)
                tot = sum(len(x) for x in res_m.values())
                if best is None or tot < best_len:
                    best, best_len = res_m, tot
            res = best
        memo[(a, b)] = res
        return res

    # the top level needs only d = 0: pick its split separately
    best = None
    for m in range(1, n):
        L, Rr = R(0, m), R(m, n)
        parts = [cat(L[u], Rr[(-u) % q]) for u in L if (-u) % q in Rr]
        r = alt(*parts)
        if best is None or len(r) < len(best):
            best = r
    return best
