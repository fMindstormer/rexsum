"""From an automaton to a regular expression by state elimination.

The automaton becomes a graph whose edges carry regexes, with a new source and sink. States are
removed one at a time; removing k replaces every path p -> k -> q by the edge
p -> q : R(p,k) R(k,k)* R(k,q). The result's size depends heavily on the order, and finding the
best order is hard in general, so `eliminate` tries a few greedy rules and keeps the shortest.
"""
from __future__ import annotations

import random
import sys

from .regex import EPS, alt, cat, chars, star
from .automata import DFA

sys.setrecursionlimit(100000)

SRC, SNK = "src", "snk"


def graph_of(d: DFA):
    """Edges {(p, q): regex} of the automaton, plus source and sink."""
    E = {}
    for q, row in enumerate(d.delta):
        by = {}
        for c, r in row.items():
            by.setdefault(r, set()).add(c)
        for r, cs in by.items():
            E[(q, r)] = chars(cs)
    E[(SRC, d.start)] = EPS
    for f in d.finals:
        E[(f, SNK)] = alt(E.get((f, SNK)), EPS)
    return E


def graph_of_nfa(n, starts, finals, edges):
    E = {(p, q): chars(cs) for (p, q), cs in edges.items()}
    for s in starts:
        E[(SRC, s)] = EPS
    for f in finals:
        E[(f, SNK)] = EPS
    return E


def _adj(E):
    out, inn = {}, {}
    for (p, q) in E:
        out.setdefault(p, set()).add(q)
        inn.setdefault(q, set()).add(p)
    return out, inn


def _cost(E, out, inn, k):
    """Length added by removing k, from the lengths of the regexes it combines (an estimate:
    the smart constructors usually do better)."""
    loop = E.get((k, k))
    ls = len(star(loop)) if loop is not None else 0
    ins = [p for p in inn.get(k, ()) if p != k]
    outs = [q for q in out.get(k, ()) if q != k]
    added = 0
    for p in ins:
        lp = len(E[(p, k)])
        for q in outs:
            added += lp + ls + len(E[(k, q)]) + 4
    removed = sum(len(E[(p, k)]) for p in ins) + sum(len(E[(k, q)]) for q in outs) + (len(loop) if loop is not None else 0)
    return added - removed


def remove(E, out, inn, k):
    loop = E.pop((k, k), None)
    s = star(loop) if loop is not None else EPS
    ins = [p for p in inn.get(k, ()) if p != k]
    outs = [q for q in out.get(k, ()) if q != k]
    for p in ins:
        rp = E.pop((p, k))
        out[p].discard(k)
        for q in outs:
            new = cat(rp, s, E[(k, q)])
            E[(p, q)] = alt(E.get((p, q)), new) if (p, q) in E else new
            out[p].add(q)
            inn[q].add(p)
    for q in outs:
        del E[(k, q)]
        inn[q].discard(k)
    out.pop(k, None)
    inn.pop(k, None)


def eliminate(E, order=None, rule="cost", seed=0):
    """Eliminate all states; `order` fixes the order, otherwise `rule` picks the next state
    greedily: "cost" (smallest estimated growth), "degree" (in-degree x out-degree)."""
    E = dict(E)
    out, inn = _adj(E)
    states = {x for e in E for x in e} - {SRC, SNK}
    rnd = random.Random(seed)
    if order is not None:
        for k in order:
            remove(E, out, inn, k)
    else:
        while states:
            if rule == "cost":
                k = min(states, key=lambda s: (_cost(E, out, inn, s), str(s)))
            elif rule == "degree":
                k = min(states, key=lambda s: (len(inn.get(s, ())) * len(out.get(s, ())), str(s)))
            elif rule == "random":
                k = rnd.choice(sorted(states, key=str))
            else:
                raise ValueError(rule)
            remove(E, out, inn, k)
            states.discard(k)
    return E.get((SRC, SNK))


def best(E, tries=("cost", "degree"), randoms=0):
    """The shortest regex over a few elimination rules."""
    found = []
    for rule in tries:
        found.append((rule, eliminate(E, rule=rule)))
    for i in range(randoms):
        found.append((f"random{i}", eliminate(E, rule="random", seed=i)))
    rule, r = min(found, key=lambda x: len(x[1]) if x[1] is not None else 1 << 60)
    return r, rule, {name: len(x) for name, x in found}
