async page => {
  const FILE = globalThis.B1_FILE;
  const COPY = globalThis.B1_COPY;
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  const old = { read: { "01": true }, en: false, last: "01", quiz: { "01": { r: [1, 1, 0, 1, 1] } }, syn: false, drill: {}, ver: { "02": "l" }, pread: { "03": true }, pq: { "01": { A: [1, 1, 1, 1, 1], B: [1, 0, 1, 1, 1] } }, welcomed: true };
  await page.evaluate(s => localStorage.setItem("b1VocabStories_v1", JSON.stringify(s)), old);
  await page.reload();
  const welcomeOnDay = await page.evaluate(() => !!document.querySelector(".welcome"));
  await page.click("#bToc");
  const toc = await page.evaluate(() => ({ chk: (document.querySelector('.toc li[data-n="01"] .lchip').textContent.includes("✓") ? "✓" : ""), meta: document.querySelector('.toc li[data-n="01"]').innerText.replace(/\s+/g, " "), p3: document.querySelector('.toc li[data-n="03"]').innerText, welcome: !!document.querySelector(".welcome") }));
  ok("progress saved by the 11-05 version loads: read mark and both quiz scores", toc.chk === "✓" && /Quiz 4\/5/.test(toc.meta) && /Quiz 9\/10/.test(toc.meta), toc.meta.slice(0, 160));
  ok("old progress: the Prüfung read mark and the hidden welcome box are kept", /Prüfung ✓/.test(toc.p3) && !welcomeOnDay);
  await page.click('.toc li[data-n="02"]');
  ok("old progress: the saved version choice is kept (story 02 opens in Leicht)", await page.evaluate(() => !!document.querySelector('.vsw [data-ver="l"].on')));
  await page.click("#bToc");
  await page.evaluate(() => { window.__blob = null; const orig = URL.createObjectURL; URL.createObjectURL = function (b) { window.__blob = b; return orig.call(URL, b); }; });
  await page.click("#saveProg");
  const backup = await page.evaluate(async () => window.__blob ? await window.__blob.text() : "");
  let parsed = null;
  try { parsed = JSON.parse(backup); } catch (e) {}
  ok("Fortschritt sichern makes a backup file with the progress", !!parsed && parsed.app === "b1VocabStories" && parsed.state.read["01"] === true && parsed.state.pq["01"].B.length === 5, backup.slice(0, 70));
  ok("the contents show the version date", await page.evaluate(() => /Version vom \d\d\.\d\d\.\d{4}/.test(document.querySelector("main").innerText)));
  const load = async (txt) => {
    await page.evaluate((t) => { const dt = new DataTransfer(); dt.items.add(new File([t], "b1-fortschritt.json", { type: "application/json" })); const inp = document.getElementById("loadProg"); inp.files = dt.files; inp.dispatchEvent(new Event("change")); }, txt);
    await page.waitForTimeout(400);
  };
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.click("#bToc");
  ok("after clearing the browser storage, the progress is gone", !(await page.$eval('.toc li[data-n="01"] .lchip', e => e.textContent)).includes("✓"));
  await page.click('.toc li[data-n="05"]');
  await page.click("#mark");
  await page.click("#bToc");
  await load(backup);
  const back = await page.evaluate(() => ({ c1: (document.querySelector('.toc li[data-n="01"] .lchip').textContent.includes("✓") ? "✓" : ""), c5: document.querySelector('.toc li[data-n="05"]').innerText, meta: document.querySelector('.toc li[data-n="01"]').innerText.replace(/\s+/g, " "), msg: (document.getElementById("progMsg") || {}).textContent }));
  ok("Fortschritt laden brings the old progress back", back.c1 === "✓" && /Quiz 4\/5/.test(back.meta) && /Quiz 9\/10/.test(back.meta) && /Geladen/.test(back.msg), JSON.stringify(back).slice(0, 160));
  ok("loading only adds: progress made in the new file stays", /✓/.test(back.c5));
  await load('{"foo": 1}');
  ok("a wrong file is rejected with a message", /keine Sicherungsdatei/.test(await page.$eval("#progMsg", e => e.textContent)));
  await page.reload();
  await page.click("#bToc");
  ok("after a reload (same file, same place) the progress is still there", (await page.$eval('.toc li[data-n="01"] .lchip', e => e.textContent)).includes("✓"));
  const cover = await page.evaluate(() => {
    const D = JSON.parse(document.getElementById("data").textContent), W = /[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*/g, miss = new Set();
    const has = f => D.off[f] || D.off[f.toLowerCase()] || D.off[f.charAt(0).toUpperCase() + f.slice(1)];
    const conn = sg => { const m = /^k\w+:\d+:(.+)$/.exec(sg[4] || ""); return !!m && D.syn.items.some(it => it.w === m[1] && it.en); };
    const walk = segs => segs.forEach(sg => {
      if (typeof sg === "string") { (sg.match(W) || []).forEach(f => { if (f.length > 1 && !has(f)) miss.add(f); }); }
      else if (sg[2] === "r" && !sg[1] && sg[0].length > 1 && !has(sg[0]) && !conn(sg)) miss.add(sg[0]);
    });
    D.stories.forEach(s => s.p.forEach(walk));
    Object.values(D.pr).forEach(P => P.blocks.forEach(b => walk(b.s)));
    Object.values(D.quiz).forEach(Q => Q.forEach(q => { walk(q.q); q.o.forEach(walk); }));
    Object.values(D.pq).forEach(parts => parts.forEach(p => { p.items.forEach(it => { if (it.q) { walk(it.q); it.o.forEach(walk); } else walk(it.s); }); (p.opts || []).forEach(o => walk(o.s)); }));
    const ids = Object.values(D.off).filter(o => o.id && !D.words[o.id]).length;
    return { miss: [...miss].slice(0, 15), n: miss.size, ids };
  });
  ok("every tappable word has a meaning (list entry or off-list gloss)", cover.n === 0 && cover.ids === 0, JSON.stringify(cover));
  await page.click('.toc li[data-n="17"]');
  const offForm = await page.evaluate(() => { const D = JSON.parse(document.getElementById("data").textContent); const el = [...document.querySelectorAll("article .n")].find(x => { const o = D.off[x.textContent]; return o && o.k === "word" && !o.id; }); return el ? el.textContent : null; });
  if (offForm) {
    const el = page.locator("article .n", { hasText: offForm }).first();
    await el.scrollIntoViewIfNeeded();
    await el.click();
    const card = await page.evaluate(() => document.getElementById("card").innerText.replace(/\s+/g, " "));
    ok("tap an off-list word: meaning plus the not-on-the-list note", /nicht auf der Liste/.test(card) && /Nicht auf der B1-Wortliste/.test(card) && card.length > 60, card.slice(0, 160));
  } else ok("found an off-list word in set 17", false);
  const tapOff = async kind => {
    const hit = await page.evaluate(kind => {
      const D = JSON.parse(document.getElementById("data").textContent), W = /[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*/g;
      const want = o => o && (kind === "linked" ? o.k === "word" && !!o.id : o.k === kind);
      for (const s of D.stories) for (const p of s.p) for (const sg of p) if (typeof sg === "string") for (const f of (sg.match(W) || [])) if (f.length > 1 && want(D.off[f])) return { n: s.n, f };
      return null;
    }, kind);
    if (!hit) return { f: null, card: "" };
    await page.keyboard.press("Escape");
    await page.click("#bToc");
    await page.click('.toc li[data-n="' + hit.n + '"]');
    if (await page.$('.vsw [data-ver="l"]')) await page.click('.vsw [data-ver="l"]');
    const el = page.locator("article .n").filter({ hasText: new RegExp("^" + hit.f + "$") }).first();
    await el.scrollIntoViewIfNeeded();
    await el.click();
    await page.waitForTimeout(80);
    return { f: hit.f, card: await page.evaluate(() => document.getElementById("card").innerText.replace(/\s+/g, " ")) };
  };
  const linked = await tapOff("linked");
  ok("tap a new form of a list word: its meaning plus the list word, no off-list badge", !!linked.f && /Das Grundwort steht auf der Liste/.test(linked.card) && !/nicht auf der Liste/.test(linked.card), linked.f + " | " + linked.card.slice(0, 170));
  const name = await tapOff("name");
  ok("tap a name: marked Name, no learn-it note", !!name.f && /Name/.test(name.card) && !/Nicht auf der B1-Wortliste/.test(name.card), name.f + " | " + name.card.slice(0, 170));
  await page.keyboard.press("Escape");
  try {
    await page.goto(COPY);
    const there = await page.evaluate(() => !!localStorage.getItem("b1VocabStories_v1"));
    out.push("INFO a copy of the file at another path " + (there ? "SEES" : "does NOT see") + " the same progress in this browser");
  } catch (e) { out.push("INFO no copy at " + COPY + ", skipped the other-path check"); }
  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
