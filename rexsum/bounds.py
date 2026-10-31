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
The arithmetic is exact (integers and Fractions), so the bound returned is the exact value.

Upper bound. The interval construction of pipeline.layered_dp, counted in symbols, with the
best split chosen per interval and residue:
    U(I, rho) = min over splits of the sum over a of U(I1, a) + U(I2, rho - a).

    python -m rexsum.bounds"""
from __future__ import annotations

import itertools
import math
from fractions import Fraction


def bounds(positions, p, target):
    """positions: one {residue: number of symbols} per position.
    Returns (lower bound, interval construction, number of strings), the first two in symbols."""
    n = len(positions)
    N, g, U = {}, {}, {}
    for i, d in enumerate(positions):
        N[i, i + 1], g[i, i + 1], U[i, i + 1] = dict(d), {r: Fraction(1) for r in d}, {r: 1 for r in d}
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
                        v = (g1[r1] + g2[r2]) / (c1 * c2)
                        if r not in lo or v < lo[r]:
                            lo[r] = v
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


def vin():
    """VINs: 17 positions, letters standing for digits, weights mod 11 (the check digit, 0 to 9 or
    X for 10, counts -1). Several characters share a residue here; a class of them counts as one
    symbol, in the bound and in the construction alike."""
    from .specs import VIN_VALUE, VIN_WEIGHTS
    positions = []
    for i, w in enumerate(VIN_WEIGHTS):
        d = {}
        for v in (range(11) if i == 8 else VIN_VALUE.values()):
            d[w * v % 11] = d.get(w * v % 11, 0) + 1
        positions.append(d)
    return bounds(positions, 11, 0)


def digits_of(weights, p, allowed=None):
    """One position per weight; allowed[i] lists the digits position i may hold (default all)."""
    out = []
    for i, w in enumerate(weights):
        d = {}
        for x in (allowed or {}).get(i, range(10)):
            d[x * w % p] = d.get(x * w % p, 0) + 1
        out.append(d)
    return out


# Schemes whose check characters name the remainder. A regex for the language gives one, no
# larger, for any narrower language that allows fewer characters at some positions: intersect each
# character class at those positions (the length is fixed, so every symbol has its position). So
# the bound for a narrowing is a bound for the scheme; the narrowings below are the best of a few
# tried. A check letter is one more position, each letter adding minus its residue; two check
# digits are narrowed to 01 to 89 without a final 0, which makes the two positions independent.

def dni():
    """8 digits, then a letter for the number mod 23 (narrowed to DNIs: no X, Y or Z first)."""
    pos = digits_of([pow(10, 7 - i, 23) for i in range(8)], 23)
    return bounds(pos + [{-r % 23: 1 for r in range(23)}], 23, 0)


def hetu():
    """9 digits, then a character for the number mod 31; narrowed to dates that exist in every
    month (days 01-08, 11-18, 21-28 of January to September), one century sign, and numbers
    010 to 899 without a 0 in the middle."""
    allowed = {0: range(3), 1: range(1, 9), 2: [0], 3: range(1, 10), 6: range(9), 7: range(1, 10)}
    pos = digits_of([pow(10, 8 - i, 31) for i in range(9)], 31, allowed)
    return bounds(pos + [{-r % 31: 1 for r in range(31)}], 31, 0)


def ogm():
    """10 digits, then the number mod 97 as two digits."""
    pos = digits_of([pow(10, 9 - i, 97) for i in range(10)] + [-10, -1], 97, {10: range(9), 11: range(1, 10)})
    return bounds(pos, 97, 0)


def nir():
    """13 digits, then 97 minus the number mod 97 (narrowed to no Corsican department)."""
    pos = digits_of([pow(10, 12 - i, 97) for i in range(13)] + [10, 1], 97, {13: range(9), 14: range(1, 10)})
    return bounds(pos, 97, 0)


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
        print(f"{k}-digit multiples of 97   {math.ceil(lo):12,}   {up:12,}")
    for cc, n in [("NO", 11), ("BE", 12), ("DK", 14), ("FI", 14), ("AT", 16), ("DE", 18),
                  ("ES", 20), ("SE", 20), ("PT", 21), ("PL", 24)]:
        lo, up, _ = iban(cc, n)
        print(f"IBAN {cc}, {n + 2} free digits   {lo:12.3g}   {up:12.3g}")
    lo, up, _ = vin()
    print(f"VIN, 17 characters mod 11   {math.ceil(lo):12,}   {up:12,}")
    for name, f in [("DNI or NIE, mod 23", dni), ("HETU, mod 31", hetu), ("OGM-VCS, mod 97", ogm),
                    ("NIR, mod 97", nir)]:
        lo, up, _ = f()
        print(f"{name}   {math.ceil(lo):12,}   {up:12,}")
