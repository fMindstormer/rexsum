"""Regular expressions as small immutable trees, printed in JavaScript syntax.

Smart constructors keep the trees short: alternatives of single characters become one character
class, alternatives that share a first or last item are factored ("ab|ac" -> "a(?:b|c)"), repeats
become counters ("\\d\\d\\d" -> "\\d{3}"). Printing follows the `v`-flag rules browsers use for the
HTML `pattern` attribute (only digits and capital letters ever appear here, so no escaping
subtleties arise).
"""
from __future__ import annotations

from functools import lru_cache

DIGITS = frozenset("0123456789")


class Node:
    __slots__ = ("key", "_s")

    def __init__(self, key):
        self.key = key
        self._s = None

    def __eq__(self, other):
        return isinstance(other, Node) and self.key == other.key

    def __hash__(self):
        return hash(self.key)

    def __repr__(self):
        return f"/{self.text}/"

    @property
    def text(self) -> str:
        if self._s is None:
            self._s = _print(self, 0)
        return self._s

    def __len__(self):
        return len(self.text)


_interned: dict = {}


def _node(key) -> Node:
    n = _interned.get(key)
    if n is None:
        n = _interned[key] = Node(key)
    return n


EPS = _node(("eps",))


def chars(cs) -> Node:
    cs = frozenset(cs)
    assert cs
    return _node(("chr", cs))


def kind(n: Node) -> str:
    return n.key[0]


def _items(n: Node, k: str):
    return n.key[1] if kind(n) == k else (n,)


def cat(*parts: Node) -> Node:
    items: list = []
    for p in parts:
        if p is None:
            return None                    # the empty language absorbs concatenation
        for x in _items(p, "cat"):
            if x is EPS:
                continue
            if items:
                prev = items[-1]
                pb, pn = (prev.key[1], prev.key[2]) if kind(prev) == "rep" else (prev, 1)
                xb, xn = (x.key[1], x.key[2]) if kind(x) == "rep" else (x, 1)
                if pb == xb and kind(pb) != "star":
                    items[-1] = rep(pb, pn + xn)
                    continue
                if prev == x and kind(x) == "star":
                    continue                   # x*x* = x*
                if kind(prev) == "star" and prev.key[1] == x:
                    items[-1] = plus(x)            # x*x = x+
                    continue
                if kind(x) == "star" and x.key[1] == prev:
                    items[-1] = plus(prev)         # xx* = x+
                    continue
            items.append(x)
    if not items:
        return EPS
    if len(items) == 1:
        return items[0]
    return _node(("cat", tuple(items)))


def rep(x: Node, n: int) -> Node:
    if n == 1:
        return x
    return _node(("rep", x, n))


def plus(x: Node) -> Node:
    if x is EPS:
        return EPS
    if kind(x) in ("star", "plus"):
        return x
    return _node(("plus", x))


def star(x: Node) -> Node:
    if x is None or x is EPS:
        return EPS
    if kind(x) == "star":
        return x
    if kind(x) == "plus":
        return star(x.key[1])
    if kind(x) == "alt" and EPS in x.key[1]:
        rest = [y for y in x.key[1] if y is not EPS]
        return star(alt(*rest)) if rest else EPS
    return _node(("star", x))


def _head(x: Node):
    if kind(x) == "cat":
        it = x.key[1]
        return it[0], (cat(*it[1:]))
    if kind(x) == "rep":
        return x.key[1], rep(x.key[1], x.key[2] - 1)
    return x, EPS


def _last(x: Node):
    if kind(x) == "cat":
        it = x.key[1]
        return it[-1], (cat(*it[:-1]))
    if kind(x) == "rep":
        return x.key[1], rep(x.key[1], x.key[2] - 1)
    return x, EPS


def alt(*parts: Node) -> Node:
    items: set = set()
    cs: set = set()
    for p in parts:
        if p is None:
            continue
        for x in _items(p, "alt"):
            if kind(x) == "chr":
                cs |= x.key[1]
            else:
                items.add(x)
    if cs:
        items.add(chars(cs))
    if not items:
        return None
    if len(items) == 1:
        return next(iter(items))
    items = _factor(items, _head, lambda h, t: cat(h, t))
    if len(items) == 1:
        return next(iter(items))
    items = _factor(items, _last, lambda h, t: cat(t, h))
    if len(items) == 1:
        return next(iter(items))
    # merge again: factoring can expose single characters
    cs2 = {x for x in items if kind(x) == "chr"}
    if len(cs2) > 1:
        items = (items - cs2) | {chars(frozenset().union(*(x.key[1] for x in cs2)))}
        if len(items) == 1:
            return next(iter(items))
    return _node(("alt", tuple(sorted(items, key=lambda n: n.text))))


def _factor(items: set, split, join) -> set:
    groups: dict = {}
    for x in items:
        if x is EPS:
            groups.setdefault(None, []).append((x, EPS))
            continue
        h, t = split(x)
        groups.setdefault(h, []).append((x, t))
    out = set()
    for h, members in groups.items():
        if h is None or len(members) == 1:
            out.update(m[0] for m in members)
        else:
            out.add(join(h, alt(*[t for _, t in members])))
    return out


def opt(x: Node) -> Node:
    return alt(EPS, x)


# ----------------------------------------------------------------- printing
def _class(cs: frozenset) -> str:
    if cs == DIGITS:
        return r"\d"
    if len(cs) == 1:
        c = next(iter(cs))
        return c if c.isalnum() else "\\" + c
    s = sorted(cs)
    runs, i = [], 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and ord(s[j + 1]) == ord(s[j]) + 1:
            j += 1
        if j - i >= 2:
            runs.append(f"{s[i]}-{s[j]}")
        else:
            runs.extend(s[i:j + 1])
        i = j + 1
    body = "".join(runs)
    if "0-9" in body:
        body = body.replace("0-9", r"\d")
    return f"[{body}]"


# precedence: 0 = inside alternation, 1 = inside concatenation, 2 = operand of a postfix
def _print(n: Node, ctx: int) -> str:
    k = kind(n)
    if k == "eps":
        return "" if ctx < 2 else "(?:)"
    if k == "chr":
        return _class(n.key[1])
    if k == "cat":
        s = "".join(_print(x, 1) for x in n.key[1])
        return s if ctx < 2 else f"(?:{s})"
    if k == "alt":
        its = n.key[1]
        if EPS in its:
            rest = [x for x in its if x is not EPS]
            inner = rest[0] if len(rest) == 1 else _node(("alt", tuple(rest)))
            s = _print(inner, 2) + "?"
            return s if ctx < 2 else f"(?:{s})"
        s = "|".join(_print(x, 0) for x in its)
        return s if ctx == 0 else f"(?:{s})"
    if k == "star":
        return _print(n.key[1], 2) + "*"
    if k == "rep":
        return _print(n.key[1], 2) + "{%d}" % n.key[2]
    if k == "plus":
        return _print(n.key[1], 2) + "+"
    raise ValueError(k)


def reverse(n: Node) -> Node:
    """The regex for the reversed language."""
    return _rev(n)


@lru_cache(maxsize=None)
def _rev(n: Node) -> Node:
    if n is None:
        return None
    k = kind(n)
    if k in ("eps", "chr"):
        return n
    if k == "cat":
        return cat(*[_rev(x) for x in reversed(n.key[1])])
    if k == "alt":
        return alt(*[_rev(x) for x in n.key[1]])
    if k == "star":
        return star(_rev(n.key[1]))
    if k == "plus":
        return plus(_rev(n.key[1]))
    if k == "rep":
        return rep(_rev(n.key[1]), n.key[2])
    raise ValueError(k)
