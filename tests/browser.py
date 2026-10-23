"""Check every pattern in Chromium, Firefox and WebKit with JavaScript turned off: the HTML pattern
attribute alone must mark each test string valid or invalid as the reference checker says. A second
page, with JavaScript on, times the checks: the first one compiles the pattern, and after that every
keystroke costs one check."""
import argparse
import html
import json
import sys

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument("patterns")
ap.add_argument("cases")
ap.add_argument("names", nargs="*")
ap.add_argument("--browser", default="chromium,firefox,webkit")
args = ap.parse_args()
patterns = json.load(open(args.patterns))
cases = json.load(open(args.cases))

TIME = """cases => {
  const f = document.getElementById("f");
  let t0 = performance.now();
  f.value = cases[0][0];
  f.matches(":valid");
  const first = performance.now() - t0;
  t0 = performance.now();
  for (const [s] of cases) { f.value = s; f.matches(":valid"); }
  return [first, (performance.now() - t0) / cases.length];
}"""

total_bad = 0
with sync_playwright() as p:
    for engine in args.browser.split(","):
        b = getattr(p, engine).launch()
        print(engine, b.version, flush=True)
        timer = b.new_context().new_page()
        page = b.new_context(java_script_enabled=False).new_page()
        errors = []
        page.on("console", lambda m: errors.append(m.text))
        for name, r in patterns.items():
            if args.names and name not in args.names:
                continue
            errors.clear()
            doc = f'<form><input id="f" pattern="{html.escape(r["pattern"], quote=True)}"></form>'
            timer.set_content(doc)
            first, each = timer.evaluate(TIME, cases[name])
            page.set_content(doc)
            inp = page.locator("#f")
            bad = []
            for s, want in cases[name]:
                inp.fill(s)
                if (page.locator("#f:valid").count() == 1) != want:
                    bad.append(s)
            total_bad += len(bad)
            print(f"{engine:8s} {name:8s} {r['length']:>8,} chars: first check {first:.0f} ms, then {each * 1000:,.0f} µs each, "
                  f"{len(cases[name])} strings, mismatches {len(bad)} {' '.join(bad[:3])} {errors[:2]}", flush=True)
        b.close()
sys.exit(1 if total_bad else 0)
