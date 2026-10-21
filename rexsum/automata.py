"""Deterministic automata: built by exploring a step function, minimized, reversed."""
from __future__ import annotations

from collections import deque


class DFA:
    """States are 0..n-1; `delta[q]` maps a character to the next state (missing = reject)."""

    def __init__(self, n, start, finals, delta, alphabet):
        self.n, self.start, self.finals, self.delta, self.alphabet = n, start, frozenset(finals), delta, alphabet

    def accepts(self, w: str) -> bool:
        q = self.start
        for c in w:
            q = self.delta[q].get(c)
            if q is None:
                return False
        return q in self.finals

    def __repr__(self):
        edges = sum(len(d) for d in self.delta)
        return f"DFA({self.n} states, {edges} transitions)"


def explore(start, step, accept, alphabet) -> DFA:
    """Build the reachable part of the automaton whose states are values `start`, `step(q, c)`
    (None = reject); `accept(q)` marks final states."""
    index = {start: 0}
    order = [start]
    delta = []
    todo = deque([start])
    while todo:
        q = todo.popleft()
        row = {}
        for c in alphabet:
            r = step(q, c)
            if r is None:
                continue
            if r not in index:
                index[r] = len(order)
                order.append(r)
                todo.append(r)
            row[c] = index[r]
        delta.append(row)
    finals = {index[q] for q in order if accept(q)}
    return minimize(DFA(len(order), 0, finals, delta, alphabet))


def minimize(d: DFA) -> DFA:
    """Moore's partition refinement, after dropping states that cannot reach a final state."""
    # co-reachable states
    rev = [set() for _ in range(d.n)]
    for q, row in enumerate(d.delta):
        for r in row.values():
            rev[r].add(q)
    live = set(d.finals)
    todo = deque(d.finals)
    while todo:
        q = todo.popleft()
        for p in rev[q]:
            if p not in live:
                live.add(p)
                todo.append(p)
    if d.start not in live:
        return DFA(1, 0, set(), [{}], d.alphabet)
    cls = {q: (q in d.finals) for q in live}
    while True:
        sig = {}
        for q in live:
            row = d.delta[q]
            sig[q] = (cls[q],) + tuple(cls.get(row.get(c), None) if row.get(c) in live else None for c in d.alphabet)
        ids = {}
        new = {q: ids.setdefault(sig[q], len(ids)) for q in sorted(live)}
        if len(ids) == len(set(cls.values())):
            cls = new
            break
        cls = new
    # renumber from the start state in BFS order, for stable output
    order, index = [], {}
    todo = deque([cls[d.start]])
    index[cls[d.start]] = 0
    rep = {}
    for q in sorted(live):
        rep.setdefault(cls[q], q)
    delta = []
    while todo:
        c = todo.popleft()
        order.append(c)
        q = rep[c]
        row = {}
        for a in d.alphabet:
            r = d.delta[q].get(a)
            if r is None or r not in live:
                continue
            cr = cls[r]
            if cr not in index:
                index[cr] = len(index)
                todo.append(cr)
            row[a] = index[cr]
        delta.append(row)
    finals = {index[cls[q]] for q in live if q in d.finals}
    return DFA(len(index), 0, finals, delta, d.alphabet)


def reverse_nfa(d: DFA):
    """The reversed automaton as (states, starts, finals, edges[(p, q)] -> set of chars)."""
    edges = {}
    for q, row in enumerate(d.delta):
        for c, r in row.items():
            edges.setdefault((r, q), set()).add(c)
    return d.n, set(d.finals), {d.start}, edges
