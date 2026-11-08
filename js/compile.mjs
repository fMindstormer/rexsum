// Weighted check-digit sums compiled to a regex for the HTML pattern attribute: the constructions of
// `rexsum custom` (rexsum/pipeline.py, regex.py, elim.py, automata.py) in JavaScript, for the
// generator page and the npm package. It prints the same pattern as the Python, character for
// character (tests/test_js.py).
//
//   import { compileCustom, inputElement } from "rexsum/compile";
//   compileCustom({ weights: [1, 3], mod: 10, from: "right", length: 13 }).pattern

const DIGITS = "0123456789";
const mod = (a, q) => ((a % q) + q) % q;

// ---------------------------------------------------------------- regexes (rexsum/regex.py)
// Small immutable trees, interned so that equal trees are the same object; `text` prints them.
const EPS = { k: "eps", id: 0, t: "" };
let table = new Map();
let nextId = 1;
let revMemo = new Map();
let budget = Infinity;

// A regex longer than the budget is given up: the candidate, elimination order or split that made
// it is dropped. Dropped ones are longer than the budget, so a pattern that fits is unchanged.
class TooLong extends Error {}

function attempt(f) {
  try {
    return f();
  } catch (e) {
    if (e instanceof TooLong) return null;
    throw e;
  }
}

function reset() {
  table = new Map();
  nextId = 1;
  revMemo = new Map();
}

function node(key, fields) {
  let n = table.get(key);
  if (!n) {
    n = { id: nextId++, t: null, ...fields };
    table.set(key, n);
  }
  return n;
}

function chars(cs) {
  const s = [...new Set(cs)].sort().join("");
  return node("c" + s, { k: "chr", cs: s });
}

const itemsOf = (p, k) => (p.k === k ? p.items : [p]);

function cat(...parts) {
  const items = [];
  for (const p of parts) {
    if (p == null) return null; // the empty language absorbs concatenation
    for (const x of itemsOf(p, "cat")) {
      if (x === EPS) continue;
      if (items.length) {
        const prev = items[items.length - 1];
        const [pb, pn] = prev.k === "rep" ? [prev.x, prev.n] : [prev, 1];
        const [xb, xn] = x.k === "rep" ? [x.x, x.n] : [x, 1];
        if (pb === xb && pb.k !== "star") {
          items[items.length - 1] = rep(pb, pn + xn);
          continue;
        }
        if (prev === x && x.k === "star") continue; // x*x* = x*
        if (prev.k === "star" && prev.x === x) {
          items[items.length - 1] = plus(x); // x*x = x+
          continue;
        }
        if (x.k === "star" && x.x === prev) {
          items[items.length - 1] = plus(prev); // xx* = x+
          continue;
        }
      }
      items.push(x);
    }
  }
  if (!items.length) return EPS;
  if (items.length === 1) return items[0];
  return node("t" + items.map((x) => x.id).join(","), { k: "cat", items });
}

function rep(x, n) {
  return n === 1 ? x : node("r" + x.id + "," + n, { k: "rep", x, n });
}

function plus(x) {
  if (x === EPS) return EPS;
  if (x.k === "star" || x.k === "plus") return x;
  return node("p" + x.id, { k: "plus", x });
}

function star(x) {
  if (x == null || x === EPS) return EPS;
  if (x.k === "star") return x;
  if (x.k === "plus") return star(x.x);
  if (x.k === "alt" && x.eps) {
    const rest = x.items.filter((y) => y !== EPS);
    return rest.length ? star(alt(...rest)) : EPS;
  }
  return node("s" + x.id, { k: "star", x });
}

function head(x) {
  if (x.k === "cat") return [x.items[0], cat(...x.items.slice(1))];
  if (x.k === "rep") return [x.x, rep(x.x, x.n - 1)];
  return [x, EPS];
}

function last(x) {
  if (x.k === "cat") return [x.items[x.items.length - 1], cat(...x.items.slice(0, -1))];
  if (x.k === "rep") return [x.x, rep(x.x, x.n - 1)];
  return [x, EPS];
}

