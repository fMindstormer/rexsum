// Every pattern under the v flag the pattern attribute uses, in V8: correctness on the test strings
// (any mismatch exits with status 1), then timings, which are informational: compile time, match
// time on the test strings, and the slowest of 20 random 1,000-digit inputs.
//   node tests/speed.mjs patterns.json tests/cases.json speed.json
import fs from "fs";
import os from "os";
const pats = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const cases = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const rows = {};
let failed = 0;
const rnd = (k) => Array.from({length: k}, () => "0123456789"[Math.floor(Math.random() * 10)]).join("");
for (const [name, r] of Object.entries(pats)) {
  let t0 = performance.now();
  const rx = new RegExp(`^(?:${r.pattern})$`, "v");
  rx.test("0");
  const compile = performance.now() - t0;
  const bad = [], times = [];
  for (let rep = 0; rep < 5; rep++) for (const [s, want] of cases[name]) {
    t0 = performance.now(); const got = rx.test(s); times.push(performance.now() - t0);
    if (rep === 0 && got !== want) bad.push(s);
  }
  failed += bad.length;
  times.sort((a, b) => a - b);
  let long = 0;
  for (let i = 0; i < 20; i++) { const s = rnd(1000); t0 = performance.now(); rx.test(s); long = Math.max(long, performance.now() - t0); }
  rows[name] = {chars: r.pattern.length, compile_ms: +compile.toFixed(2), median_us: +(times[times.length >> 1] * 1000).toFixed(1),
                p99_us: +(times[Math.floor(times.length * 0.99)] * 1000).toFixed(1), long1000_ms: +long.toFixed(2), mismatches: bad.length};
  console.log(name, JSON.stringify(rows[name]), bad.length ? `MISMATCHES ${bad.slice(0, 3).join(" ")}` : "");
}
const meta = {date: new Date().toISOString().slice(0, 10), node: process.version, v8: process.versions.v8,
              platform: `${os.platform()} ${os.release()} ${os.arch()}`, cpu: os.cpus()[0]?.model ?? "unknown"};
if (process.argv[4]) fs.writeFileSync(process.argv[4], JSON.stringify({meta, rows}, null, 1) + "\n");
console.log(JSON.stringify(meta));
if (failed) { console.error(`${failed} mismatches`); process.exit(1); }
