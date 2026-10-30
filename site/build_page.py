"""Build the demo page (site/index.html), one standalone example per scheme (site/examples/), and
the README's results table, from patterns.json and speed.json."""
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from rexsum.meta import SCHEMES, keyboard  # noqa: E402

lib = json.loads((ROOT / "patterns.json").read_text())
speed = json.loads((ROOT / "speed.json").read_text())
facts = json.loads((ROOT / "site" / "facts.json").read_text())

# the demo page's fields, with a short description of each format
FEATURED = [
    ("card", "12 to 19 digits, Luhn"),
    ("imei", "15 digits, Luhn"),
    ("isbn13", "978 or 979, then 10 digits"),
    ("isbn10", "9 digits, then a digit or X"),
    ("upca", "12 digits"),
    ("ean8", "8 digits"),
    ("issn", "7 digits, then a digit or X"),
    ("aba", "9 digits, weights 3, 7, 1"),
    ("sin", "9 digits, Luhn"),
    ("bsn", "9 digits, the elfproef"),
    ("iban_de", "DE, then 20 digits, no spaces"),
]

# the README's names for the schemes, in its table
README_TITLES = {
    "luhn": "Luhn, any length", "card": "Payment card, 12–19 digits", "card16": "Payment card, 16 digits",
    "imei": "IMEI (15 digits)", "sin": "Canadian SIN (9 digits)", "gtin": "GTIN, any length", "ean8": "EAN-8",
    "upca": "UPC-A", "ean13": "EAN-13", "isbn13": "ISBN-13", "gtin14": "GTIN-14", "aba": "ABA routing number",
    "isbn10": "ISBN-10", "issn": "ISSN", "bsn": "BSN (Dutch elfproef)", "iban_de": "IBAN, Germany",
    "iban_nl": "IBAN, Netherlands", "iban_gb": "IBAN, United Kingdom", "iban_fr": "IBAN, France",
    "lei": "LEI (Legal Entity Identifier)",
}

CONSTRUCTION = {"cyclic": "period-first elimination", "cyclic, any length": "period-first elimination",
                "intervals": "interval splitting", "registers": "capture groups as registers"}
facts["iban_de"] = f"{lib['iban_de']['length']:,}"
facts["iban_de_groups"] = str(lib["iban_de"]["components"]["97"]["groups"])
facts["lei"] = f"{lib['lei']['length']:,}"


def fmt(n):
    return f"{n:,}"


def fill(text, values):
    return re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], text)


# standalone examples: no script, no external files
example = (ROOT / "site" / "example_template.html").read_text()
out_dir = ROOT / "site" / "examples"
out_dir.mkdir(exist_ok=True)
for old in out_dir.glob("*.html"):
    if old.stem not in lib:
        old.unlink()
for name, r in lib.items():
    m = SCHEMES[name]
    (out_dir / f"{name}.html").write_text(fill(example, {
        "name": name, "title": html.escape(m["title"]), "shape": html.escape(m["shape"], quote=True),
        "valid": m["valid"], "invalid": m["invalid"], "keyboard": keyboard(name), "chars": fmt(r["length"]),
        "pattern": html.escape(r["pattern"], quote=True)}))

cards = []
for name, shape in FEATURED:
    r, m = lib[name], SCHEMES[name]
    cards.append(f'''
    <div class="field">
      <label for="in-{name}"><span class="fname">{html.escape(m["title"])}</span><span class="fshape">{html.escape(shape)}</span></label>
      <input id="in-{name}" name="{name}" value="{m["valid"]}" placeholder=" " {keyboard(name)} autocomplete="off" spellcheck="false"
        pattern="{html.escape(r['pattern'], quote=True)}">
      <p class="status" aria-hidden="true"></p>
      <div class="fmeta"><span class="tnum">{fmt(r['length'])}-character pattern</span>
        <span class="actions"><button type="button" class="copy" data-for="in-{name}">Copy pattern</button>
        <a class="copy" href="examples/{name}.html" download="rexsum-{name}.html">Download HTML</a></span></div>
    </div>''')

rows = []
for name, r in lib.items():
    comps = r["components"]
    parts = []
    for q, c in sorted(comps.items(), key=lambda x: int(x[0])):
        parts.append(f"mod {q}: {fmt(c['length'])}")
    big = max(comps.items(), key=lambda x: x[1]["length"])
    sp = speed["rows"][name]
    rows.append(f'''<tr><td>{html.escape(r['title'])}</td><td class="num">{fmt(r['length'])}</td>
      <td class="parts">{'<br>'.join(parts)}</td><td>{CONSTRUCTION[big[1]['construction']]}</td>
      <td class="num">{sp['compile_ms']:.0f}</td><td class="num">{sp['median_us']:.1f}</td></tr>''')

page = (ROOT / "site" / "template.html").read_text()
page = page.replace("<!--CARDS-->", "".join(cards)).replace("<!--ROWS-->", "".join(rows))
for k, v in facts.items():
    page = page.replace("{{" + k + "}}", v)
(ROOT / "site" / "index.html").write_text(page)

# the README's table, between its markers
table = ["| Scheme | Characters | V8 compile | Median match |", "|---|---:|---:|---:|"]
for name, r in lib.items():
    sp = speed["rows"][name]
    us = sp["median_us"]
    match = f"{us:.1f} µs" if us < 10 else f"{us:.0f} µs"
    table.append(f"| {README_TITLES[name]} | {fmt(r['length'])} | {sp['compile_ms']:.0f} ms | {match} |")
m = speed["meta"]
table += ["", f"V8 {m['v8']} in Node {m['node'].lstrip('v')}, {m['cpu']}, measured {m['date']} (`speed.json`)."]
readme = (ROOT / "README.md").read_text()
readme = re.sub(r"(<!-- table -->\n).*?(\n<!-- /table -->)", lambda m: m.group(1) + "\n".join(table) + m.group(2),
                readme, flags=re.S)
(ROOT / "README.md").write_text(readme)
print(f"site/index.html: {len(page) / 1000:.0f} kB, {len(lib)} examples in site/examples/")