const first = (set) => set.values().next().value;
const byText = (a, b) => (text(a) < text(b) ? -1 : text(a) > text(b) ? 1 : 0);

function alt(...parts) {
  let items = new Set();
  const cs = new Set();
  for (const p of parts) {
    if (p == null) continue;
    for (const x of itemsOf(p, "alt")) {
      if (x.k === "chr") for (const c of x.cs) cs.add(c);
      else items.add(x);
    }
  }
  if (cs.size) items.add(chars(cs));
  if (!items.size) return null;
  if (items.size === 1) return first(items);
  items = factor(items, head, (h, t) => cat(h, t));
  if (items.size === 1) return first(items);
  items = factor(items, last, (h, t) => cat(t, h));
  if (items.size === 1) return first(items);
  // merge again: factoring can expose single characters
  const cs2 = [...items].filter((x) => x.k === "chr");
  if (cs2.length > 1) {
    for (const x of cs2) items.delete(x);
    items.add(chars(cs2.map((x) => x.cs).join("")));
    if (items.size === 1) return first(items);
  }
  const sorted = [...items].sort(byText);
  return node("a" + sorted.map((x) => x.id).join(","), { k: "alt", items: sorted, eps: sorted.includes(EPS) });
}

function factor(items, split, join) {
  const groups = new Map();
  for (const x of items) {
    const [h, t] = x === EPS ? [null, EPS] : split(x);
    if (!groups.has(h)) groups.set(h, []);
    groups.get(h).push([x, t]);
  }
  const out = new Set();
  for (const [h, members] of groups) {
    if (h === null || members.length === 1) for (const [x] of members) out.add(x);
    else out.add(join(h, alt(...members.map(([, t]) => t))));
  }
  return out;
}

function cls(s) {
  if (s === DIGITS) return "\\d";
  if (s.length === 1) return /[A-Za-z0-9]/.test(s) ? s : "\\" + s;
  const runs = [];
  for (let i = 0; i < s.length; ) {
    let j = i;
    while (j + 1 < s.length && s.charCodeAt(j + 1) === s.charCodeAt(j) + 1) j++;
    if (j - i >= 2) runs.push(s[i] + "-" + s[j]);
    else runs.push(s.slice(i, j + 1));
    i = j + 1;
  }
  return "[" + runs.join("").replaceAll("0-9", "\\d") + "]";
}

// precedence: 0 = inside alternation, 1 = inside concatenation, 2 = operand of a postfix
function pr(n, ctx) {
  switch (n.k) {
    case "eps":
      return ctx < 2 ? "" : "(?:)";
    case "cat":
      return ctx < 2 ? text(n) : "(?:" + text(n) + ")";
    case "alt":
      return ctx === 0 || (n.eps && ctx === 1) ? text(n) : "(?:" + text(n) + ")";
    case "rep":
      return ctx === 2 && !counted(n) ? "(?:" + text(n) + ")" : text(n);
    default:
      return text(n);
  }
}

// a repeat is written out (xx) unless the counter (x{2}) is shorter: V8 gives every counter a loop
// register, and with thousands of them Chromium compiles a pattern up to seven times slower
const counted = (n) => pr(n.x, 1).length * n.n > pr(n.x, 2).length + String(n.n).length + 2;

function text(n) {
  if (n.t !== null) return n.t;
  let s;
  switch (n.k) {
    case "chr":
      s = cls(n.cs);
      break;
    case "cat":
      s = n.items.map((x) => pr(x, 1)).join("");
      break;
    case "alt":
      if (n.eps) {
        const rest = n.items.filter((x) => x !== EPS);
        s = (rest.length === 1 ? pr(rest[0], 2) : "(?:" + rest.map((x) => pr(x, 0)).join("|") + ")") + "?";
      } else s = n.items.map((x) => pr(x, 0)).join("|");
      break;
    case "star":
      s = pr(n.x, 2) + "*";
      break;
    case "plus":
      s = pr(n.x, 2) + "+";
      break;
    case "rep":
      s = counted(n) ? pr(n.x, 2) + "{" + n.n + "}" : pr(n.x, 1).repeat(n.n);
      break;
  }
  if (s.length > budget) throw new TooLong();
  return (n.t = s);
}

