"""Check every pattern in Chromium, with JavaScript turned off: the HTML pattern attribute alone
must mark each test string valid or invalid as the reference checker says."""
import html
import json
import sys
import time

from playwright.sync_api import sync_playwright

patterns = json.load(open(sys.argv[1]))
cases = json.load(open(sys.argv[2]))
only = set(sys.argv[3:])

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(java_script_enabled=False)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text))
    total_bad = 0
    for name, r in patterns.items():
        if only and name not in only:
            continue
        errors.clear()
        t0 = time.time()
        page.set_content(f'<form><input id="f" pattern="{html.escape(r["pattern"], quote=True)}"></form>')
        load = time.time() - t0
        inp = page.locator("#f")
        bad, t1 = [], time.time()
        for s, want in cases[name]:
            inp.fill(s)
            got = page.locator("#f:valid").count() == 1
            if got != want:
                bad.append((s, want, got))
        dt = (time.time() - t1) / len(cases[name]) * 1000
        total_bad += len(bad)
        print(f"{name:7s} {r['length']:>8,} chars: load {load * 1000:.0f} ms, {len(cases[name])} strings, "
              f"{dt:.1f} ms per check, mismatches {len(bad)} {bad[:3]} {errors[:2]}", flush=True)
    b.close()
sys.exit(1 if total_bad else 0)
