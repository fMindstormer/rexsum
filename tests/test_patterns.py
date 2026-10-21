"""The shipped patterns agree with the reference checkers; small schemes compile the same way."""
import json
import random
import re
from pathlib import Path

import pytest

from rexsum.check import verify
from rexsum.pipeline import compile_spec, prime_powers
from rexsum.regex import alt, cat, chars, star, reverse, EPS
from rexsum.specs import SPECS

ROOT = Path(__file__).resolve().parent.parent
LIB = json.loads((ROOT / "patterns.json").read_text())


@pytest.mark.parametrize("sp,check", SPECS, ids=[s.name for s, _ in SPECS])
def test_shipped_pattern(sp, check):
    v = verify(sp, check, LIB[sp.name]["pattern"], k=3000)
    assert v["bad"] == 0, v["examples"]
    assert v["valid"] > 300


def test_known_numbers():
    rx = {k: re.compile(v["pattern"]) for k, v in LIB.items()}
    assert rx["card"].fullmatch("4111111111111111")
    assert not rx["card"].fullmatch("4111111111111112")
    assert rx["imei"].fullmatch("490154203237518")
    assert rx["isbn13"].fullmatch("9780306406157")
    assert not rx["isbn13"].fullmatch("9780306406158")
    assert rx["isbn10"].fullmatch("080442957X")
    assert rx["upca"].fullmatch("036000291452")
    assert rx["aba"].fullmatch("011000015")


def test_small_scheme_compiles_and_is_correct():
    sp, check = next((s, c) for s, c in SPECS if s.name == "ean8")
    r = compile_spec(sp)
    assert r["length"] == LIB["ean8"]["length"]
    assert verify(sp, check, r["pattern"], k=2000)["bad"] == 0


def test_regex_simplifications():
    a, b, c = chars("a"), chars("b"), chars("c")
    assert alt(a, b).text == "[ab]"
    assert alt(cat(a, b), cat(a, c)).text == "a[bc]"
    assert alt(cat(b, a), cat(c, a)).text == "[bc]a"
    assert cat(a, a, a).text == "a{3}"
    assert cat(a, star(a)).text == "a+"
    assert reverse(cat(a, b, star(c))).text == "c*ba"
    assert alt(EPS, cat(a, b)).text == "(?:ab)?"


def test_prime_powers():
    assert prime_powers(10) == [2, 5]
    assert prime_powers(11) == [11]
    assert prime_powers(36) == [4, 9]
