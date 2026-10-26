"""Check every pattern in Chromium, Firefox and WebKit (Playwright's builds) with JavaScript turned
off: the HTML pattern attribute alone must mark each test string valid or invalid as expected.
Then the standalone examples in site/examples/, opened from disk: each must accept its valid
sample, reject its invalid one, and reject an empty value because the field is required; a field
without `required` must accept the empty value. A second page, with JavaScript on, times the
checks: the first one compiles the pattern, and after that every keystroke costs one check. Any
wrong answer exits with status 1; the times are informational.
    python tests/browser.py patterns.json tests/cases.json [names ...] [--browser chromium,firefox,webkit] [--report r.json]"""
import argparse
import html
import json
import platform
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rexsum.meta import SCHEMES  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("patterns")
ap.add_argument("cases")
ap.add_argument("names", nargs="*")
ap.add_argument("--browser", default="chromium,firefox,webkit")
ap.add_argument("--examples", default=str(Path(__file__).resolve().parent.parent / "site" / "examples"))
ap.add_argument("--report", help="write the results as JSON")
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
report = {"date": date.today().isoformat(), "machine": f"{platform.system()} {platform.machine()}",
          "playwright": True, "engines": {}}
with sync_playwright() as p:
    for engine in args.browser.split(","):
        b = getattr(p, engine).launch()
        print(engine, b.version, flush=True)
        rep = report["engines"][engine] = {"version": b.version, "patterns": {}, "examples": {}}
        timer = b.new_context().new_page()
        page = b.new_context(java_script_enabled=False).new_page()
        for name, r in patterns.items():
            if args.names and name not in args.names:
                continue
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
            rep["patterns"][name] = {"strings": len(cases[name]), "mismatches": bad,
                                     "first_check_ms": round(first, 2), "each_check_us": round(each * 1000, 1)}
            print(f"{engine:8s} {name:8s} {r['length']:>8,} chars: first check {first:.0f} ms, then {each * 1000:,.0f} µs each, "
                  f"{len(cases[name])} strings, mismatches {len(bad)} {' '.join(bad[:3])}", flush=True)

        # field semantics, separate from the checksum: the empty value
        page.set_content(f'<input id="f" pattern="{html.escape(patterns["card"]["pattern"], quote=True)}">')
        page.locator("#f").fill("")
        optional_ok = page.locator("#f:valid").count() == 1
        total_bad += not optional_ok
        rep["empty_without_required_is_valid"] = optional_ok

        for f in sorted(Path(args.examples).glob("*.html")):
            name = f.stem
            if args.names and name not in args.names:
                continue
            m = SCHEMES[name]
            page.goto(f.as_uri())
            inp = page.locator("#f")
            got = {"valid_sample": page.locator("#f:valid").count() == 1}
            inp.fill(m["invalid"])
            got["invalid_sample_rejected"] = page.locator("#f:invalid").count() == 1
            inp.fill("")
            got["empty_rejected"] = page.locator("#f:invalid").count() == 1
            inp.fill(m["valid"])
            got["valid_again"] = page.locator("#f:valid").count() == 1
            failures = [k for k, ok in got.items() if not ok]
            total_bad += len(failures)
            rep["examples"][name] = got
            if failures:
                print(f"{engine:8s} example {name}: FAILED {failures}", flush=True)
        print(f"{engine:8s} examples: {len(rep['examples'])} checked; empty field without required valid: {optional_ok}", flush=True)
        b.close()
if args.report:
    Path(args.report).write_text(json.dumps(report, indent=1) + "\n")
print("all correct" if not total_bad else f"{total_bad} failures")
sys.exit(1 if total_bad else 0)
