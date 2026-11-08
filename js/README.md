# rexsum

The last digit of a credit card number is a checksum. So is the last digit of an ISBN, a barcode
or an IMEI, the two digits after the country code in an IBAN, and the letter at the end of a
Spanish identity number. rexsum compiles the checksum itself into a regular expression, small
enough for a plain HTML `pattern` attribute. The browser's own form validation then does the
arithmetic, with no validation code of yours.

```
npm install rexsum
```

```jsx
import { card, iban } from "rexsum";

// React: the field is invalid whenever the Luhn digit is wrong
<input inputMode="numeric" pattern={card} />

// the DOM: any country's IBAN
document.querySelector("#iban").pattern = iban;

// in a script, with the attribute's own semantics
new RegExp(`^(?:${card})$`, "v").test("4111111111111111");   // true
```

Each export is a string, so a bundler keeps only the patterns you import. A payment card pattern
is 24,471 characters and gzips to 550 bytes.

| Export | Scheme |
|---|---|
| `luhn`, `card`, `card16`, `imei`, `sin` | Luhn: any length, payment cards (12 to 19 digits, or 16), IMEI, Canadian SIN |
| `gtin`, `ean8`, `upca`, `ean13`, `isbn13`, `gtin14` | GTIN barcodes and ISBN-13 |
| `isbn10`, `issn` | ISBN-10, ISSN (check character X for 10) |
| `aba`, `bsn` | US bank routing numbers, Dutch BSN |
| `iban`, `iban_de`, `iban_nl`, `iban_gb`, `iban_fr` | IBAN: every country, or one |
| `lei`, `rf` | Legal Entity Identifiers, RF creditor references |
| `vin`, `dni`, `hetu`, `ogm`, `nir` | VIN, Spanish DNI/NIE, Finnish HETU, Belgian OGM-VCS, French NIR |
| `aadhaar`, `damm`, `verhoeff` | Indian Aadhaar numbers; Damm and Verhoeff check digits, 1 to 20 digits |

`schemes` gives each one's title and length. The patterns expect what the scheme writes: capitals,
no spaces. Every pattern was tested against a reference implementation in Python, V8 and
Safari's engine, and in real `<input>` fields in Chromium, Firefox and WebKit with JavaScript off.

## Your own weights

```js
import { compileCustom, inputElement } from "rexsum/compile";

const { pattern } = compileCustom({ weights: [1, 3], mod: 10, from: "right", length: 13 });
inputElement(pattern);   // '<input inputmode="numeric" pattern="(?=\d{13}$)…">'
```

The weights repeat from the rightmost digit (`from: "right"`) or the leftmost, and the weighted
sum must be 0 mod `mod`. Leave out `length` for any number of digits. Some moduli and periods
need enormous patterns; `budget: 1e6` gives up beyond a million characters instead of running
out of memory. The output is the same, character for character, as the Python command
`rexsum custom` (`pip install rexsum`).

The [generator](https://fmindstormer.github.io/rexsum/generator.html) does both in the browser.
How the arithmetic fits into regex syntax:
[github.com/fMindstormer/rexsum](https://github.com/fMindstormer/rexsum).