const len = (n) => text(n).length;

function reverse(n) {
  if (n == null) return null;
  if (revMemo.has(n)) return revMemo.get(n);
  let r;
  switch (n.k) {
    case "eps":
    case "chr":
      r = n;
      break;
    case "cat":
      r = cat(...[...n.items].reverse().map(reverse));
      break;
    case "alt":
      r = alt(...n.items.map(reverse));
      break;
    case "star":
      r = star(reverse(n.x));
      break;
    case "plus":
      r = plus(reverse(n.x));
      break;
    case "rep":
      r = rep(reverse(n.x), n.n);
      break;
  }
  revMemo.set(n, r);
  return r;
}

// ---------------------------------------------------------------- state elimination (rexsum/elim.py)
// A graph is a Map from "p>q" to the regex on the edge p -> q; states are integers >= 0.
const SRC = -1, SNK = -2;
const ek = (p, q) => p + ">" + q;

class Graph {
  constructor(E) {
    this.E = new Map(E.E ?? E);
    this.out = new Map();
    this.inn = new Map();
    for (const key of this.E.keys()) {
      const [p, q] = key.split(">").map(Number);
      this.link(p, q);
    }
  }
  link(p, q) {
    if (!this.out.has(p)) this.out.set(p, new Set());
    if (!this.inn.has(q)) this.inn.set(q, new Set());
    this.out.get(p).add(q);
    this.inn.get(q).add(p);
  }
  get(p, q) {
    return this.E.get(ek(p, q));
  }
  states() {
    const s = new Set([...this.out.keys(), ...this.inn.keys()]);
    s.delete(SRC);
    s.delete(SNK);
    return s;
  }
  // the length added by removing k, from the lengths of the regexes it combines (an estimate)
  cost(k) {
    const loop = this.get(k, k);
    const ls = loop !== undefined ? len(star(loop)) : 0;
    const ins = [...(this.inn.get(k) ?? [])].filter((p) => p !== k);
    const outs = [...(this.out.get(k) ?? [])].filter((q) => q !== k);
    let added = 0;
    for (const p of ins) {
      const lp = len(this.get(p, k));
      for (const q of outs) added += lp + ls + len(this.get(k, q)) + 4;
    }
    let removed = loop !== undefined ? len(loop) : 0;
    for (const p of ins) removed += len(this.get(p, k));
    for (const q of outs) removed += len(this.get(k, q));
    return added - removed;
  }
  // every path p -> k -> q becomes the edge p -> q : R(p,k) R(k,k)* R(k,q)
  remove(k) {
    const loop = this.get(k, k);
    this.E.delete(ek(k, k));
    const s = loop !== undefined ? star(loop) : EPS;
    const ins = [...(this.inn.get(k) ?? [])].filter((p) => p !== k);
    const outs = [...(this.out.get(k) ?? [])].filter((q) => q !== k);
    for (const p of ins) {
      const rp = this.get(p, k);
      this.E.delete(ek(p, k));
      this.out.get(p).delete(k);
      for (const q of outs) {
        const fresh = cat(rp, s, this.get(k, q));
        const old = this.get(p, q);
        this.E.set(ek(p, q), old !== undefined ? alt(old, fresh) : fresh);
        this.link(p, q);
      }
    }
    for (const q of outs) {
      this.E.delete(ek(k, q));
      this.inn.get(q).delete(k);
    }
    this.out.delete(k);
    this.inn.delete(k);
  }
}

// eliminate every state, the next one always the one of smallest estimated growth
function eliminateByCost(g) {
  g = new Graph(g);
  const states = g.states();
  while (states.size) {
    let best = null, bestCost = 0;
    for (const s of states) {
      const c = g.cost(s);
      if (best === null || c < bestCost || (c === bestCost && String(s) < String(best))) [best, bestCost] = [s, c];
    }
    g.remove(best);
    states.delete(best);
  }
  return g.get(SRC, SNK) ?? null;
}

