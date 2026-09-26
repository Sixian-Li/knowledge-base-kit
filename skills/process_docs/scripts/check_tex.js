#!/usr/bin/env node
// Validate TeX spans against the pinned KaTeX engine, independently of viewers.
// stdin:  JSON array of {tex, display} objects (a bare string means inline)
// stdout: JSON array of {tex, display, error} for the ones that do not render
// See vendor/README.md for why this is KaTeX rather than pandoc's texmath.
const path = require("path");
const katex = require(path.join(__dirname, "..", "vendor", "katex.min.js"));

let raw = "";
process.stdin.on("data", (c) => (raw += c));
process.stdin.on("end", () => {
  let spans;
  try {
    spans = JSON.parse(raw);
  } catch (e) {
    console.error("check_tex.js: bad stdin JSON: " + e.message);
    process.exit(2);
  }
  const bad = [];
  for (const span of spans) {
    const tex = typeof span === "string" ? span : span.tex;
    const display = typeof span === "string" ? false : Boolean(span.display);
    try {
      katex.renderToString(tex, { throwOnError: true, strict: false, displayMode: display });
    } catch (e) {
      bad.push({ tex, display, error: String(e.message || e).slice(0, 200) });
    }
  }
  process.stdout.write(JSON.stringify(bad));
});
