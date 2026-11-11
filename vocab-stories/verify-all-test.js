async page => {
  const FILE = globalThis.B1_FILE;
  const out = [];
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const D = await page.evaluate(() => JSON.parse(document.getElementById("data").textContent));
  const nums = D.stories.map(s => s.n);
  let bad = 0;
  for (const n of nums) {
    const notes = [];
    await page.click("#bToc");
    await page.click('.toc li[data-n="' + n + '"]');
    const P = D.pq[n];
    if (!D.pr[n] || !P) { notes.push("no Prüfung set or quiz"); }
    else {
      const view = await page.evaluate(() => ({ p: !!document.querySelector('.vsw [data-ver="p"].on'), parts: document.querySelectorAll(".part").length, A: !!document.getElementById("pqA"), B: !!document.getElementById("pqB") }));
      if (!view.p || view.parts !== 2 || !view.A || !view.B) notes.push("Prüfung view " + JSON.stringify(view));
      for (let k = 0; k < P[0].items.length; k++) await page.click('#pqA .qq[data-k="' + k + '"] .opt[data-j="' + P[0].items[k].a + '"]');
      const B = P[1];
      for (let k = 0; k < B.items.length; k++) {
        if (B.t === "rf") await page.click('#pqB .rq[data-k="' + k + '"] .opt[data-rf="' + (B.items[k].a ? "1" : "0") + '"]');
        else await page.click('#pqB .mq[data-k="' + k + '"] .let[data-l="' + B.items[k].a + '"]');
      }
      const before = await page.evaluate(() => document.querySelectorAll(".opt.yes, .opt.no").length + document.querySelector("#pqA-score").textContent.length);
      if (before) notes.push("feedback shown before checking");
      await page.click("#pcheck");
      const sA = await page.$eval("#pqA-score", e => e.textContent);
      if (!/Ergebnis: 5 von 5/.test(sA)) notes.push("Teil A score: " + sA);
      const sB = await page.$eval("#pqB-score", e => e.textContent);
      if (!/Ergebnis: 5 von 5/.test(sB)) notes.push("Teil B score: " + sB);
      await page.click('#pqB .qq[data-k="0"] .fb .show');
      await page.waitForTimeout(120);
      if (!(await page.evaluate(() => !!document.querySelector("article .flash")))) notes.push("'Stelle im Text zeigen' did not highlight");
      await page.keyboard.press("Escape");
      const w = page.locator("article.pr .w").first();
      await w.scrollIntoViewIfNeeded();
      const bx = await w.boundingBox();
      await page.mouse.click(bx.x + Math.min(8, bx.width / 2), bx.y + bx.height / 2);
      await page.waitForTimeout(80);
      const card = await page.evaluate(() => { const c = document.getElementById("card"); return getComputedStyle(c).display === "block" ? c.innerText.replace(/\s+/g, " ") : ""; });
      if (!card || card.length < 15) notes.push("word card did not open");
      await page.keyboard.press("Escape");
      await page.click('.vsw [data-ver="l"]');
    }
    const Q = D.quiz[n];
    if (!Q) notes.push("no Leicht quiz");
    else {
      for (let k = 0; k < Q.length; k++) await page.click('#quiz .qq[data-k="' + k + '"] .opt[data-j="' + Q[k].a + '"]');
      if (await page.evaluate(() => document.querySelectorAll("#quiz .opt.yes, #quiz .opt.no").length)) notes.push("Leicht feedback before checking");
      await page.click("#qcheck");
      const sL = await page.$eval("#qscore", e => e.textContent);
      if (!new RegExp("Ergebnis: " + Q.length + " von " + Q.length).test(sL)) notes.push("Leicht score: " + sL);
    }
    await page.click("#bToc");
    const meta = await page.$eval('.toc li[data-n="' + n + '"]', e => e.innerText.replace(/\s+/g, " "));
    if (!/Leicht · Quiz 5\/5/.test(meta) || (D.pr[n] && !/Prüfung · Quiz 10\/10/.test(meta))) notes.push("contents line: " + meta);
    if (notes.length) bad++;
    out.push((notes.length ? "FAIL " : "PASS ") + n + " " + (D.pr[n] ? D.pr[n].b : "") + (notes.length ? " | " + notes.join(" ; ") : ""));
  }
  out.push((bad === 0 && errors.length === 0 ? "PASS" : "FAIL") + " all " + nums.length + " stories, " + bad + " with problems, page errors: " + (errors.join(" | ") || "none"));
  return out.join("\n");
}
