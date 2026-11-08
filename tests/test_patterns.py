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
    assert rx["iban"].fullmatch("GB82WEST12345698765432")
    assert rx["iban"].fullmatch("NO9386011117947")
    assert not rx["iban"].fullmatch("DE89370400440532013001")
    assert not rx["iban"].fullmatch("XX89370400440532013000")
    assert rx["lei"].fullmatch("506700GE1G29325QX363")
    assert rx["lei"].fullmatch("5493001KJTIIGC8Y1R12")
    assert not rx["lei"].fullmatch("506700GE1G29325QX336")              # last two swapped
    assert not rx["lei"].fullmatch("506700ge1g29325qx363")
    assert rx["rf"].fullmatch("RF18539007547034")
    assert rx["rf"].fullmatch("RF185390075470Y")
    assert not rx["rf"].fullmatch("RF17539007547034")
    assert rx["vin"].fullmatch("1M8GDM9AXKP042788")
    assert rx["vin"].fullmatch("5YJSA1DG9DFP14705")
    assert not rx["vin"].fullmatch("1M8GDM9A0KP042788")                # check digit 0, not X
    assert not rx["vin"].fullmatch("1m8gdm9axkp042788")
    assert rx["dni"].fullmatch("54362315K")
    assert rx["dni"].fullmatch("X2482300W")                            # an NIE
    assert not rx["dni"].fullmatch("54362315Z")
    assert rx["damm"].fullmatch("5724")
    assert not rx["damm"].fullmatch("5727")
    assert rx["verhoeff"].fullmatch("2363")
    assert not rx["verhoeff"].fullmatch("2336")                         # neighbours swapped
    assert rx["aadhaar"].fullmatch("234123412346")
    assert not rx["aadhaar"].fullmatch("123412341234")                  # never starts with 1
    assert rx["hetu"].fullmatch("131052-308T")
    assert not rx["hetu"].fullmatch("131052-308U")
    assert not rx["hetu"].fullmatch("310252-308Y")                     # 31 February
    assert rx["ogm"].fullmatch("010806817183")
    assert not rx["ogm"].fullmatch("010806817180")
    assert rx["nir"].fullmatch("295109912611193")
    assert rx["nir"].fullmatch("253072A07300443")                      # Corsica
    assert not rx["nir"].fullmatch("253072C07300443")


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


def test_weighted_sums_in_registers():
    """Random weighted sums, every string of each: the register machine agrees with the sum."""
    import itertools
    from rexsum.registers import cls, weighted
    rng = random.Random(3)
    for _ in range(120):
        n = rng.randint(1, 6)
        m = rng.randint(2, n + 1)
        alpha = "".join(rng.sample("0123456789AX", rng.randint(1, 4)))
        table = {(j, c): rng.randrange(-3 * m, 3 * m) for j in range(n)
                 for c in rng.sample(alpha, rng.randint(1, len(alpha)))}
        target = rng.randrange(m)
        body, _ = weighted(n, m, lambda j, c: table.get((j, c)), alpha, target)
        fmt = "".join(cls("".join(c for c in alpha if (j, c) in table)) for j in range(n))
        rx = re.compile(python_pattern(f"(?={fmt}$){body}{fmt}"))
        for t in itertools.islice(itertools.product(alpha, repeat=n), 2000):
            s = "".join(t)
            want = all(k in table for k in enumerate(s)) and sum(table[k] for k in enumerate(s)) % m == target
            assert (rx.fullmatch(s) is not None) == want, (n, m, table, target, s)


