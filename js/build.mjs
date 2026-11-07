// Writes index.js and index.d.ts from ../patterns.json, and copies the license: run by npm pack and
// npm publish (prepack), so the patterns in the package are the repo's.
import fs from "fs";
const here = new URL(".", import.meta.url);
const lib = JSON.parse(fs.readFileSync(new URL("../patterns.json", here), "utf8"));
const names = Object.keys(lib);
const fmt = (n) => n.toLocaleString("en");
const js = [
  "// Generated from rexsum's patterns.json (js/build.mjs). Each export is a pattern for the HTML pattern",
  "// attribute; in a script, test with new RegExp(`^(?:${pattern})$`, \"v\").",
  ...names.map((n) => `export const ${n} = ${JSON.stringify(lib[n].pattern)};`),
  `export const schemes = ${JSON.stringify(Object.fromEntries(names.map((n) => [n, { title: lib[n].title, length: lib[n].length }])))};`,
  `export default { ${names.join(", ")} };`,
  "",
].join("\n");
const dts = [
  "// Generated from rexsum's patterns.json (js/build.mjs).",
  ...names.map((n) => `/** ${lib[n].title}: ${fmt(lib[n].length)} characters. */\nexport declare const ${n}: string;`),
  `/** Each scheme's title and pattern length. */\nexport declare const schemes: { readonly [name in ${names.map((n) => JSON.stringify(n)).join(" | ")}]: { readonly title: string; readonly length: number } };`,
  `declare const patterns: { readonly ${names.map((n) => `${n}: string`).join("; ")} };`,
  "export default patterns;",
  "",
].join("\n");
fs.writeFileSync(new URL("index.js", here), js);
fs.writeFileSync(new URL("index.d.ts", here), dts);
fs.copyFileSync(new URL("../LICENSE", here), new URL("LICENSE", here));
console.log(`js/index.js: ${names.length} patterns, ${fmt(js.length)} bytes`);
