const fs = require("fs"), path = require("path"), vm = require("vm");

const file = path.join(__dirname, "..", "declension-quiz.html");
const html = fs.readFileSync(file, "utf8");
const scriptMatch = html.match(/<script>([\s\S]*)<\/script>/);
if (!scriptMatch) { console.error("FAIL: no <script> block in " + file); process.exit(1); }
const js = scriptMatch[1];
const errs = [], info = [];

try { new vm.Script(js, {filename: "declension-quiz.js"}); info.push("JS syntax OK"); }
catch (e) { errs.push("JS syntax error: " + e.message); }

const markup = html.slice(0, html.indexOf("<script>"));
const htmlIds = new Set([...markup.matchAll(/id="([^"]+)"/g)].map(x => x[1]));
const dynamicIds = new Set(["againBtn", "errBtn", "repBtn"]);
const missingIds = [...new Set([...js.matchAll(/\$\("([^"]+)"\)/g)].map(x => x[1]))].filter(id => !htmlIds.has(id) && !dynamicIds.has(id));
if (missingIds.length) errs.push("element ids used in JS but missing in HTML: " + missingIds.join(", "));

const a = js.indexOf("/*DATA-START*/"), b = js.indexOf("/*DATA-END*/");
if (a < 0 || b < 0) { console.error("FAIL: DATA-START / DATA-END markers missing"); process.exit(1); }
const D = vm.runInNewContext(js.slice(a, b) +
  "\n;({ITEMS, TABLES, CTX_POOL, TRAP_LABELS, isCorrect, classifyErr, cellValue, colIndex, itemTraps, answers, stemOf, trapOf})", {});
const {ITEMS, TABLES, CTX_POOL, TRAP_LABELS, isCorrect, classifyErr, cellValue, colIndex, itemTraps, answers, stemOf} = D;

const END = {m:{Nom:"e0", Akk:"en", Dat:"em", Gen:"es"}, f:{Nom:"e", Akk:"e", Dat:"er", Gen:"er"},
  n:{Nom:"e0", Akk:"e0", Dat:"em", Gen:"es"}, Pl:{Nom:"e", Akk:"e", Dat:"en", Gen:"er"}};
const SUF = {e0:"", e:"e", en:"en", em:"em", er:"er", es:"es"};

const ids = new Set();
for (const it of ITEMS){
  if (ids.has(it.id)) errs.push("duplicate id " + it.id);
  ids.add(it.id);
  for (const c of it.cells){
    if (!TABLES[c.t]) { errs.push(it.id + ": unknown table " + c.t); continue; }
    if (!TABLES[c.t].data[c.r]) errs.push(it.id + ": unknown row " + c.r);
    if (colIndex(c.t, c.c) < 0) errs.push(it.id + ": unknown col " + c.c);
  }
  const ans = answers(it)[0], c0 = it.cells[0], t2 = it.cells.find(c => c.t === "T2");
  if (t2 && cellValue(t2) !== ans) errs.push(it.id + ": T2 cell is " + cellValue(t2) + " but answer is " + ans);
  if (c0.t === "T1e" && t2 && END[c0.r][c0.c] !== t2.c) errs.push(it.id + ": " + c0.r + " " + c0.c + " needs ending -" + END[c0.r][c0.c] + " but T2 col is " + t2.c);
  if (c0.t === "T1e" && !t2){
    const stem = /\[kein\]/.test(it.q) ? "kein" : "ein";
    const want = stem + cellValue(c0).slice(4);
    if (want !== ans) errs.push(it.id + ": expected " + want + " but answer is " + ans);
  }
  if (["T1d", "T3", "T4"].includes(c0.t) && it.cells.length === 1){
    const v = cellValue(c0);
    const same = TABLES[c0.t].caps ? v === ans : v.toLowerCase() === ans.toLowerCase();
    if (!same) errs.push(it.id + ": table says " + v + " but answer is " + ans);
  }
  for (const tr of itemTraps(it)) if (!TRAP_LABELS[tr]) errs.push(it.id + ": no label for rule " + tr);
}

const seenCtx = new Set();
for (const [end, list] of Object.entries(CTX_POOL)) for (const [g, k] of list){
  const v = cellValue({t:"T1e", r:g, c:k});
  if (v !== "mein" + SUF[end]) errs.push("CTX_POOL: " + g + " " + k + " is " + v + " but pool says -" + end);
  if (seenCtx.has(g + k)) errs.push("CTX_POOL: duplicate context " + g + " " + k);
  seenCtx.add(g + k);
}
if (seenCtx.size !== 16) errs.push("CTX_POOL covers " + seenCtx.size + "/16 gender-case contexts");

const byId = id => ITEMS.find(x => x.id === id);
const capsCases = [["x-tothem", "ihnen", true], ["x-tothem", "Ihnen", false], ["x-toyou", "Ihnen", true], ["x-toyou", "ihnen", false],
  ["p-ihr-pl-nom", "Ihre", true], ["p-ihr-pl-akk", "Ihre", false], ["p-Ihr-n-gen", "ihres", false], ["d-m-nom", "Der", true]];
for (const [id, v, want] of capsCases){
  const it = byId(id);
  if (!it) { errs.push("caps test: missing item " + id); continue; }
  if (isCorrect(it, v) !== want) errs.push("isCorrect(" + id + ", '" + v + "') should be " + want);
}
const classCases = [["ihrem", "ihnem", ["datMN"], "ihr", "stem"], ["Ihr", "Ihren", ["bare"], "Ihr", "bare"],
  ["eurem", "euerem", ["datMN"], "eu", "euer"], ["ihnen", "Ihnen", ["pron"], null, "caps"], ["meinen", "meine", ["datPl"], "mein", "datPl"]];
for (const [exp, given, traps, stem, want] of classCases){
  const got = classifyErr(exp, given, traps, stem);
  if (got !== want) errs.push("classifyErr(" + exp + ", " + given + ") = " + got + ", expected " + want);
}

const t2All = []; Object.keys(TABLES.T2.data).forEach(r => TABLES.T2.cols.forEach(([c]) => t2All.push(r + ":" + c)));
const t2Cov = new Set(ITEMS.flatMap(it => it.cells.filter(c => c.t === "T2").map(c => c.r + ":" + c.c)));
const t2Missing = t2All.filter(k => !t2Cov.has(k));
if (t2Missing.length) errs.push("T2 cells without a quiz item: " + t2Missing.join(", "));
const cov = t => new Set(ITEMS.flatMap(it => it.cells.filter(c => c.t === t).map(c => c.r + ":" + c.c))).size;

const perCat = ITEMS.reduce((m, it) => (m[it.cat] = (m[it.cat] || 0) + 1, m), {});
info.push("items: " + ITEMS.length + " " + JSON.stringify(perCat));
info.push("coverage: T1 der " + cov("T1d") + "/16 · T2 " + (t2All.length - t2Missing.length) + "/" + t2All.length + " · T4 " + cov("T4") + "/16");
console.log(info.join("\n"));
if (errs.length){ console.log("FAIL (" + errs.length + "):\n- " + errs.join("\n- ")); process.exit(1); }
console.log("ALL CHECKS PASSED");