def test_weighted_sums_in_two_registers():
    """Moduli too large for one register: every K that fits, every string, and a check that names
    the remainder at the end."""
    import itertools
    from rexsum.registers import Pair, cls
    rng = random.Random(5)
    for _ in range(60):
        n = rng.randint(3, 6)
        m = rng.randint(n + 2, (n + 1) ** 2)
        alpha = "".join(rng.sample("0123456789AX", rng.randint(2, 4)))
        table = {(j, c): rng.randrange(-2 * m, 2 * m) for j in range(n - 1)
                 for c in rng.sample(alpha, rng.randint(1, len(alpha)))}
        table.update({(n - 1, c): 0 for c in alpha})
        names = {r: rng.choice(alpha) if rng.random() < 0.8 else None for r in range(m)}
        target = rng.randrange(m)
        fmt = "".join(cls("".join(c for c in alpha if (j, c) in table)) for j in range(n))
        for K in [K for K in range(2, min(n + 1, m - 1) + 1) if (m - 1) // K <= n]:
            for named in (False, True):
                p = Pair(n, m, K)
                for j in range(n):
                    by = {}
                    for c in alpha:
                        by.setdefault(table[j, c] % m, []).append(c) if (j, c) in table else None
                    p.add(j, {t: "".join(cs) for t, cs in by.items()})
                tail = p.accept_table(lambda r: names[r] and p.ends(names[r])) if named else p.accept(target)
                rx = re.compile(python_pattern(f"(?={fmt}$)" + "".join(p.parts) + tail + fmt))
                for t in itertools.islice(itertools.product(alpha, repeat=n), 1000):
                    s = "".join(t)
                    ok = all(k in table for k in enumerate(s))
                    r = sum(table[k] for k in enumerate(s)) % m if ok else None
                    want = ok and (names[r] is not None and s.endswith(names[r]) if named else r == target)
                    assert (rx.fullmatch(s) is not None) == want, (n, m, K, table, s)


def test_automata_in_a_register():
    """registers.automaton for any length up to a limit, and the fixed-length pure regex, on two
    small automata: divisibility by 7 read from the left, and a weighted sum mod 5 read from
    the right."""
    from rexsum.pipeline import Spec, compile_automaton
    from rexsum.registers import automaton
    rng = random.Random(3)
    for step, k, backwards, ref in [
            (lambda i, v, c: (10 * v + int(c)) % 7, 7, False, lambda s: int(s) % 7 == 0),
            (lambda i, v, c: (v + (i % 3 + 1) * int(c)) % 5, 5, True,
             lambda s: sum((i % 3 + 1) * int(c) for i, c in enumerate(reversed(s))) % 5 == 0)]:
        pattern, groups, short = automaton(r"\d{1,12}", step, k, 12, "0123456789", backwards)
        assert groups == 12
        rx = re.compile(python_pattern(pattern), re.ASCII)
        for _ in range(3000):
            t = "".join(rng.choice("0123456789") for _ in range(rng.randint(1, 13)))
            assert (rx.fullmatch(t) is not None) == (len(t) <= 12 and ref(t)), t
        fixed = compile_automaton(Spec("t", "t", r"\d{6}", "automaton", k, backwards=backwards, step=step, n=6))
        rx = re.compile(python_pattern(fixed["pattern"]), re.ASCII)
        for _ in range(2000):
            t = "".join(rng.choice("0123456789") for _ in range(6))
            assert (rx.fullmatch(t) is not None) == ref(t), t


def test_regex_simplifications():
    a, b, c = chars("a"), chars("b"), chars("c")
    assert alt(a, b).text == "[ab]"
    assert alt(cat(a, b), cat(a, c)).text == "a[bc]"
    assert alt(cat(b, a), cat(c, a)).text == "[bc]a"
    assert cat(a, a, a).text == "aaa"                                  # written out while no longer
    assert cat(a, a, a, a, a).text == "a{5}"
    assert cat(alt(a, b), alt(a, b)).text == "[ab]{2}"
    assert star(cat(a, a)).text == "(?:aa)*"
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
    for name, numeric in [("card", True), ("isbn10", False), ("issn", False), ("iban_de", False), ("lei", False),
                          ("rf", False), ("vin", False), ("dni", False), ("ogm", True), ("nir", False),
                          ("damm", True), ("aadhaar", True)]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main([name, "--html"])
        assert ('inputmode="numeric"' in out.getvalue()) == numeric, name
