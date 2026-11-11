async page => {
  const FILE = globalThis.B1_FILE;
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const D = await page.evaluate(() => JSON.parse(document.getElementById("data").textContent));
  const sets = Object.keys(D.pr).sort();
  ok("data has Prüfung sets", sets.length > 0, sets.join(","));
  if (!sets.length) return out.join("\n");
  await page.click("#bToc");
  const tags = await page.$$eval(".toc .pchip", e => e.length);
  ok("contents tags every set that has a Prüfung version", tags === sets.length, tags + " tags");
  const open = async n => { await page.click("#bToc"); await page.click('.toc li[data-n="' + n + '"]'); };
  const n0 = sets[0];
  await open(n0);
  const sw = await page.evaluate(() => ({ p: !!document.querySelector('.vsw [data-ver="p"].on'), l: !!document.querySelector('.vsw [data-ver="l"]'), parts: [...document.querySelectorAll(".part .plabel")].map(x => x.textContent) }));
  ok("switch exists and Prüfung is the default", sw.p && sw.l, JSON.stringify(sw));
  ok("both parts render with labels", sw.parts.length === 2 && /^Teil A/.test(sw.parts[0]) && /^Teil B/.test(sw.parts[1]), sw.parts.join(" / "));
  const tap = async sel => {
    await page.keyboard.press("Escape");
    const el = page.locator(sel).first();
    await el.scrollIntoViewIfNeeded();
    const b = await el.boundingBox();
    await page.mouse.click(b.x + Math.min(8, b.width / 2), b.y + b.height / 2);
    await page.waitForTimeout(150);
    return page.evaluate(() => { const c = document.getElementById("card"); return { vis: getComputedStyle(c).display === "block", text: c.innerText.replace(/\s+/g, " ").slice(0, 200) }; });
  };
  let r = await tap("article.pr .w");
  ok("tap a bold word in the Prüfung text: card opens with a meaning", r.vis && /B1|extra|AT/.test(r.text), r.text);
  const exSet = sets.find(n => D.pr[n].blocks.some(b => b.s.some(sg => Array.isArray(sg) && /^X/.test(sg[1]))));
  if (exSet) {
    await open(exSet);
    r = await tap('article.pr .w[data-id^="X"]');
    ok("tap an extra word: card says it isn't on the B1 list", r.vis && /extra/.test(r.text) && /Nicht auf der B1-Liste/.test(r.text), r.text);
  } else ok("found a set with an extra word", false);
  const atSet = sets.find(n => D.pr[n].blocks.some(b => b.s.some(sg => Array.isArray(sg) && /^R/.test(sg[1]))));
  if (atSet) {
    await open(atSet);
    r = await tap('article.pr .w[data-id^="R"]');
    ok("tap an Austrian word: card gives the word used in Germany", r.vis && /Österreich\. In Deutschland: \S/.test(r.text), r.text);
  }
  const goSet = sets.find(n => Object.keys(D.pr[n].go || {}).length);
  if (goSet) {
    const [gid, gtext] = Object.entries(D.pr[goSet].go)[0];
    await open(goSet);
    const sel = 'article.pr .w[data-id="' + gid + '"]';
    if (await page.$(sel)) { r = await tap(sel); ok("a set's gloss override shows in the card", r.text.includes(gtext), gid + " " + r.text); }
  }
  const qsets = Object.keys(D.pq).sort();
  ok("verified Prüfung quizzes exist", qsets.length > 0, qsets.join(","));
  const kinds = {};
  qsets.slice(1).forEach(n => { const b = D.pq[n][1]; const k = b.t === "rf" ? "rf" : b.kind; if (!kinds[k]) kinds[k] = n; });
  const pickB = async (P, k, val) => {
    if (P.t === "rf") await page.click('#pqB .qq[data-k="' + k + '"] .opt[data-rf="' + (val ? "1" : "0") + '"]');
    else await page.click('#pqB .qq[data-k="' + k + '"] .opt[data-l="' + val + '"]');
  };
  const wrongB = (P, k) => P.t === "rf" ? !P.items[k].a : P.lets.find(l => l !== P.items[k].a);
  if (qsets.length) {
    const n = qsets[0], A = D.pq[n][0].items, B = D.pq[n][1];
    await open(n);
    const wrong0 = [0, 1, 2].find(j => j !== A[0].a);
    await page.click('#pqA .qq[data-k="0"] .opt[data-j="' + wrong0 + '"]');
    const early = await page.evaluate(() => ({ fb: document.querySelector('#pqA .qq[data-k="0"] .fb').innerText, marks: document.querySelectorAll(".opt.yes, .opt.no").length, disabled: document.getElementById("pcheck").disabled, left: document.querySelector(".checkbar .left").textContent }));
    ok("Prüfung: picking shows no right or wrong yet", early.fb === "" && early.marks === 0, JSON.stringify(early));
    ok("Prüfung: one check button for Teil A and B, off until all 10 are answered", early.disabled && /Noch 9 Fragen offen/.test(early.left), early.left);
    await page.click('#pqA .qq[data-k="0"] .opt[data-j="' + A[0].a + '"]');
    for (let k = 1; k < 4; k++) await page.click('#pqA .qq[data-k="' + k + '"] .opt[data-j="' + A[k].a + '"]');
    await page.click('#pqA .qq[data-k="4"] .opt[data-j="' + [0, 1, 2].find(j => j !== A[4].a) + '"]');
    ok("Prüfung: still off after Teil A only", await page.evaluate(() => document.getElementById("pcheck").disabled));
    for (let k = 0; k < 4; k++) await pickB(B, k, B.items[k].a);
    await pickB(B, 4, wrongB(B, 4));
    await page.click("#pcheck");
    const sc = await page.evaluate(() => ({ A: document.getElementById("pqA-score").textContent, B: document.getElementById("pqB-score").textContent, all: document.querySelector(".checkbar .left").innerText }));
    ok("Prüfung: scores per part and in total after checking", /4 von 5/.test(sc.A) && /4 von 5/.test(sc.B) && /Ergebnis: 8 von 10/.test(sc.all), JSON.stringify(sc));
    const fbA = await page.$eval('#pqA .qq[data-k="4"] .fb', e => e.innerText);
    ok("Prüfung: a wrong answer shows the right one with the sentence and why", /^Falsch\. Richtig ist [abc]\)/.test(fbA) && fbA.length > 60, fbA.slice(0, 100));
    await page.click('#pqA .qq[data-k="1"] .fb .show');
    await page.waitForTimeout(300);
    ok("Prüfung: 'Stelle im Text zeigen' highlights the text", await page.evaluate(() => !!document.querySelector("article .flash")));
    await page.click(".checkbar .again");
    const fresh = await page.evaluate(() => ({ marks: document.querySelectorAll(".opt.yes, .opt.no, .opt.picked").length, disabled: document.getElementById("pcheck").disabled, last: document.getElementById("pqA").innerText }));
    ok("Prüfung: 'Nochmal von vorn' starts a clean round and shows the last result", fresh.marks === 0 && fresh.disabled && /Letztes Ergebnis: 4 von 5/.test(fresh.last), JSON.stringify(fresh).slice(0, 120));
  }
  for (const kind of ["rf", "headlines", "ads"]) {
    const n = kinds[kind];
    if (!n) { ok("a verified set with " + kind, false); continue; }
    const A = D.pq[n][0].items, P = D.pq[n][1];
    await open(n);
    if (kind === "headlines") ok("headlines: 8 headlines listed", (await page.$$eval("#pqB .heads li", e => e.length)) === 8);
    if (kind === "ads") ok("ads: the ads render as boxes", (await page.$$eval("article.pr .item", e => e.length)) >= 6);
    for (let k = 0; k < A.length; k++) await page.click('#pqA .qq[data-k="' + k + '"] .opt[data-j="' + A[k].a + '"]');
    for (let k = 0; k < P.items.length; k++) await pickB(P, k, P.items[k].a);
    await page.click("#pcheck");
    const s = await page.$eval("#pqB-score", e => e.textContent);
    const noWrong = await page.$$eval("#pqB .opt.no", e => e.length);
    let extra = "";
    if (kind === "ads") { const kx = P.items.findIndex(it => it.a === "x"); extra = await page.$eval('#pqB .qq[data-k="' + kx + '"] .fb', e => e.innerText); }
    ok(kind + ": all right gives 5 von 5" + (kind === "ads" ? ", and x counts as right" : ""), /5 von 5/.test(s) && noWrong === 0 && (kind !== "ads" || /^Richtig!/.test(extra)), s);
  }
  if (qsets.length) {
    await page.reload();
    await page.click("#bToc");
    const meta = await page.$eval('.toc li[data-n="' + qsets[0] + '"] .pchip', e => e.textContent);
    ok("contents shows the Prüfung quiz score after reload", /^Prüfung( ✓)? · Quiz \d+\/\d+$/.test(meta), meta);
    await page.click('.toc li[data-n="' + qsets[0] + '"]');
    const last = await page.$eval("#pqA", e => e.innerText);
    ok("the set shows the last Teil A result after reload", /Letztes Ergebnis: 4 von 5/.test(last));
  }
  await open(n0);
  await page.click('.vsw [data-ver="l"]');
  const leicht = await page.evaluate(() => ({ on: !!document.querySelector('.vsw [data-ver="l"].on'), pr: !!document.querySelector("article.pr"), quiz: !!document.querySelector("#quiz") }));
  ok("Leicht shows the easy story and its quiz", leicht.on && !leicht.pr && leicht.quiz, JSON.stringify(leicht));
  await page.reload();
  await page.click("#bToc");
  await page.click('.toc li[data-n="' + n0 + '"]');
  ok("the version choice is saved per story", await page.evaluate(() => !!document.querySelector('.vsw [data-ver="l"].on')));
  await page.click('.vsw [data-ver="p"]');
  await page.click("#mark");
  await page.click("#bToc");
  const pm = await page.$eval('.toc li[data-n="' + n0 + '"] .pchip', e => e.textContent);
  ok("Prüfung read mark shows in the contents", /^Prüfung ✓/.test(pm), pm);
  const xw = Object.entries(D.words).find(([id, w]) => /^X/.test(id) && (w.ps || []).some(n => D.pr[n]));
  await page.click("#bIdx");
  await page.fill("#search", xw ? xw[1].d : "angeblich");
  const idx = await page.$eval("#idx", e => e.innerText);
  ok("word index lists extras with their Prüfung sets", !!xw && /extra/.test(idx) && /P\d\d/.test(idx), (xw ? xw[1].d + ": " : "") + idx.slice(0, 120));
  await page.setViewportSize({ width: 390, height: 844 });
  await open(n0);
  r = await tap("article.pr .w");
  const fit = await page.evaluate(() => { const c = document.getElementById("card").getBoundingClientRect(); return c.left >= 0 && c.right <= window.innerWidth; });
  ok("phone: card fits on the screen in the Prüfung view", r.vis && fit);
  const all = await page.evaluate(() => { const D = JSON.parse(document.getElementById("data").textContent); const bad = []; Object.values(D.pr).forEach(P => P.blocks.forEach(b => b.s.forEach(sg => { if (Array.isArray(sg) && sg[1] && sg[2] !== "c") sg[1].split(",").forEach(i => { if (!D.words[i] || !D.words[i].g) bad.push(i); }); }))); return bad; });
  ok("every tappable word in the Prüfung texts has a meaning", all.length === 0, all.slice(0, 10).join(","));
  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
