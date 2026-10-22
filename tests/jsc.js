// Check every pattern in JavaScriptCore, Safari's regex engine, with the jsc shell that ships with
// macOS (/System/Library/Frameworks/JavaScriptCore.framework/Versions/A/Helpers/jsc):
//   jsc tests/jsc.js -- patterns.json tests/cases.json [name ...]
const pats = JSON.parse(readFile(arguments[0]));
const cases = JSON.parse(readFile(arguments[1]));
const only = arguments.slice(2);
let totalBad = 0;
for (const [name, r] of Object.entries(pats)) {
  if (only.length && !only.includes(name)) continue;
  let t0 = preciseTime();
  const rx = new RegExp(`^(?:${r.pattern})$`, "v");
  rx.test("0");
  const compile = (preciseTime() - t0) * 1000;
  const bad = [];
  t0 = preciseTime();
  for (const [s, want] of cases[name]) if (rx.test(s) !== want) bad.push(s);
  const each = (preciseTime() - t0) / cases[name].length * 1e6;
  totalBad += bad.length;
  print(`${name.padEnd(8)} ${String(r.pattern.length).padStart(7)} chars: compile ${compile.toFixed(0)} ms, ` +
        `${cases[name].length} strings, ${each.toFixed(1)} us each, mismatches ${bad.length} ${bad.slice(0, 3).join(" ")}`);
}
if (totalBad) throw new Error(`${totalBad} mismatches`);
