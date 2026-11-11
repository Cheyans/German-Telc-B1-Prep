const fs = require("fs"), path = require("path"), vm = require("vm");

const file = process.argv[2] || path.join(__dirname, "..", "verb-prep-trainer.html");
const html = fs.readFileSync(file, "utf8");
const m = html.match(/<script>([\s\S]*)<\/script>/);
if (!m) { console.error("FAIL: no <script> block in " + file); process.exit(1); }
const js = m[1];
const errs = [], info = [];

try { new vm.Script(js, {filename: "verb-prep-trainer.js"}); info.push("JS syntax OK"); }
catch (e) { errs.push("JS syntax error: " + e.message); }

const markup = html.slice(0, html.indexOf("<script>"));
const htmlIds = new Set([...markup.matchAll(/id="([^"]+)"/g)].map(x => x[1]));
const dynamicIds = new Set(["againBtn", "errBtn", "repBtn", "cAgain", "cToSaetze"]);
const missingIds = [...new Set([...js.matchAll(/\$\("([^"]+)"\)/g)].map(x => x[1]))].filter(id => !htmlIds.has(id) && !dynamicIds.has(id));
if (missingIds.length) errs.push("element ids used in JS but missing in HTML: " + missingIds.join(", "));

const a = js.indexOf("/*DATA-START*/"), b = js.indexOf("/*DATA-END*/");
if (a < 0 || b < 0) { console.error("FAIL: DATA-START / DATA-END markers missing"); process.exit(1); }
const D = vm.runInNewContext(js.slice(a, b) + "\n;({CARDS, ITEMS, CARD_BY_ID, checkBlank, classify, caseHint, artForm, CONTR, PRON, parseHint, hintParts, blankStarts, strictCaps, ERR_LABELS, OBJ_SHORT, daForm, woForm})", {});
const {CARDS, ITEMS, CARD_BY_ID, checkBlank, classify, caseHint, artForm, CONTR, PRON, parseHint, hintParts, blankStarts, strictCaps, ERR_LABELS, OBJ_SHORT} = D;

const EMDASH = /—/;
const cardIds = new Set();
for (const c of CARDS){
  if (cardIds.has(c.id)) errs.push("duplicate card id " + c.id);
  cardIds.add(c.id);
  if (c.grp === "P"){ if (!c.preps.length || c.preps.some(x => !["A", "D"].includes(x.k))) errs.push(c.id + ": bad preps"); }
  else if (c.grp === "K"){ if (!OBJ_SHORT[c.obj]) errs.push(c.id + ": bad obj " + c.obj); }
  else errs.push(c.id + ": bad group " + c.grp);
  if (!c.en || !c.ex.length || c.ex.some(x => x.length !== 2 || !x[0] || !x[1])) errs.push(c.id + ": missing meaning or example");
  for (const t of [c.verb, c.en, c.note, c.forms, ...c.ex.flat()]) if (EMDASH.test(t)) errs.push(c.id + ": em dash in card text");
}

const ACC = new Set(["mich", "dich", "ihn", "sie", "es", "uns", "euch", "Sie"]);
const DAT = new Set(["mir", "dir", "ihm", "ihr", "uns", "euch", "ihnen", "Ihnen"]);
const VOWEL = /^[aeiouäöü]/;
const ids = new Set(), qs = new Set(), typCount = {}, used = {};
for (const it of ITEMS){
  const c = CARD_BY_ID[it.card];
  if (ids.has(it.id)) errs.push("duplicate item id " + it.id);
  ids.add(it.id);
  if (qs.has(it.q)) errs.push(it.id + ": duplicate sentence");
  qs.add(it.q);
  typCount[it.typ] = (typCount[it.typ] || 0) + 1;
  if (!c){ errs.push(it.id + ": unknown card " + it.card); continue; }
  used[c.id] = (used[c.id] || 0) + 1;
  const nb = it.q.split("___").length - 1;
  if (nb !== it.a.length) errs.push(it.id + ": " + nb + " blanks but " + it.a.length + " answers");
  if (!it.en) errs.push(it.id + ": missing English");
  for (const t of [it.q, it.en, it.hint, it.note, ...it.a.flat()]) if (EMDASH.test(t)) errs.push(it.id + ": em dash");
  if ((it.typ === "KA") !== (c.grp === "K")) errs.push(it.id + ": typ " + it.typ + " does not fit card group " + c.grp);
  const preps = c.preps ? c.preps.map(x => x.p) : [];
  const caseOf = p => (c.preps.find(x => x.p === p) || {}).k;
  if (it.typ === "P"){
    it.a.forEach((alts, i) => alts.forEach(x => { if (!preps.includes(x)) errs.push(it.id + ": blank " + (i + 1) + " answer " + x + " is not a preposition of " + c.id); }));
    if (it.a.length > 1 && new Set(it.a.map(x => x[0])).size !== it.a.length) errs.push(it.id + ": same preposition twice");
  }
  if (it.typ === "PA"){
    const h = parseHint(it.hint);
    if (!h || h.pron) { errs.push(it.id + ": bad hint " + it.hint); continue; }
    const p = it.a[0][0].split(" ")[0];
    const full = Object.keys(CONTR).find(k => CONTR[k] === p);
    const prep = full ? full.split(" ")[0] : p;
    if (!preps.includes(prep)) { errs.push(it.id + ": preposition " + prep + " not in card " + c.id); continue; }
    const art = artForm(caseOf(prep), h.g, h.stem);
    const want = new Set([prep + " " + art]); if (CONTR[prep + " " + art]) want.add(CONTR[prep + " " + art]);
    const got = new Set(it.a[0]);
    if (want.size !== got.size || [...want].some(x => !got.has(x))) errs.push(it.id + ": expected " + [...want].join("|") + " but answer is " + it.a[0].join("|"));
  }
  if (it.typ === "DA"){
    if (it.hint) errs.push(it.id + ": DA items must not have a hint");
    const x = it.a[0][0], starts = blankStarts(it.q)[0];
    const comp = x.match(/^(da|wo)(r?)([a-zäöüß]+)$/i);
    if (comp){
      const p = comp[3].toLowerCase(), wo = comp[1].toLowerCase() === "wo";
      if (!preps.includes(p)) errs.push(it.id + ": " + x + " uses " + p + ", card has " + preps.join("/"));
      if ((comp[2] === "r") !== VOWEL.test(p)) errs.push(it.id + ": r rule broken in " + x);
      if (wo && !starts) errs.push(it.id + ": wo-word not at the start of a question");
      if (wo !== /^W/.test(x)) errs.push(it.id + ": capitalisation of " + x);
    } else {
      const w = x.split(" ");
      const p = w[0].toLowerCase(), k = caseOf(p);
      if (w.length !== 2 || !k) errs.push(it.id + ": bad pronoun answer " + x);
      else if (w[1] === "wen" || w[1] === "wem"){ if ((w[1] === "wen") !== (k === "A")) errs.push(it.id + ": " + x + " has the wrong case"); if (!starts) errs.push(it.id + ": question word not at the start"); }
      else if (!(k === "A" ? ACC : DAT).has(w[1])) errs.push(it.id + ": pronoun " + w[1] + " is not " + (k === "A" ? "Akkusativ" : "Dativ"));
    }
  }
  if (it.typ === "KA"){
    const hp = hintParts(it);
    if (hp.length !== nb || it.cases.length !== nb) errs.push(it.id + ": hints/cases do not match blanks");
    const objCases = c.obj.replace("rD", "D").split(" ");
    it.cases.forEach((k, i) => {
      if (!objCases.includes(k.replace("rD", "D"))) errs.push(it.id + ": case " + k + " does not fit " + c.id + " (" + c.obj + ")");
      const h = parseHint(hp[i] || "");
      if (!h) { errs.push(it.id + ": bad hint " + hp[i]); return; }
      const want = h.pron ? PRON[k][h.pron] : artForm(k, h.g, h.stem);
      if (it.a[i].length !== 1 || it.a[i][0] !== want) errs.push(it.id + ": blank " + (i + 1) + " expected " + want + " but answer is " + it.a[i].join("|"));
    });
  }
}
const wantCounts = {P: 70, PA: 40, DA: 50, KA: 40};
for (const [t, n] of Object.entries(wantCounts)) if (typCount[t] !== n) errs.push("typ " + t + ": " + (typCount[t] || 0) + " items, expected " + n);
if (ITEMS.length !== 200) errs.push(ITEMS.length + " items, expected 200");
const unused = CARDS.filter(c => !used[c.id]).map(c => c.id);
if (unused.length) errs.push("cards without a sentence: " + unused.join(", "));

const byId = id => ITEMS.find(x => x.id === id);
const checks = [["c13", 0, "mit Ihnen", true], ["c13", 0, "mit ihnen", false], ["c46", 0, "mit ihnen", true], ["c46", 0, "mit Ihnen", false],
  ["b09", 0, "für ihre", false], ["b09", 0, "fuer Ihre", true], ["a01", 0, "Auf", true], ["a10", 0, "fuer", true],
  ["b35", 0, "von dem", true], ["b35", 0, "vom", true], ["c02", 0, "worauf", true], ["b06", 0, "mit Ihren", false], ["b06", 0, "mit ihren", true]];
for (const [id, bl, v, want] of checks){ const it = byId(id); if (!it) { errs.push("test: missing " + id); continue; }
  if (checkBlank(it, bl, v).ok !== want) errs.push("checkBlank(" + id + ", '" + v + "') should be " + want); }
const cls = [["a01", "an", "prep"], ["b12", "mit den", "kasus"], ["b09", "für ihnen", "stamm"], ["c18", "auf es", "sache"], ["c23", "darauf", "person"],
  ["c01", "daauf", "r"], ["c12", "Mit wen", "pron"], ["c02", "Was", "wfrage"], ["d03", "deine", "kasusD"], ["d06", "einen", "kasusN"],
  ["d28", "dich", "kasusD"], ["d40", "dich", "kasusD"], ["d02", "dem", "kasusA"], ["c13", "mit ihnen", "caps"], ["b37", "an den", "kasus"], ["c02", "Darauf", "dawo"]];
for (const [id, g, want] of cls){ const it = byId(id); const got = classify(it, 0, g); if (got !== want) errs.push("classify(" + id + ", '" + g + "') = " + got + ", expected " + want); if (!ERR_LABELS[got]) errs.push("no label for " + got); }
if (!caseHint(byId("a01"), 0, "mit")) errs.push("caseHint(a01, mit) should warn");
if (caseHint(byId("a01"), 0, "an")) errs.push("caseHint(a01, an) should be empty");

info.push(`${CARDS.length} cards, ${ITEMS.length} items: ` + Object.entries(typCount).map(([k, v]) => k + " " + v).join(", "));
info.forEach(x => console.log("ok  " + x));
if (errs.length){ errs.forEach(x => console.log("ERR " + x)); console.log(`\n${errs.length} problem(s)`); process.exit(1); }
console.log("\nALL CHECKS PASSED");