// ---------------------------------------------------------------- automata (rexsum/automata.py)
// explore a step function from `start` (states are arrays of numbers), then minimize
function explore(start, step, accept, alphabet) {
  const index = new Map([[String(start), 0]]);
  const order = [start];
  const delta = [];
  for (let i = 0; i < order.length; i++) {
    const row = new Map();
    for (const c of alphabet) {
      const r = step(order[i], c);
      if (r === null) continue;
      const key = String(r);
      if (!index.has(key)) {
        index.set(key, order.length);
        order.push(r);
      }
      row.set(c, index.get(key));
    }
    delta.push(row);
  }
  const finals = new Set(order.map((q, i) => (accept(q) ? i : -1)).filter((i) => i >= 0));
  return minimize({ n: order.length, start: 0, finals, delta, alphabet });
}

// Moore's partition refinement, after dropping states that cannot reach a final state
function minimize(d) {
  const rev = Array.from({ length: d.n }, () => new Set());
  d.delta.forEach((row, q) => row.forEach((r) => rev[r].add(q)));
  const live = new Set(d.finals);
  const todo = [...d.finals];
  while (todo.length) {
    const q = todo.shift();
    for (const p of rev[q]) if (!live.has(p)) (live.add(p), todo.push(p));
  }
  if (!live.has(d.start)) return { n: 1, start: 0, finals: new Set(), delta: [new Map()], alphabet: d.alphabet };
  const sortedLive = [...live].sort((a, b) => a - b);
  let cl = new Map(sortedLive.map((q) => [q, d.finals.has(q) ? 1 : 0]));
  for (;;) {
    const ids = new Map();
    const next = new Map();
    for (const q of sortedLive) {
      const row = d.delta[q];
      const sig = [cl.get(q), ...[...d.alphabet].map((c) => (live.has(row.get(c)) ? cl.get(row.get(c)) : "n"))].join(",");
      if (!ids.has(sig)) ids.set(sig, ids.size);
      next.set(q, ids.get(sig));
    }
    const before = new Set(cl.values()).size;
    cl = next;
    if (ids.size === before) break;
  }
  // renumber from the start state in BFS order, for stable output
  const index = new Map([[cl.get(d.start), 0]]);
  const queue = [cl.get(d.start)];
  const repr = new Map();
  for (const q of sortedLive) if (!repr.has(cl.get(q))) repr.set(cl.get(q), q);
  const delta = [];
  while (queue.length) {
    const c = queue.shift();
    const q = repr.get(c);
    const row = new Map();
    for (const a of d.alphabet) {
      const r = d.delta[q].get(a);
      if (r === undefined || !live.has(r)) continue;
      const cr = cl.get(r);
      if (!index.has(cr)) (index.set(cr, index.size), queue.push(cr));
      row.set(a, index.get(cr));
    }
    delta.push(row);
  }
  const finals = new Set(sortedLive.filter((q) => d.finals.has(q)).map((q) => index.get(cl.get(q))));
  return { n: index.size, start: 0, finals, delta, alphabet: d.alphabet };
}

function graphOf(d) {
  const E = new Map();
  d.delta.forEach((row, q) => {
    const by = new Map();
    for (const [c, r] of row) {
      if (!by.has(r)) by.set(r, []);
      by.get(r).push(c);
    }
    for (const [r, cs] of by) E.set(ek(q, r), chars(cs));
  });
  E.set(ek(SRC, d.start), EPS);
  for (const f of d.finals) E.set(ek(f, SNK), EPS);
  return E;
}

// ---------------------------------------------------------------- the constructions (rexsum/pipeline.py)
function primePowers(m) {
  const out = [];
  for (let p = 2; m > 1; p++) {
    if (m % p) continue;
    let q = 1;
    while (m % p === 0) (m /= p, (q *= p));
    out.push(q);
  }
  return out;
}

