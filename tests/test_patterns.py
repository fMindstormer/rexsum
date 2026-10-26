"""The shipped patterns agree with the reference checkers; small schemes compile the same way."""
import json
import random
import re
from pathlib import Path

import pytest

from rexsum.check import python_pattern, verify
from rexsum.pipeline import compile_spec, prime_powers
from rexsum.regex import alt, cat, chars, star, reverse, EPS
from rexsum.specs import IBAN_LAYOUTS, SPECS, iban_spec

ROOT = Path(__file__).resolve().parent.parent
LIB = json.loads((ROOT / "patterns.json").read_text())


@pytest.mark.parametrize("sp,check", SPECS, ids=[s.name for s, _ in SPECS])
def test_shipped_pattern(sp, check):
    v = verify(sp, check, LIB[sp.name]["pattern"], k=3000)
    assert v["bad"] == 0, v["examples"]
    assert v["valid"] > 300


def test_known_numbers():
    rx = {k: re.compile(python_pattern(v["pattern"]), re.ASCII) for k, v in LIB.items()}
    assert rx["card"].fullmatch("4111111111111111")
    assert not rx["card"].fullmatch("4111111111111112")
    assert rx["imei"].fullmatch("490154203237518")
    assert rx["isbn13"].fullmatch("9780306406157")
    assert not rx["isbn13"].fullmatch("9780306406158")
    assert rx["isbn10"].fullmatch("080442957X")
    assert rx["upca"].fullmatch("036000291452")
    assert rx["aba"].fullmatch("011000015")
    assert rx["iban_de"].fullmatch("DE89370400440532013000")
    assert not rx["iban_de"].fullmatch("DE89370400440532013001")
    assert not rx["iban_de"].fullmatch("DE89 3704 0044 0532 0130 00")     # electronic form only
    assert rx["iban_nl"].fullmatch("NL91ABNA0417164300")
    assert rx["iban_gb"].fullmatch("GB82WEST12345698765432")
    assert not rx["iban_gb"].fullmatch("GB82WEST12345698765423")
    assert rx["iban_fr"].fullmatch("FR1420041010050500013M02606")


@pytest.mark.parametrize("cc", sorted(IBAN_LAYOUTS))
def test_iban_layouts(cc):
    sp, check = iban_spec(cc, cc)
    v = verify(sp, check, compile_spec(sp)["pattern"], k=600)
    assert v["bad"] == 0, v["examples"]
    assert v["valid"] > 60


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


@pytest.mark.parametrize("name", sorted(LIB))
def test_boundary_cases(name):
    from boundary import cases
    rx = re.compile(python_pattern(LIB[name]["pattern"]), re.ASCII)
    wrong = [(s, want, why) for s, want, why in cases()[name] if (rx.fullmatch(s) is not None) != want]
    assert not wrong


def test_a_wrong_pattern_is_caught():
    sp, check = next((s, c) for s, c in SPECS if s.name == "card")
    assert verify(sp, check, LIB["card16"]["pattern"], k=2000)["bad"] > 0


@pytest.mark.parametrize("name", sorted(LIB))
def test_standalone_example(name):
    import html as h
    from rexsum.meta import SCHEMES
    page = (ROOT / "site" / "examples" / f"{name}.html").read_text()
    assert "<script" not in page.lower() and "<link" not in page.lower() and "@import" not in page
    assert "url(" not in page and 'src="' not in page
    attr = re.search(r'\spattern="([^"]*)"', page).group(1)
    assert h.unescape(attr) == LIB[name]["pattern"]
    assert " required " in page
    assert SCHEMES[name]["valid"] in page and SCHEMES[name]["invalid"] in page


def test_html_export_keyboard():
    from rexsum.__main__ import main
    import contextlib
    import io
    for name, numeric in [("card", True), ("isbn10", False), ("issn", False), ("iban_de", False)]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([name, "--html"])
        assert ('inputmode="numeric"' in out.getvalue()) == numeric, name
