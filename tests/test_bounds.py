"""The lower bound of rexsum/bounds.py against exhaustive search on tiny cases, and the figures
the README quotes."""
import math
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rexsum.bounds import bounds, digit, exact, iban, multiples  # noqa: E402

TINY = [((1, 1, 1, 1), 3, 2), ((1, 2, 1, 2, 1), 3, 2), ((4, 2, 1), 5, 3), ((2, 4, 3, 1), 5, 2),
        ((1, 3, 4, 2, 1), 5, 2), ((1, 2, 4, 1, 2), 7, 2), ((4, 2, 1, 4, 2, 1), 7, 2)]


@pytest.mark.parametrize("weights,p,base", TINY)
def test_lower_bound_holds(weights, p, base):
    for t in range(p):
        lo, up, _ = bounds([digit(w, p, base) for w in weights], p, t)
        best = exact(list(weights), p, base, t)
        assert lo <= best <= up


def test_construction_is_not_always_optimal():
    # six bits read as a number, 0 mod 7: a regex using part of a residue class wins
    lo, up, _ = bounds([digit(w, 7, 2) for w in (4, 2, 1, 4, 2, 1)], 7, 0)
    assert exact([4, 2, 1, 4, 2, 1], 7, 2, 0) == 42 < up == 44


def test_quoted_figures():
    assert [multiples(k)[0] for k in (4, 6, 8)] == [208, Fraction(51550, 11), Fraction(515464, 13)]
    lo, up, _ = iban("DE", 18)
    assert lo == Fraction(11168428237247836984769, 201098145295168) and up == 116_317_552
    assert math.ceil(lo) == 55_537_202