function* permutations(xs) {
  if (xs.length <= 1) {
    yield xs;
    return;
  }
  for (let i = 0; i < xs.length; i++)
    for (const rest of permutations([...xs.slice(0, i), ...xs.slice(i + 1)])) yield [xs[i], ...rest];
}

// cyclic weights: states (sum mod q, j) with j = position mod k are numbered s * k + j
function cyclicGraph(maps, q, alphabet, parity) {
  const k = maps.length;
  const E = new Map();
  for (let s = 0; s < q; s++)
    for (let j = 0; j < k; j++) {
      const by = new Map();
      for (const c of alphabet) {
        if (!(c in maps[j])) continue;
        const t = mod(s + maps[j][c], q) * k + ((j + 1) % k);
        if (!by.has(t)) by.set(t, []);
        by.get(t).push(c);
      }
      for (const [t, cs] of by) E.set(ek(s * k + j, t), chars(cs));
    }
  E.set(ek(SRC, 0), EPS);
  for (let j = 0; j < k; j++) if (parity === null || j === parity) E.set(ek(j, SNK), EPS);
  return E;
}

// the positions inside one period first, then the q remaining states in the best of all orders
function structured(E, k, exhaustive = 6) {
  const g = new Graph(E);
  const states = [...g.states()].sort((a, b) => a - b);
  for (const st of states) if (st % k !== 0) g.remove(st);
  for (const x of g.E.values()) len(x);
  const rest = states.filter((st) => st % k === 0);
  let best = null;
  for (const order of rest.length <= exhaustive ? permutations(rest) : [rest]) {
    const r = attempt(() => {
      const g2 = new Graph(g);
      for (const st of order) g2.remove(st);
      const r = g2.get(SRC, SNK);
      return r === undefined ? null : (len(r), r);
    });
    if (r !== null && (best === null || len(r) < len(best))) best = r;
  }
  return best;
}

function cyclicComponent(maps, q, alphabet, backwards, parity) {
  const cands = [attempt(() => structured(cyclicGraph(maps, q, alphabet, parity), maps.length))];
  // a tiny component may minimize to fewer states (GTIN mod 2 is just "digit sum even")
  const k = maps.length;
  const d = explore([0, 0], ([s, j], c) => (c in maps[j] ? [mod(s + maps[j][c], q), (j + 1) % k] : null),
                    ([s, j]) => s === 0 && (parity === null || j === parity), alphabet);
  if (d.n <= 8) cands.push(attempt(() => eliminateByCost(graphOf(d))));
  let r = null;
  for (const c of cands) if (c !== null && (r === null || len(c) < len(r))) r = c;
  return r === null ? null : backwards ? attempt(() => (len(reverse(r)), reverse(r))) : r;
}

// fixed length n: R[a, b][d] = strings of positions a..b-1 whose sum is d mod q, an interval split
// at the position that makes its regexes shortest
function layeredDp(n, q, alphabet, contrib) {
  const memo = new Map();
  function base(i) {
    const by = new Map();
    for (const c of alphabet) {
      const d = contrib(i, c);
      if (d === null) continue;
      if (!by.has(d)) by.set(d, []);
      by.get(d).push(c);
    }
    return new Map([...by].map(([d, cs]) => [d, chars(cs)]));
  }
  function R(a, b) {
    const key = a * (n + 1) + b;
    if (memo.has(key)) return memo.get(key);
    let res;
    if (b - a === 1) res = base(a);
    else {
      let bestLen = null;
      for (let m = a + 1; m < b; m++) {
        const L = R(a, m), Rr = R(m, b);
        if (L === null || Rr === null) continue;
        const split = attempt(() => {
          const resM = new Map();
          for (let d = 0; d < q; d++) {
            const parts = [];
            for (const [u, x] of L) if (Rr.has(mod(d - u, q))) parts.push(cat(x, Rr.get(mod(d - u, q))));
            if (parts.length) resM.set(d, alt(...parts));
          }
          let tot = 0;
          for (const x of resM.values()) tot += len(x);
          return [resM, tot];
        });
        if (split !== null && (bestLen === null || split[1] < bestLen)) [res, bestLen] = split;
      }
      res ??= null;
    }
    memo.set(key, res);
    return res;
  }
  // the top level needs only d = 0: pick its split separately
  let best = null;
  for (let m = 1; m < n; m++) {
    const L = R(0, m), Rr = R(m, n);
    if (L === null || Rr === null) continue;
    const r = attempt(() => {
      const parts = [];
      for (const [u, x] of L) if (Rr.has(mod(-u, q))) parts.push(cat(x, Rr.get(mod(-u, q))));
      const r = alt(...parts);
      return r === null ? null : (len(r), r);
    });
    if (r !== null && (best === null || len(r) < len(best))) best = r;
  }
  return best;
}

