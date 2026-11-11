async page => {
  const FILE = globalThis.B1_FILE;
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  const ctx = page.context();
  const chromium = !!ctx.browser() && ctx.browser().browserType().name() === "chromium";
  const REAL = "Liebe Lena, vielen Dank für deine Einladung. Leider kann ich am Samstag nicht kommen, weil ich arbeiten muss. Hast du am Sonntag Zeit? Wir könnten zusammen frühstücken. Viele Grüße, Sam";
  const BLOCKER = '[style*="position: fixed"] { display: none !important; }';
  const stubOpen = () => page.evaluate(() => { window.__opened = []; window.open = u => { window.__opened.push(u); return null; }; });
  const opened = () => page.evaluate(() => window.__opened);
  const msg = () => page.$eval("#cmsg", e => ({ t: e.textContent, warn: e.classList.contains("warn"), color: getComputedStyle(e).color, hint: getComputedStyle(document.querySelector(".fbox p.hint")).color, after: (e.previousElementSibling || {}).className || "" }));
  const st = () => page.evaluate(() => JSON.parse(localStorage.getItem("b1VocabStories_v1") || "{}"));
  const watchCopy = () => page.evaluate(() => { window.__data = null; window.addEventListener("copy", e => { window.__data = { d: e.clipboardData ? e.clipboardData.getData("text/plain") : "", prevented: e.defaultPrevented }; }); });

  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.goto(FILE + "#/schreiben");
  await page.reload();
  const id = await page.evaluate(() => location.hash.split("/")[2]);
  await stubOpen();
  ok("the help line says the buttons need 15 words", /Ab 15 Wörtern/.test(await page.$eval(".fbox", e => e.textContent)));

  await page.click("#toClaude");
  let m = await msg();
  ok("an empty box gives a clear note and opens nothing", m.t === "Schreib zuerst deine E-Mail (mindestens 15 Wörter)." && m.warn && (await opened()).length === 0, m.t);
  await page.fill("#mtext", "Hallo");
  await page.click("#toGpt");
  ok("one word reads „1 Wort“", (await msg()).t === "Noch zu kurz: erst 1 Wort. Schreib mindestens 15 Wörter.", (await msg()).t);

  await page.fill("#mtext", "asefasef\nasefa\nasefasef\nasefase");
  await page.click("#toClaude");
  m = await msg();
  ok("the screenshot case (4 words) says how many words are missing and opens nothing", m.t === "Noch zu kurz: erst 4 Wörter. Schreib mindestens 15 Wörter." && (await opened()).length === 0, m.t);
  ok("the note is red, not gray like the help text", m.warn && m.color !== m.hint, m.color + " vs " + m.hint);
  ok("the note sits right under the buttons", /fbtns/.test(m.after), m.after);
  await page.click("#mDone");
  let S = await st();
  ok("„Fertig ohne Feedback“ with 4 words does not mark the email done", !((S.mails || {})[id] || {}).done && /erst 4 Wörter/.test((await msg()).t), id);

  await page.fill("#mtext", REAL);
  m = await msg();
  ok("the note goes away once the email is long enough", m.t === "" && !m.warn, m.t);
  await page.click("#mDone");
  S = await st();
  m = await msg();
  ok("„Fertig ohne Feedback“ with a real email marks it done", S.mails[id].done === true && m.t === "Erledigt. Gut gemacht!" && !m.warn, m.t);

  await page.addStyleTag({ content: BLOCKER });
  await watchCopy();
  await page.evaluate(() => { if (navigator.clipboard) navigator.clipboard.writeText = () => Promise.reject(new Error("blocked")); });
  await page.click("#toClaude");
  await page.waitForTimeout(200);
  const cd = await page.evaluate(() => window.__data);
  m = await msg();
  ok("the copy works even when a blocker hides fixed elements and the Clipboard API fails", !!cd && cd.prevented && /Meine E-Mail:/.test(cd.d) && cd.d.includes("Leider kann ich am Samstag"), JSON.stringify(cd && { len: cd.d.length, prevented: cd.prevented }));
  ok("then it says Kopiert and opens Claude", /^Kopiert/.test(m.t) && !m.warn && (await opened()).slice(-1)[0] === "https://claude.ai/new", m.t);

  await page.evaluate(() => { document.execCommand = () => { throw new Error("no copy"); }; });
  await page.click("#toGpt");
  await page.waitForTimeout(200);
  m = await msg();
  ok("if both copy paths fail, it says so and opens the box with the text", /nicht geklappt/.test(m.t) && m.warn && (await page.$eval("#pboxWrap", e => e.open)) && /Meine E-Mail:/.test(await page.$eval("#pbox", e => e.value)), m.t);

  if (chromium) {
    await ctx.grantPermissions(["clipboard-read", "clipboard-write"]);
    await page.reload();
    await page.fill("#mtext", REAL);
    await page.addStyleTag({ content: BLOCKER });
    await stubOpen();
    await page.evaluate(() => navigator.clipboard.writeText("SENTINEL"));
    await page.click("#toClaude");
    await page.waitForTimeout(300);
    const clip = await page.evaluate(() => navigator.clipboard.readText());
    ok("Chrome: the real clipboard holds the prompt even with the blocker", /Meine E-Mail:/.test(clip) && clip.includes("Leider kann ich am Samstag"), clip.slice(0, 40));
  } else ok("SKIP real clipboard read: only Chrome allows it in tests", true);

  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
