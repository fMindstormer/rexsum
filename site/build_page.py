"""Build the demo page: site/index.html, published by GitHub Pages."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
lib = json.loads((ROOT / "patterns.json").read_text())
speed = json.loads((ROOT / "speed.json").read_text())
facts = json.loads((ROOT / "site" / "facts.json").read_text())

FEATURED = [
    ("card", "Payment card", "12 to 19 digits, Luhn", "4111111111111111", "numeric"),
    ("imei", "IMEI", "15 digits, Luhn", "490154203237518", "numeric"),
    ("isbn13", "ISBN-13", "978 or 979, then 10 digits", "9780306406157", "numeric"),
    ("isbn10", "ISBN-10", "9 digits, then a digit or X", "080442957X", "text"),
    ("upca", "UPC-A barcode", "12 digits", "036000291452", "numeric"),
    ("ean8", "EAN-8 barcode", "8 digits", "96385074", "numeric"),
    ("issn", "ISSN", "7 digits, then a digit or X", "03785955", "text"),
    ("aba", "US bank routing number", "9 digits, weights 3, 7, 1", "011000015", "numeric"),
    ("sin", "Canadian SIN", "9 digits, Luhn", "046454286", "numeric"),
    ("bsn", "Dutch BSN", "9 digits, the elfproef", "111222333", "numeric"),
]

CONSTRUCTION = {"cyclic": "period-first elimination", "cyclic, any length": "period-first elimination",
                "intervals": "interval splitting"}


def fmt(n):
    return f"{n:,}"


cards = []
for name, title, shape, example, mode in FEATURED:
    r = lib[name]
    cards.append(f'''
    <div class="field">
      <label for="in-{name}"><span class="fname">{html.escape(title)}</span><span class="fshape">{html.escape(shape)}</span></label>
      <input id="in-{name}" name="{name}" value="{example}" placeholder=" " inputmode="{mode}" autocomplete="off" spellcheck="false"
        pattern="{html.escape(r['pattern'], quote=True)}">
      <p class="status" aria-hidden="true"></p>
      <div class="fmeta"><span class="tnum">{fmt(r['length'])}-character pattern</span>
        <button type="button" class="copy" data-for="in-{name}">Copy pattern</button></div>
    </div>''')

rows = []
for name, r in lib.items():
    comps = r["components"]
    parts = []
    for q, c in sorted(comps.items(), key=lambda x: int(x[0])):
        parts.append(f"mod {q}: {fmt(c['length'])}")
    big = max(comps.items(), key=lambda x: x[1]["length"])
    sp = speed[name]
    rows.append(f'''<tr><td>{html.escape(r['title'])}</td><td class="num">{fmt(r['length'])}</td>
      <td class="parts">{'<br>'.join(parts)}</td><td>{CONSTRUCTION[big[1]['construction']]}</td>
      <td class="num">{sp['compile_ms']:.0f}</td><td class="num">{sp['median_us']:.1f}</td></tr>''')

page = (ROOT / "site" / "template.html").read_text()
page = page.replace("<!--CARDS-->", "".join(cards)).replace("<!--ROWS-->", "".join(rows))
for k, v in facts.items():
    page = page.replace("{{" + k + "}}", v)
(ROOT / "site" / "index.html").write_text(page)
print(f"site/index.html: {len(page) / 1000:.0f} kB")
