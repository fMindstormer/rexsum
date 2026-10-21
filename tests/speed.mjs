// V8 timing: compile time with the v flag, and match time on the test strings and on long inputs.
import fs from "fs";
const pats = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const cases = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const rows = {};
const rnd = (k) => Array.from({length: k}, () => "0123456789"[Math.floor(Math.random() * 10)]).join("");
for (const [name, r] of Object.entries(pats)) {
  let t0 = performance.now();
  const rx = new RegExp(`^(?:${r.pattern})$`, "v");
  rx.test("0");
  const compile = performance.now() - t0;
  let bad = 0, times = [];
  for (let rep = 0; rep < 5; rep++) for (const [s, want] of cases[name]) {
    t0 = performance.now(); const got = rx.test(s); times.push(performance.now() - t0);
    if (got !== want) bad++;
  }
  times.sort((a, b) => a - b);
  let long = 0;
  for (let i = 0; i < 20; i++) { const s = rnd(1000); t0 = performance.now(); rx.test(s); long = Math.max(long, performance.now() - t0); }
  rows[name] = {chars: r.pattern.length, compile_ms: +compile.toFixed(2), median_us: +(times[times.length >> 1] * 1000).toFixed(1),
                p99_us: +(times[Math.floor(times.length * 0.99)] * 1000).toFixed(1), long1000_ms: +long.toFixed(2), mismatches: bad};
  console.log(name, JSON.stringify(rows[name]));
}
fs.writeFileSync(process.argv[4], JSON.stringify(rows, null, 1));
