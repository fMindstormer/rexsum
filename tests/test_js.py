"""The JavaScript side: js/compile.mjs prints the same patterns as `rexsum custom`, the npm package
exports the patterns of patterns.json, and the Python and npm packages carry the same version."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from rexsum import __version__
from rexsum.__main__ import custom

ROOT = Path(__file__).resolve().parent.parent
node = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node 20 or later")

CONFIGS = [  # weights, mod, the side the weights start from, length (None: any)
    ([1, 3], 10, "right", None), ([2, 1], 10, "right", None), ([3], 7, "left", None), ([1, 1], 3, "left", None),
    ([5, 2], 4, "right", None), ([1, 3], 10, "left", 6), ([-1, 2], 9, "right", 7), ([7, 3, 1], 10, "right", 9),
    ([1, 3], 10, "right", 8), ([2, 1], 10, "right", 5), ([3, 1], 5, "left", None), ([1, 2, 1], 6, "left", 4),
]


def run_node(script, *args):
    r = subprocess.run(["node", "--input-type=module", "-e", script, *args], capture_output=True, text=True,
                       cwd=ROOT, check=True)
    return json.loads(r.stdout)


@node
def test_js_compiler_prints_the_python_patterns():
    got = run_node("""
        import { compileCustom } from "./js/compile.mjs";
        const out = JSON.parse(process.argv[1]).map(([weights, mod, from, length]) =>
          compileCustom({ weights, mod, from, length, budget: 2e6 }));
        console.log(JSON.stringify(out));""", json.dumps(CONFIGS))
    for cfg, g in zip(CONFIGS, got):
        want = custom(*cfg)
        assert g["pattern"] == want["pattern"], cfg
        assert {int(q): c["construction"] for q, c in g["components"].items()} == \
            {q: c["construction"] for q, c in want["components"].items()}, cfg


@node
def test_js_budget_drops_only_what_is_too_long():
    got = run_node("""
        import { compileCustom } from "./js/compile.mjs";
        const isbn = { weights: [10, 9, 8, 7, 6, 5, 4, 3, 2, 1], mod: 11, from: "left", length: 10 };
        let small = null;
        try { compileCustom({ ...isbn, budget: 1000 }); } catch (e) { small = e.constructor.name; }
        const r = compileCustom({ ...isbn, budget: 1e6 });
        console.log(JSON.stringify({ small, length: r.length, tried: r.components["11"].tried }));""")
    assert got["small"] == "RangeError"
    # the cyclic construction is over a million characters, the interval one under 100,000
    assert got["tried"]["cyclic"] is None and got["tried"]["intervals"] < 100_000
    assert got["length"] == len(f"(?=\\d{{10}}$)(?:)") + got["tried"]["intervals"]


@node
def test_npm_package_exports_the_patterns():
    subprocess.run(["node", "js/build.mjs"], cwd=ROOT, check=True, capture_output=True)
    got = run_node("""
        import * as m from "./js/index.js";
        console.log(JSON.stringify({ named: Object.fromEntries(Object.entries(m).filter(([k]) => k !== "default" && k !== "schemes")),
                                     def: m.default, schemes: m.schemes }));""")
    lib = json.loads((ROOT / "patterns.json").read_text())
    want = {n: r["pattern"] for n, r in lib.items()}
    assert got["named"] == want and got["def"] == want
    assert got["schemes"] == {n: {"title": r["title"], "length": r["length"]} for n, r in lib.items()}


def test_versions_agree():
    pkg = json.loads((ROOT / "js" / "package.json").read_text())
    assert pkg["version"] == __version__
    assert sorted(pkg["files"]) == ["compile.d.ts", "compile.mjs", "index.d.ts", "index.js"]
