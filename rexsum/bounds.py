"""How small can a pure regex for a fixed-length checksum be?

A pure regex here has union, concatenation, star and character classes (no counters, lookarounds
or backreferences); its size is its number of symbol occurrences, which no pattern can undercut
in characters. The language is L = { x : sum of contrib_i(x_i) = t mod p } over fixed positions,
where different symbols allowed at one position add different residues (true for digits mod 97).

Lower bound. Every useful subexpression E matches strings of one length at one offset, and the
whole regex contains P L(E) S for the languages P, S of its concatenation siblings, so every string
E matches adds the same residue on its interval I: L(E) lies in one class (I, rho) of size
N(I, rho). Then Phi(E) = g(I, rho) |L(E)| / N(I, rho) is at most the size of E when
    g(I, rho) = N(I, rho) * min over splits I = I1 I2 and a of (g(I1, a) + g(I2, rho - a)) / (N(I1, a) N(I2, rho - a))
and g = 1 on single positions: a symbol has Phi = 1, union adds at most the sum, and a
concatenation is a rectangle, which inside a class covers at most N1 N2 of its N strings.

Upper bound. The interval construction of pipeline.layered_dp, counted in symbols, with the
best split chosen per interval and residue:
    U(I, rho) = min over splits of the sum over a of U(I1, a) + U(I2, rho - a).

    python -m rexsum.bounds"""
from __future__ import annotations

import itertools
import math


def bounds(positions, p, target):
    """positions: one {residue: number of symbols} per position.
    Returns (lower bound, interval construction, number of strings), the first two in symbols."""
    n = len(positions)
    N, g, U = {}, {}, {}
    for i, d in enumerate(positions):
        N[i, i + 1], g[i, i + 1], U[i, i + 1] = dict(d), {r: 1.0 for r in d}, {r: 1 for r in d}
    for ln in range(2, n + 1):
        for a in range(n - ln + 1):
            b = a + ln
            cnt, lo, up = {}, {}, {}
            for m in range(a + 1, b):
                N1, N2, g1, g2, U1, U2 = N[a, m], N[m, b], g[a, m], g[m, b], U[a, m], U[m, b]
                tot = {}
                for r1, c1 in N1.items():
                    for r2, c2 in N2.items():
                        r = (r1 + r2) % p
                        if m == a + 1:
                            cnt[r] = cnt.get(r, 0) + c1 * c2
                        lo[r] = min(lo.get(r, math.inf), (g1[r1] + g2[r2]) / (c1 * c2))
                        tot[r] = tot.get(r, 0) + U1[r1] + U2[r2]
                for r, v in tot.items():
                    up[r] = min(up.get(r, math.inf), v)
            N[a, b], g[a, b], U[a, b] = cnt, {r: cnt[r] * lo[r] for r in cnt}, up
    t = target % p
    return g[0, n][t], U[0, n][t], N[0, n][t]


def digit(weight, p, base=10):
    d = {}
    for x in range(base):
        d[x * weight % p] = d.get(x * weight % p, 0) + 1
    return d


def multiples(k, p=97):
    """k-digit strings (leading zeros allowed) that are multiples of p."""
    return bounds([digit(pow(10, k - 1 - j, p), p) for j in range(k)], p, 0)


def iban(cc, bban_digits):
    """CC, 2 check digits, then a BBAN of digits only. Moving the first four characters to the
    end gives BBAN * 10^6 + num(CC) * 100 + check digits, which must be 1 mod 97."""
    cc_value = int("".join(str(int(c, 36)) for c in cc))
    positions = [{0: 1}, {0: 1}, digit(10, 97), digit(1, 97)]
    positions += [digit(pow(10, 6 + bban_digits - 1 - j, 97), 97) for j in range(bban_digits)]
    return bounds(positions, 97, 1 - cc_value * 100)


def exact(weights, p, base, target):
    """The true minimum size, by search over every sublanguage of every residue class (useful
    subexpressions lie in one class). Tiny cases only: it is exponential in the class sizes."""
    n = len(weights)
    words, cost = {}, {}
    for a in range(n):
        for b in range(a + 1, n + 1):
            cl = {}
            for w in itertools.product(range(base), repeat=b - a):
                cl.setdefault(sum(weights[a + i] * x for i, x in enumerate(w)) % p, []).append(w)
            words[a, b] = cl
    for ln in range(1, n + 1):
        for a in range(n - ln + 1):
            b = a + ln
            cost[a, b] = {}
            for r, ws in words[a, b].items():
                k = len(ws)
                c = [math.inf] + [1 if ln == 1 else math.inf] * ((1 << k) - 1)
                if ln > 1:
                    index = {w: i for i, w in enumerate(ws)}
                    for m in range(a + 1, b):
                        for r1, w1 in words[a, m].items():
                            w2 = words[m, b].get((r - r1) % p)
                            if w2 is None:
                                continue
                            c1, c2 = cost[a, m][r1], cost[m, b][(r - r1) % p]
                            for A in range(1, 1 << len(w1)):
                                xs = [w1[i] for i in range(len(w1)) if A >> i & 1]
                                for B in range(1, 1 << len(w2)):
                                    T = 0
                                    for x in xs:
                                        for i in range(len(w2)):
                                            if B >> i & 1:
                                                T |= 1 << index[x + w2[i]]
                                    c[T] = min(c[T], c1[A] + c2[B])
                    for X in sorted(range(1, 1 << k), key=lambda x: bin(x).count("1")):
                        Y = (X - 1) & X
                        while Y:  # X = Y | Z with Z a proper subset of X containing X - Y
                            W = Y
                            while True:
                                Z = (X & ~Y) | W
                                if Z != X:
                                    c[X] = min(c[X], c[Y] + c[Z])
                                if not W:
                                    break
                                W = (W - 1) & Y
                            Y = (Y - 1) & X
                cost[a, b][r] = c
    ws = words[0, n][target % p]
    return cost[0, n][target % p][(1 << len(ws)) - 1]


if __name__ == "__main__":
    print("size in symbols   lower bound   construction")
    for k in (4, 6, 8):
        lo, up, _ = multiples(k)
        print(f"{k}-digit multiples of 97   {math.ceil(lo - 1e-9):12,}   {up:12,}")
    for cc, n in [("NO", 11), ("BE", 12), ("DK", 14), ("FI", 14), ("AT", 16), ("DE", 18),
                  ("ES", 20), ("SE", 20), ("PT", 21), ("PL", 24)]:
        lo, up, _ = iban(cc, n)
        print(f"IBAN {cc}, {n + 2} free digits   {lo:12.3g}   {up:12.3g}")
