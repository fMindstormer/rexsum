# rexsum

**Check-digit validation in one regular expression**, small enough for the HTML `pattern`
attribute. A credit card number, IMEI, ISBN, UPC/EAN barcode, US routing number, Dutch BSN or IBAN
typed into a plain `<input>` is checked by the browser's own form validation, with no JavaScript:

**[Try it in your browser](https://fmindstormer.github.io/rexsum/)**: eleven live fields, no script.

```html
<input inputmode="numeric" pattern="(?=\d{12,19}$)(?=(?:(?:[02468]|[13579]…">   <!-- 24,471 characters -->
```

Common advice says this cannot be done ("regex cannot perform the Luhn check"). It can: any
check-digit rule is a finite automaton, so an equivalent regular expression exists. The problem is
size: converted as one automaton, Luhn gives a regex of 37,396,808 characters. rexsum gets it
down to 24,465 (12,602 for 16-digit card numbers), 1,500 times smaller.

IBANs (mod 97) are beyond a pure regex: a German one would need about 10^8 characters. Their
patterns use JavaScript's capture groups as registers instead and compute the remainder one
character at a time: 59,966 characters for Germany, 49,350 for the Netherlands.

| Scheme | Characters | V8 compile | Median match |
|---|---:|---:|---:|
| Luhn, any length | 24,465 | 16 ms | 7 µs |
| Payment card, 12–19 digits | 24,471 | 16 ms | 1 µs |
| Payment card, 16 digits | 12,602 | 7 ms | 2 µs |
| IMEI (15 digits) | 24,466 | 16 ms | 7 µs |
| Canadian SIN (9 digits) | 10,379 | 76 ms | 1 µs |
| GTIN, any length | 23,806 | 21 ms | 14 µs |
| EAN-8 | 3,971 | 10 ms | 1 µs |
| UPC-A | 12,262 | 8 ms | 2 µs |
| EAN-13 | 23,808 | 21 ms | 13 µs |
| ISBN-13 | 23,814 | 21 ms | 10 µs |
| GTIN-14 | 12,262 | 8 ms | 3 µs |
| ABA routing number | 10,022 | 32 ms | 1 µs |
| ISBN-10 | 91,659 | 232 ms | 51 µs |
| ISSN | 16,199 | 316 ms | 2 µs |
| BSN (Dutch elfproef) | 53,594 | 116 ms | 37 µs |
| IBAN, Germany | 59,966 | 87 ms | 18 µs |
| IBAN, Netherlands | 49,350 | 68 ms | 15 µs |
| IBAN, United Kingdom | 66,271 | 107 ms | 19 µs |
| IBAN, France | 107,237 | 217 ms | 51 µs |

Every pattern agrees with a reference implementation on 23,000 to 27,000 test strings in Python,
and on 780 more in V8 and in JavaScriptCore (`tests/speed.mjs`, `tests/jsc.js`). The same 780 were
entered into a real `<input>` with JavaScript disabled in Chromium 156 and WebKit 27.2
(`tests/browser.py`), and in Safari 27's own engine on macOS (`tests/safari.swift`): the `pattern`
attribute alone gets every one right. Matching stays linear: 1,000-digit inputs take about 2 ms at
most.

The first keystroke in a field compiles its pattern. In Chromium that takes 2 to 62 ms on an
Apple M4 (189 ms for ISBN-10), and every later keystroke a few microseconds. Safari compiles the
pattern again at every keystroke, but quickly: 0.1 to 2.8 ms, growing with the pattern's length.
The table's times are V8 in Node 24.

Servers compress HTML, and the patterns compress well, 8 to 45 times: Luhn's 24,465 characters
gzip to 542 bytes and the German IBAN's 59,966 to 6.6 kB. GitHub Pages sends the demo page,
358 kB with eleven fields, as 29 kB.

## How

1. **Split the modulus with lookaheads.** A sum is 0 mod 10 exactly when it is 0 mod 2 and
   0 mod 5 (Chinese remainder theorem). JavaScript regexes can intersect: `(?=A$)B` matches what
   both `A` and `B` match. So each prime-power part gets its own, much smaller automaton. For Luhn
   the mod-2 part is 198 characters; the work is in the mod-5 part. Without the split, the same
   elimination order gives 37,396,808 characters.
2. **Eliminate states in a structured order.** State elimination removes states one by one; the
   order decides the size, by orders of magnitude. For cyclic weights (Luhn's 1, 2, 1, 2, …) the
   positions inside one period go first, so the 5 remaining states read two digits at a time; then
   all 120 orders of those 5 are tried. On Luhn's mod-5 part this gives 24,246 characters, against
   47,183 for the best greedy rule from the literature and 72,000 for the best of 178 random orders.
3. **Split fixed lengths at the best point.** For a fixed length the weighted sum is translation
   invariant, so an interval of positions needs only one regex per residue. Each interval is split
   where its regexes come out shortest, recursively (`layered_dp`). This wins for short numbers
   (EAN-8: 3,971 characters against 12,203) and for the mod-11 schemes, whose digits never share a
   character class.
4. **For IBAN, use capture groups as registers.** Mod 97 is beyond the three steps above (see
   Limits). But a group captured inside a lookahead keeps its value, and a backreference can test
   it: capturing the first v characters stores the number v, and `(?=\5(?<=^...))` tests whether
   group 5 holds 3. Uezato (ICALP 2024) used the same device to prove that such regexes recognize
   exactly NLOG; see Prior work. An IBAN pattern is a row of such lookaheads that compute the
   remainder one character at a time, each step writing fresh groups (a repeated group resets on
   every iteration, so the steps are written out). The remainder is held as (a, b), standing for
   10a + b with a ≤ 13 and b ≤ 9, and never reduced: since 100 ≡ 3 (mod 97), a digit d turns
   (a, b) into (b + ⌊(3a+d)/10⌋, (3a+d) mod 10). A letter counts as two digits. The size grows
   linearly, about 2,500 characters per digit (`rexsum/registers.py`). Repeats are written out
   (`...`, not `.{3}`): V8 gives every counted repeat a loop register, and with thousands of them
   the German pattern takes 715 ms to compile instead of 58. Backreferences put these patterns
   outside the regular languages, so they are not regular expressions in the textbook sense; the
   `pattern` attribute accepts them all the same.

The regex builder (`rexsum/regex.py`) keeps expressions small as it goes: single characters merge
into classes, alternatives that share a first or last item are factored, repeats become `{n}` and
`+`. The patterns use only syntax that is valid under the `v` flag browsers apply to `pattern`.

## Limits

- **Prime moduli are expensive.** The language "digits whose sum is a multiple of 5" already needs
  stars nested five deep (McNaughton: for bideterministic languages, star height equals the cycle
  rank of the minimal automaton, here a complete graph on 5 states). The constructions here grow
  like 4^(q−1) for modulus q.
- **Mod 97 is out of reach for a pure regex.** 97 is prime, so nothing splits, and the ten digits
  add ten different residues, so no character classes merge. Multiples of 97 with 4, 6 and 8
  digits need 524, 9,653 and 100,133 characters. Each country fixes the length, so interval
  splitting grows only polynomially: halving the length divides the size by about 2 × 97, so it
  grows like n^7.6. That still puts a German IBAN (20 free digits) near 10^8 characters. Whether
  this is close to optimal is open. For plain regexes, communication-complexity lower bounds
  (Gruber and Johannsen, FoSSaCS 2008) look like the tool; with lookaheads, which express AND, OR
  and NOT, it becomes a question of Boolean formula size. The registers of step 4 sidestep it.
- **IBAN patterns take the electronic form only:** capitals, no spaces. Each covers one country;
  `python -m rexsum iban CC` makes the others, with `--layout` from the IBAN registry for
  countries that are not built in.
- **Damm** (a quasigroup, so nothing splits) comes out at 1,398,101 characters by direct
  elimination. Registers should handle Damm and Verhoeff, and might shrink the mod-11 patterns;
  not tried yet.

## Prior work

- Validation guides say a regex can only check the format and pair it with code
  ([example](https://techearl.com/regex-validate-credit-card-luhn)); tools such as re-search.py call a
  Luhn function after the match ([Didier Stevens, 2021](https://blog.didierstevens.com/2021/02/22/re-search-py-and-custom-validations/)).
- Steven Pemberton, *The Syntax of Credit Card Numbers* (CWI, Invisible XML Symposium 2026),
  writes the Luhn check as an ixml grammar: 20 states right to left, about 100 rules left to right
  ([paper](https://homepages.cwi.nl/~steven/Talks/2026/02-27-ixml/paper.html)). A grammar, not a regex.
- *Can a regex match valid card numbers?* ([Abstract Nonsense, 2025](https://abstractnonsense.xyz/blog/2025-08-31-can-a-regex-match-valid-card-numbers/))
  converts a Luhn automaton with the greenery library (Brzozowski's algebraic method): 32,461,605
  characters for even lengths and 48,236,673 for odd. Python's `re` runs it; grep and ripgrep run
  out of memory. This is the direct conversion that rexsum makes 1,500 times smaller.
- Divisibility regexes are puzzles (Codewars katas for binary multiples of 7 and decimal multiples
  of 4); [DivisibilityRegexes](https://github.com/Fiona1729/DivisibilityRegexes) generates them through
  JFLAP's plain conversion or with recursive PCRE, which JavaScript lacks.
- H. Gruber and M. Holzer, *From Finite Automata to Regular Expressions and Back — A Summary on
  Descriptional Complexity* ([arXiv:1405.5594](https://arxiv.org/abs/1405.5594)): worst-case
  2^Θ(n) blow-up, lower bounds through cycle rank and star height, and elimination-order heuristics
  (Delgado and Morais 2004; Lombardy, Régis-Gianas and Sakarovitch 2004; Moreira, Nabais and Reis
  2010).
- Y. Uezato, *Regular Expressions with Backreferences and Lookaheads Capture NLOG* (ICALP 2024,
  [arXiv:2404.17492](https://arxiv.org/abs/2404.17492)), stores numbers as the lengths of captured
  strings and compares them with backreferences inside lookaheads, the device behind the IBAN
  patterns, and proves that such regexes recognize exactly NLOG, the languages decidable in
  nondeterministic logarithmic space. Its constructions update captures inside loops, which
  JavaScript rules out (a repeated group resets on every iteration); here the steps are written out.

Apart from that Luhn conversion, I found no published regex that verifies a check digit (GTIN,
ISBN, ABA, elfproef, IBAN), and none small enough for a `pattern` attribute.

## Use it

```sh
python -m rexsum --list                     # the shipped schemes
python -m rexsum card                       # the pattern
python -m rexsum card --html                # as an <input> element
python -m rexsum custom --weights 1,3 --mod 10 --length 13     # your own weighted sum
python -m rexsum iban DE                    # an IBAN pattern (16 countries built in)
python -m rexsum iban LU --layout 3n13c     # any other country, layout from the IBAN registry
python build.py                             # rebuild patterns.json (a few minutes)
python -m pytest tests                      # check the shipped patterns
python tests/make_cases.py tests/cases.json && python tests/browser.py patterns.json tests/cases.json
node tests/speed.mjs patterns.json tests/cases.json speed.json
/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc tests/jsc.js -- patterns.json tests/cases.json
swiftc -O tests/safari.swift -o safari-check && ./safari-check patterns.json tests/cases.json
```

`patterns.json` holds every pattern with its size and parts. Python 3.10+, no dependencies; the
browser test needs Playwright (`playwright install chromium firefox webkit`), and the
JavaScriptCore and Safari tests run on macOS.

## Files

```
rexsum/regex.py      regex trees with simplifying constructors, printed in JavaScript syntax
rexsum/automata.py   automata: exploration, minimization
rexsum/elim.py       state elimination, greedy orders
rexsum/pipeline.py   the CRT split, period-first elimination, interval splitting, pattern assembly
rexsum/registers.py  IBAN: capture groups as registers
rexsum/specs.py      the shipped schemes;  rexsum/schemes.py  reference checkers and experiments
build.py             compile and test everything, write patterns.json
tests/               pytest, the browser and Safari checks with JavaScript off, V8 timings, the JavaScriptCore check
site/                the demo page
```
