# rexsum

The last digit of a credit card number is a checksum. So is the last digit of an ISBN, a barcode
or an IMEI, the two digits after the country code in an IBAN, and the letter at the end of a
Spanish identity number. rexsum compiles the checksum itself into a regular expression, small
enough for a plain HTML `pattern` attribute. No JavaScript runs: the browser's own form
validation does the arithmetic.

```
pip install rexsum
```

It needs Python 3.10 or later and nothing else.

```sh
rexsum --list                     # the shipped schemes and their sizes
rexsum card                       # the pattern for payment card numbers
rexsum card --html                # as an <input> element, with the right keyboard
rexsum iban                       # one IBAN pattern for every country
rexsum iban DE                    # a smaller one for a single country
rexsum custom --weights 1,3 --mod 10 --length 13     # a weighted check-digit sum of your own
```

`rexsum card --html` prints

```html
<input inputmode="numeric" pattern="(?=\d{12,19}$)(?=(?:(?:[02468]|[13579]…">   <!-- 24,471 characters -->
```

and the field turns invalid whenever the last digit is wrong.

Shipped: Luhn (payment cards, IMEI, Canadian SIN), GTIN/EAN/UPC, ISBN-10 and ISBN-13, ISSN, US
bank routing numbers, Dutch BSN, IBAN (every country, or one), LEI, RF creditor references, VIN,
Spanish DNI/NIE, Finnish HETU, Belgian OGM-VCS and French NIR. Each pattern was tested against a
reference implementation in Python, V8, Safari's engine, and real `<input>` fields in Chromium,
Firefox and WebKit with JavaScript off.

The same patterns are on npm (`npm install rexsum`), and the
[generator](https://fmindstormer.github.io/rexsum/generator.html) makes a ready `<input>` in the
browser. How the arithmetic fits into regex syntax, and how small a pure regex can be:
[github.com/fMindstormer/rexsum](https://github.com/fMindstormer/rexsum).