/**
 * The pattern for: the sum of weight × digit over the input is 0 mod `mod`, the weights repeating
 * from the rightmost digit (from: "right", the default) or the leftmost, for any number of digits
 * or exactly `length`. Returns { pattern, length, components } as `rexsum custom` computes them.
 * With `budget`, regexes longer than that many characters are given up, and if no construction
 * fits, compileCustom throws: the patterns that do come out are the same.
 */
export function compileCustom({ weights, mod: m = 10, from = "right", length = null, budget: limit = Infinity }) {
  if (!Array.isArray(weights) || !weights.length || !weights.every(Number.isInteger)) throw new Error("weights: a list of integers");
  if (!Number.isInteger(m) || m < 2) throw new Error("mod: an integer of at least 2");
  if (length !== null && !(Number.isInteger(length) && length >= 2)) throw new Error("length: an integer of at least 2, or null");
  reset();
  budget = limit;
  try {
    return compile(weights, m, from, length);
  } finally {
    reset();
    budget = Infinity;
  }
}

function compile(weights, m, from, length) {
  const maps = weights.map((w) => Object.fromEntries([...DIGITS].map((c) => [c, w * Number(c)])));
  const k = maps.length;
  const backwards = from === "right";
  const parity = length ? length % k : null;
  const fmt = length ? `\\d{${length}}` : "\\d+";
  const parts = [];
  for (const q of primePowers(m)) {
    const mq = maps.map((mp) => Object.fromEntries(Object.entries(mp).map(([c, v]) => [c, mod(v, q)])));
    const cands = [["cyclic", cyclicComponent(mq, q, DIGITS, backwards, parity)]];
    if (parity !== null) cands.push(["cyclic, any length", cyclicComponent(mq, q, DIGITS, backwards, null)]);
    if (length) {
      const f = (i, c) => mod(maps[(backwards ? length - 1 - i : i) % k][c], q);
      cands.push(["intervals", attempt(() => layeredDp(length, q, DIGITS, f))]);
    }
    let how = null, r = null;
    for (const [h, x] of cands) if (x !== null && (r === null || len(x) < len(r))) [how, r] = [h, x];
    if (r === null) throw new RangeError(`over ${budget.toLocaleString("en")} characters for the sum mod ${q}`);
    parts.push({ q, text: text(r), construction: how, tried: Object.fromEntries(cands.map(([h, x]) => [h, x === null ? null : len(x)])) });
  }
  parts.sort((a, b) => a.text.length - b.text.length);
  const look = parts.slice(0, -1).map((p) => `(?=(?:${p.text})$)`).join("");
  const pattern = `(?=${fmt}$)${look}(?:${parts[parts.length - 1].text})`;
  return {
    pattern,
    length: pattern.length,
    components: Object.fromEntries(parts.map((p) => [p.q, { length: p.text.length, construction: p.construction, tried: p.tried }])),
  };
}

const escapeHtml = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#x27;" })[c]);

/** An <input> element for a pattern, as `rexsum … --html` prints it; `attrs` go before the pattern. */
export function inputElement(pattern, attrs = 'inputmode="numeric"') {
  return `<input ${attrs} pattern="${escapeHtml(pattern)}">`;
}
