# rexsum

The last digit of a credit card number is a checksum. So is the last digit of an ISBN, a barcode,
an IMEI, a US routing number, and the two digits after the country code in an IBAN. Every
validation guide says the same thing about them: a regular expression can check the format, but
the checksum needs code.

rexsum compiles the checksum itself into a regular expression, and makes it small enough to hand
to the browser in a plain HTML `pattern` attribute. No JavaScript runs. The browser's own form
validation does the arithmetic:

```html
<input inputmode="numeric" pattern="(?=\d{12,19}$)(?=(?:(?:[02468]|[13579]…">   <!-- 24,471 characters -->
```

**[Try it in your browser](https://fmindstormer.github.io/rexsum/)**: eleven live fields, and the
page's only script runs its copy buttons.

The rest of this README explains what kind of machine a `pattern` attribute is, why getting
arithmetic into it is hard, the four constructions that make it fit, how the results hold up in
real browsers, and where this sits next to earlier work.

## The machine you are programming

A `pattern` attribute is a very small computer. The browser takes the pattern P, compiles
`^(?:P)$` with JavaScript's `v` flag, and runs it against the field's whole value whenever the
value changes. Out comes one bit: valid or invalid. That bit drives the `:invalid` CSS state and
blocks the form from submitting.

That is all you get. There are no variables, no loops that carry a value forward, no arithmetic,
no way to print anything. The only instructions are those of a JavaScript regex:

- characters and character classes (`7`, `[02468]`)
- sequence, alternation and repetition (`ab`, `a|b`, `a*`, `a{3}`)
- lookaheads and lookbehinds (`(?=…)`, `(?!…)`, `(?<=…)`): tests that look at the input without
  consuming it. Two lookaheads at one position mean AND, a negative one means NOT.
- capture groups and backreferences (`(…)`, `\5`): remember a piece of the input, and later
  require the same text again.

Two details shape everything below. A pattern the browser cannot compile is silently dropped, so
the field accepts anything: the patterns must be exactly right in every engine, not roughly
right. And an empty field is never checked (add `required` for that).

### Why a checksum fits in principle

Without groups and backreferences, a regex is a finite automaton in disguise. It remembers
nothing but which state it is in. That sounds hopeless for arithmetic, but a check digit only ever
needs a running remainder: Luhn's sum modulo 10, plus whether the next digit gets doubled. That
is a finite amount of memory, 20 states for Luhn, so a finite automaton can check it. By Kleene's
theorem, every finite automaton can be written as a regular expression.

For small cases the result is even readable. Here are the numbers whose digit sum is a multiple
of 3, which are exactly the multiples of 3, in 125 characters:

```
(?=\d+$)(?:(?:(?:[147]|[258][0369]*[258])(?:[0369]|[147][0369]*[258])*(?:[147][0369]*[147]|[258])|[0369]|[258][0369]*[147])*)
```

`[0369]` leaves the remainder alone, `[147]` adds 1, `[258]` adds 2, and the nesting walks
around a cycle of three remainders until it returns to zero.

### Why it fails in practice

The conversion exists, but it explodes. The same digit-sum language takes 1,463 characters for
modulus 5 and 16,647 for modulus 7, about eleven times more for each step. Converted the
textbook way, Luhn's 20-state automaton comes out at **37,396,808 characters**. That is not an
attribute you can ship; a published Luhn regex of that size makes grep and ripgrep run out of
memory (see Where this sits).

So the real problem is compression: find a regex for the same language that is thousands of times
smaller. rexsum gets Luhn to 24,465 characters, 1,500 times smaller.

## How the arithmetic gets into the syntax

### 1. Split the modulus with lookaheads

A number is divisible by 10 exactly when it is divisible by 2 and by 5. That is the Chinese
remainder theorem, and a JavaScript regex can express the "and": `(?=A$)B` matches exactly what
both `A` and `B` match. So Luhn becomes two independent checks, a mod-2 automaton and a mod-5
automaton, each converted on its own.

This is where most of the size goes away, because conversion cost grows much faster than the
number of states. The mod-2 part takes 198 characters. All the remaining difficulty is in the
mod-5 part.

### 2. Remove states in the right order

The textbook conversion, state elimination, removes the automaton's states one at a time and
rewrites the edges around each one. The order does not change the language, but it changes the
size by orders of magnitude, and no known rule finds the best order.

Luhn's weights repeat, 1, 2, 1, 2, …, so rexsum removes the states inside one period first. What
is left reads two digits at a time and has only 5 states, few enough to try all 120 orders and
keep the best. On Luhn's mod-5 part this gives 24,246 characters. The best greedy rule from the
literature gives 47,183, and the best of 178 random orders gives 72,000.

### 3. For fixed lengths, split at the best point

Many identifiers have a fixed length: 8 digits for EAN-8, 10 for ISBN-10. Then an automaton is
not needed at all. Take any interval of positions, say 3 to 6: what matters is the residue its
digits add to the sum, so the interval needs just one regex per residue. Two neighbouring
intervals combine by pairing residues that add up: "left adds u, right adds d − u", one
alternative per u. rexsum splits each interval at the point where its regexes come out shortest,
recursively, down to single positions.

This wins for short numbers (EAN-8 drops from 12,203 to 3,971 characters) and for the mod-11
schemes such as ISBN-10, where every digit adds a different residue so no character classes
merge.

### 4. For IBAN, turn capture groups into registers

IBANs are checked modulo 97. 97 is prime, so step 1 has nothing to split, and every digit adds a
different residue, so nothing merges either. A pure regex for a German IBAN would need about
10<sup>8</sup> characters (see Limits).

So the IBAN patterns leave regular expressions behind and use the other half of the instruction
set: capture groups. Three properties of JavaScript make a group usable as a register:

- **A group can hold a number.** At position 0, a lookahead that captures the first v
  characters stores v as the group's length: `(?=(...))` stores 3.
- **A stored number can be tested.** `(?=\5(?<=^...))` matches group 5's text from the start, then
  checks with a lookbehind that the match ended at position 3. It succeeds exactly when group 5
  holds 3.
- **A stored number stays put.** Lookaheads in JavaScript are atomic: once one succeeds, the
  engine never backtracks into it to try something else, so the captured value is final.

With registers, the pattern can compute the way you would on paper: read one character, update
the remainder, move on. Each step is a lookahead at position 0 that reads the input at a fixed
offset and writes fresh groups. Here is one alternative from the German pattern, part of the
step that computes a carry:

```
(?=\2(?<=^...))(?:(?=......[1-9]).|)
```

It reads: if group 2 holds 3, then capture one character if the digit at position 6 is 1 to 9,
and none otherwise. The alternatives for the other values of group 2 sit next to it, so the whole
step is a lookup table written as an alternation.

The arithmetic is shaped to keep these tables small. The remainder is held as two registers
(a, b), standing for 10a + b with a ≤ 13 and b ≤ 9, and is never reduced. Since 100 leaves 3
modulo 97, reading a digit d turns (a, b) into (b + ⌊(3a + d)/10⌋, (3a + d) mod 10), which keeps
every register under 14. A letter counts as two digits (A = 10, …, Z = 35) and takes two steps.

Two engine details forced the final shape:

- **The steps are written out, not looped.** JavaScript resets the groups inside a repeated
  group on every iteration, so a loop cannot carry a register forward. Each step gets its own
  groups, and the pattern grows linearly with the IBAN's length: about 2,500 characters per
  digit, 59,966 for Germany.
- **Repeats are written out as dots.** `...` rather than `.{3}`: V8 gives every counted repeat
  a loop register, and with thousands of them the German pattern takes 715 ms to compile instead
  of 58.

Backreferences take these patterns outside the regular languages, so strictly speaking they are
no longer regular expressions. The `pattern` attribute accepts them all the same.

### Keeping the output small

Underneath all four steps, the regex builder (`rexsum/regex.py`) simplifies as it goes: single
characters merge into classes, alternatives that share a first or last item are factored, and
repeats become `{n}` and `+`. Every pattern uses only syntax that is valid under the `v` flag,
which is stricter than older JavaScript about what may appear inside a character class.

## Results

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

The times are V8 in Node 24 on an Apple M4.

### Do they hold up in real browsers?

**Correctness.** Every pattern agrees with a reference implementation on 23,000 to 27,000 test
strings in Python, and on 780 more in V8 and in JavaScriptCore (`tests/speed.mjs`,
`tests/jsc.js`). The same 780 were entered into a real `<input>` with JavaScript disabled in
Chromium 156 and WebKit 27.2 (`tests/browser.py`), and in Safari 27's own engine on macOS
(`tests/safari.swift`). The `pattern` attribute alone gets every one right. Firefox is not tested
yet.

**Speed.** The first keystroke in a field compiles its pattern. In Chromium that takes 2 to 62 ms
(189 ms for ISBN-10), and every later keystroke a few microseconds. Safari compiles the pattern
again at every keystroke, but quickly: 0.1 to 2.8 ms, growing with the pattern's length. Regex
engines that backtrack can blow up on unlucky input, but these patterns stay linear: 1,000-digit
inputs take about 2 ms at most.

**Size on the wire.** Servers compress HTML, and the patterns compress well, 8 to 45 times:
Luhn's 24,465 characters gzip to 542 bytes and the German IBAN's 59,966 to 6.6 kB. GitHub Pages
sends the demo page, 358 kB with eleven fields, as 29 kB.

## Where this sits

**Practice.** Validation guides say a regex can check a card number's format and pair it with
code for the Luhn digit ([example](https://techearl.com/regex-validate-credit-card-luhn)). Tools
such as re-search.py call a Luhn function after the match
([Didier Stevens, 2021](https://blog.didierstevens.com/2021/02/22/re-search-py-and-custom-validations/)).
Regexes for divisibility are known puzzles (Codewars katas for binary multiples of 7 and decimal
multiples of 4), and [DivisibilityRegexes](https://github.com/Fiona1729/DivisibilityRegexes)
generates them through JFLAP's plain conversion or with recursive PCRE, which JavaScript lacks.

**The direct conversion.** *Can a regex match valid card numbers?*
([Abstract Nonsense, 2025](https://abstractnonsense.xyz/blog/2025-08-31-can-a-regex-match-valid-card-numbers/))
answers yes by converting a Luhn automaton with the greenery library (Brzozowski's algebraic
method): 32,461,605 characters for even lengths and 48,236,673 for odd. Python's `re` runs it;
grep and ripgrep run out of memory. This is the baseline that rexsum makes 1,500 times smaller.

**A grammar instead of a regex.** Steven Pemberton, *The Syntax of Credit Card Numbers* (CWI,
Invisible XML Symposium 2026), writes the Luhn check as an ixml grammar: 20 states read right to
left, about 100 rules left to right
([paper](https://homepages.cwi.nl/~steven/Talks/2026/02-27-ixml/paper.html)). A grammar is more
powerful than a regex, and browsers do not run it.

**The theory of conversion.** H. Gruber and M. Holzer, *From Finite Automata to Regular
Expressions and Back — A Summary on Descriptional Complexity*
([arXiv:1405.5594](https://arxiv.org/abs/1405.5594)), survey the field: conversion can blow up
exponentially in the worst case, lower bounds come from cycle rank and star height, and several
heuristics choose the elimination order (Delgado and Morais 2004; Lombardy, Régis-Gianas and
Sakarovitch 2004; Moreira, Nabais and Reis 2010). Steps 1 to 3 above are structure-specific
alternatives to those general heuristics, and on Luhn the period-first order comes out at about
half the size of the best greedy rule.

**Registers in regexes.** Y. Uezato, *Regular Expressions with Backreferences and Lookaheads
Capture NLOG* (ICALP 2024, [arXiv:2404.17492](https://arxiv.org/abs/2404.17492)), stores numbers
as the lengths of captured strings and compares them with backreferences inside lookaheads, the
same device as step 4, and proves that such regexes recognize exactly NLOG, the languages
decidable in nondeterministic logarithmic space. Its constructions update captures inside loops,
which JavaScript rules out; step 4 writes the steps out instead, and its arithmetic is designed
around mod 97 and around how V8 compiles patterns.

**What is new here.** Apart from the Luhn conversion above, I found no published regex that
verifies a check digit (GTIN, ISBN, ABA, elfproef, IBAN), and none small enough for a `pattern`
attribute. The new parts are the constructions that get there (the lookahead CRT split,
period-first elimination, interval splitting, and a practical mod-97 register machine within
JavaScript's rules) and the check that the result works, with JavaScript off, in real browsers.

## Limits and open questions

- **Prime moduli are expensive.** The language "digits whose sum is a multiple of 5" already needs
  stars nested five deep (McNaughton: for bideterministic languages, star height equals the cycle
  rank of the minimal automaton, here a complete graph on 5 states). The constructions here grow
  like 4^(q−1) for modulus q.
- **How small can a pure-regex IBAN be?** Multiples of 97 with 4, 6 and 8 digits need 524, 9,653
  and 100,133 characters. Each country fixes the length, so interval splitting grows only
  polynomially: halving the length divides the size by about 2 × 97, so it grows like n^7.6. That
  still puts a German IBAN (20 free digits) near 10^8 characters. Whether this is close to optimal
  is open. For plain regexes, communication-complexity lower bounds (Gruber and Johannsen, FoSSaCS
  2008) look like the tool; with lookaheads, which express AND, OR and NOT, it becomes a question
  of Boolean formula size. The registers of step 4 sidestep the question.
- **IBAN patterns take the electronic form only:** capitals, no spaces. Each covers one country;
  `python -m rexsum iban CC` makes the others, with `--layout` from the IBAN registry for
  countries that are not built in.
- **Damm** (a quasigroup, so nothing splits) comes out at 1,398,101 characters by direct
  elimination. Registers should handle Damm and Verhoeff, and might shrink the mod-11 patterns;
  not tried yet.

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
