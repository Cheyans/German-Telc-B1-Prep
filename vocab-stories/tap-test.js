
async page => {
  const FILE = globalThis.B1_FILE;
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  const near = (w, c) => !!c && c.y >= w.y + w.height - 2 && c.y - (w.y + w.height) <= 40 || !!c && c.y + c.height <= w.y + 2 && w.y - (c.y + c.height) <= 40;
  const inView = (c, vw, vh) => !!c && c.x >= 0 && c.x + c.width <= vw + 1 && c.y >= 0 && c.y + c.height <= vh + 1;
  const tapWord = async (n) => {
    const w = page.locator("article .w").nth(n);
    await w.scrollIntoViewIfNeeded();
    const b = await w.boundingBox();
    await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
    await page.waitForTimeout(250);
    const vis = await page.evaluate(() => { const c = document.getElementById("card"); const s = getComputedStyle(c); return s.display !== "none" && s.visibility !== "hidden" && c.offsetHeight > 0; });
    const c = vis ? await page.locator("#card").boundingBox() : null;
    return { w: b, c, vis };
  };
  await page.emulateMedia({ colorScheme: "dark" });
  await page.setViewportSize({ width: 1720, height: 1340 });
  await page.goto(FILE);
  await page.evaluate(() => { const v = {}; for (let i = 1; i <= 28; i++) v[String(i).padStart(2, "0")] = "l"; localStorage.setItem("b1VocabStories_v1", JSON.stringify({ ver: v })); });
  await page.reload();
  await page.click("#bToc");
  await page.click('.toc li[data-n="01"]');
  let r = await tapWord(3);
  ok("tall dark window: card opens right next to the tapped word", r.vis && near(r.w, r.c) && inView(r.c, 1720, 1340), JSON.stringify({ w: r.w && Math.round(r.w.y), c: r.c && Math.round(r.c.y) }));
  await page.click("#cardX");
  r = await tapWord(60);
  ok("after scrolling: card opens next to the word and stays on screen", r.vis && near(r.w, r.c) && inView(r.c, 1720, 1340), JSON.stringify({ w: r.w && Math.round(r.w.y), c: r.c && Math.round(r.c.y) }));
  await page.click("#cardX");
  await page.setViewportSize({ width: 390, height: 844 });
  r = await tapWord(5);
  ok("phone: card next to the word and inside the screen", r.vis && near(r.w, r.c) && inView(r.c, 390, 844), JSON.stringify({ w: r.w, c: r.c }));
  await page.click("#cardX");
  await page.setViewportSize({ width: 1720, height: 1340 });
  ok("no page errors", errors.length === 0, errors.join("; ").slice(0, 300));
  return out.join("\n");
}
