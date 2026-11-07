"""The generator page in Chromium, Firefox and WebKit (Playwright's builds), served as GitHub Pages
serves it: a shipped scheme must give the pattern of patterns.json, weights of one's own the
pattern `rexsum custom` prints, and the field it shows must accept a valid number and reject one
with its last digit changed. Any failure exits with status 1.
    python tests/generator.py [--browser chromium,firefox,webkit]"""
import argparse
import html
import json
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "site"))
from publish import publish  # noqa: E402
from rexsum.__main__ import custom  # noqa: E402
from rexsum.meta import SCHEMES  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--browser", default="chromium,firefox,webkit")
args = ap.parse_args()
lib = json.loads((ROOT / "patterns.json").read_text())

CASES = [  # the address after #, and the pattern the page must produce
    ("card", lib["card"]["pattern"]),
    ("dni", lib["dni"]["pattern"]),
    ("weights=1,3&mod=10&from=right&length=13", custom([1, 3], 10, "right", 13)["pattern"]),
    ("weights=7,3,1&mod=10&from=right&length=9", custom([7, 3, 1], 10, "right", 9)["pattern"]),
    ("weights=3&mod=7&from=left", custom([3], 7, "left", None)["pattern"]),
]

site = publish(tempfile.mkdtemp())


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".json": "application/json"}

    def log_message(self, *a):
        pass


server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_address[1]}/generator.html"

failed = 0
with sync_playwright() as p:
    for engine in args.browser.split(","):
        b = getattr(p, engine).launch()
        page = b.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        print(engine, b.version, flush=True)
        for hash_, want in CASES:
            page.goto("about:blank")
            page.goto(f"{base}#{hash_}")
            page.wait_for_function("document.getElementById('out').value !== '' || document.querySelector('#info.error')",
                                   timeout=90_000)
            out = page.input_value("#out")
            info = page.text_content("#info")
            got = html.unescape(out.split(' pattern="', 1)[1][:-2]) if ' pattern="' in out else None
            field = page.locator("#preview input")
            ok_valid = field.evaluate("f => f.value !== '' && f.matches(':valid')")
            v = field.input_value()
            field.fill(v[:-1] + ("1" if v[-1] != "1" else "2"))   # a different last character
            ok_invalid = field.evaluate("f => f.matches(':invalid')")
            name = hash_ if hash_ in SCHEMES else None
            ok_attrs = name is None or (f'name="{name}" required ' in out and f'title="{html.escape(SCHEMES[name]["shape"])}"' in out)
            ok = got == want and ok_valid and ok_invalid and ok_attrs and not errors
            failed += not ok
            print(f"  {hash_:44s} {len(out):>8,} chars  pattern {'same' if got == want else 'DIFFERENT'}"
                  f"  valid sample {'accepted' if ok_valid else 'NOT ACCEPTED'}  changed {'rejected' if ok_invalid else 'NOT REJECTED'}"
                  f"{'' if ok_attrs else '  ATTRIBUTES WRONG'}{'  ERRORS ' + '; '.join(errors) if errors else ''}  | {info}", flush=True)
            errors.clear()
        b.close()
server.shutdown()
sys.exit(1 if failed else 0)
