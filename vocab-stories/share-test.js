async page => {
  const FILE = globalThis.B1_FILE;
  const K = "b1VocabStories_v1";
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  const web = /^https?:/.test(FILE);
  const st = () => page.evaluate(k => JSON.parse(localStorage.getItem(k) || "{}"), K);
  const set = s => page.evaluate(([k, s]) => localStorage.setItem(k, JSON.stringify(s)), [K, s]);
  const stubShare = () => page.evaluate(() => { window.__shared = null; navigator.share = d => { window.__shared = d; return Promise.resolve(); }; });
  await page.setViewportSize({ width: 1280, height: 900 });
  const openFresh = async (link, keep) => { if (!keep) await page.evaluate(() => localStorage.clear()); await page.goto("about:blank"); await page.goto(link); await page.waitForFunction(() => !location.hash.startsWith("#/sync/") || !!document.getElementById("syncNote"), null, { timeout: 8000 }).catch(() => {}); };
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const SITE = await page.evaluate(() => JSON.parse(document.getElementById("data").textContent).site);
  const today = await page.evaluate(() => { const d = new Date(); return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); });
  const sender = { v: 2, welcomed: true, read: { "05": true }, quiz: { "05": { r: [1, 1, 0, 1, 1] } }, srs: { W0102: [3, 20000, 19000], W0104: [2, 20001, 19000] }, look: {}, plan: { size: 1, log: { [today]: { wd: 1 } } }, hres: {}, mails: { M01: { t: "Liebe Lena, das ist mein Entwurf.", d: today } } };
  await set(sender);
  await page.reload();
  await page.click("#bToc");
  await page.click('.toc li[data-n="05"]');
  await page.click('.vsw [data-ver="l"]');
  await page.click("#bToc");
  const label = await page.$eval(".sharerow button.share", b => b.textContent).catch(() => "");
  ok("Themen has the button „Share to your other device“", label === "Share to your other device", label);
  await stubShare();
  await page.click(".sharerow button.share");
  await page.waitForFunction(() => window.__shared, null, { timeout: 5000 }).catch(() => {});
  const shared = await page.evaluate(() => window.__shared);
  const url = shared && shared.url || "";
  const base = web ? FILE : SITE;
  ok(web ? "on the website the link points to this website" : "from the file the link points to the website, not the file", url.startsWith(base + "#/sync/"), url.slice(0, 80));
  ok("the phone share sheet gets a title and the link", !!shared && !!shared.title && !!url);
  ok("the link is short enough for chats and AirDrop", url.length > 0 && url.length < 60000, url.length + " characters");

  await openFresh(url.replace(base, FILE));
  let S = await st();
  const hash = await page.evaluate(() => location.hash);
  ok("on a new device, the link opens at the same place (the story that was open)", hash === "#/story/05/l" && !!(await page.$("article h2")), hash);
  ok("… with all the progress: read texts, quiz, words, the day, the email draft", S.read["05"] === true && !!S.quiz["05"] && !!S.srs.W0102 && !!S.plan.log[today] && /mein Entwurf/.test((S.mails.M01 || {}).t || ""), JSON.stringify(Object.keys(S)));
  ok("… and a note says it worked", /Fortschritt vom anderen Gerät übernommen/.test(await page.$eval("#syncNote", d => d.textContent).catch(() => "")));
  await page.click("#bDay");
  ok("the note goes away once you move on", !(await page.$("#syncNote")));

  await set({ v: 2, welcomed: true, read: { "07": true }, srs: { W9999: [1, 20000, 19000] } });
  await openFresh(url.replace(base, FILE), true);
  S = await st();
  ok("on a device with its own progress, nothing is lost: both are kept", S.read["05"] === true && S.read["07"] === true && !!S.srs.W9999 && !!S.srs.W0102, JSON.stringify(S.read));

  await page.goto(FILE + "#/heute");
  await page.reload();
  ok("Heute has the button too", !!(await page.$(".sharerow button.share")));
  await stubShare();
  await page.click(".sharerow button.share");
  await page.waitForFunction(() => window.__shared, null, { timeout: 5000 }).catch(() => {});
  const fromDay = (await page.evaluate(() => window.__shared && window.__shared.url)) || "";
  await openFresh(fromDay.replace(base, FILE));
  ok("shared from Heute, the link opens Heute", (await page.evaluate(() => location.hash)) === "#/heute" && !!(await page.$(".day .tasks")));

  await page.goto(FILE + "#/themen");
  await page.reload();
  await page.evaluate(() => { try { delete Navigator.prototype.share; } catch (e) {} navigator.share = undefined; });
  await page.click(".sharerow button.share");
  await page.waitForFunction(() => { const b = document.querySelector(".sharerow .shlink"); return b && !b.hidden && b.value; }, null, { timeout: 5000 }).catch(() => {});
  const box = await page.$eval(".sharerow .shlink", b => ({ hidden: b.hidden, value: b.value }));
  const m = await page.$eval(".sharerow .shmsg", s => s.textContent);
  ok("without a share sheet, the link is copied and shown to copy by hand", !box.hidden && box.value.startsWith(base + "#/sync/") && /Link kopiert|Kopiere den Link/.test(m), m);

  const D = await page.evaluate(() => { const d = JSON.parse(document.getElementById("data").textContent); return { words: Object.keys(d.words), stories: d.stories.map(x => x.n), built: d.hoeren.map(h => [h.id, h.items.length]), linked: (d.hlinked || []).map(x => [x.id, x.n || null]), mail: d.mail.map(m => [m.id, m.kind, m.mail]) }; });
  const prose = D.mail.map(m => m[2]).join(" ");
  const text = (n, off) => { let t = "", i = off % prose.length; while (t.length < n) { t += prose.slice(i, i + n - t.length); i = 0; } return t; };
  const make = (words, days, mails, linked) => {
    const S = { v: 2, welcomed: true, read: {}, pread: {}, quiz: {}, pq: {}, ver: {}, srs: {}, look: {}, plan: { size: 1, log: {} }, hres: {}, mails: {} };
    D.stories.forEach(n => { S.read[n] = true; S.pread[n] = true; S.quiz[n] = { r: [1, 1, 0, 1, 1] }; S.pq[n] = { A: [1, 0, 1, 1, 1], B: [1, 1, 1, 0, 1] }; S.ver[n] = "p"; });
    D.words.slice(0, words).forEach((k, i) => { S.srs[k] = [1 + (i % 6), 20800 + ((i * 7) % 61), 20400 + Math.floor(i / 5)]; });
    for (let x = 0; x < days; x++) S.plan.log[new Date(Date.UTC(2026, 10, 12 + Math.floor(x * 7 / 5))).toISOString().slice(0, 10)] = { wd: { r: 10 + (x % 20), n: 5 }, wn: 5, h: "U" + (1 + x % 7), l: D.stories[x % 28] + (x % 2 ? "B" : "A"), s: D.mail[x % 52][0], size: x % 4 };
    D.built.forEach(([id, n]) => { S.hres[id] = { r: Array.from({ length: n }, (_, j) => (j % 3 ? 1 : 0)), d: "2026-12-01" }; });
    D.linked.slice(0, linked).forEach(([id, n], i) => { S.hres[id] = { s: n ? n - (i % 3) : null, n: n, d: "2027-01-15", x: 1 }; });
    D.mail.slice(0, mails).forEach(([id, kind], i) => { S.mails[id] = { t: text(kind === "full" ? 820 : 360, i * 977), done: true, d: "2027-02-01" }; });
    return S;
  };
  for (const [lab, B] of [["5 months (600 words, 107 days, 45 emails)", make(600, 107, 45, 60)], ["the maximum (all " + D.words.length + " words, 200 days, all 52 emails, all listening)", make(D.words.length, 200, 52, 114)]]) {
    await set(B);
    await page.goto("about:blank");
    await page.goto(FILE + "#/heute");
    await stubShare();
    await page.click(".sharerow button.share");
    await page.waitForFunction(() => window.__shared, null, { timeout: 15000 }).catch(() => {});
    const u = (await page.evaluate(() => window.__shared && window.__shared.url)) || "";
    await openFresh(u.replace(base, FILE));
    S = await st();
    const full = Object.keys(S.srs || {}).length === Object.keys(B.srs).length && Object.keys(S.plan.log).length === Object.keys(B.plan.log).length && Object.keys(S.hres).length === Object.keys(B.hres).length && Object.keys(S.mails).length === Object.keys(B.mails).length && Object.values(S.mails).every(m => m.t);
    ok("with " + lab + ", the link stays under 30,000 characters and everything arrives, email texts too", u.length > 0 && u.length <= 30000 && full, u.length + " characters");
    if (lab.startsWith("the maximum")) {
      await openFresh(u.slice(0, Math.floor(u.length / 2)).replace(base, FILE));
      S = await st();
      ok("a link cut in half by a chat app says so and imports nothing", /ließ sich nicht lesen/.test(await page.$eval("#syncNote", d => d.textContent).catch(() => "")) && !Object.keys(S.srs || {}).length);
    }
  }

  const oldLink = await page.evaluate(async ([base]) => {
    const st = { v: 2, welcomed: true, read: { "09": true }, srs: { W0102: [4, 20500, 20400] }, plan: { size: 0, log: {} }, hres: {}, mails: {} };
    const data = new TextEncoder().encode(JSON.stringify({ app: "b1VocabStories", v: 2, saved: new Date().toISOString(), built: "2026-11-11", go: "#/story/09/p", state: st }));
    const buf = new Uint8Array(await new Response(new Blob([data]).stream().pipeThrough(new CompressionStream("deflate-raw"))).arrayBuffer());
    let bin = ""; buf.forEach(b => { bin += String.fromCharCode(b); });
    return base + "#/sync/z." + btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }, [FILE]);
  await openFresh(oldLink);
  S = await st();
  ok("links made by the first version still open", S.read["09"] === true && JSON.stringify(S.srs.W0102) === "[4,20500,20400]" && (await page.evaluate(() => location.hash)) === "#/story/09/p");

  await openFresh(FILE + "#/sync/z.not-a-real-link");
  ok("a broken link says so and opens Heute", /ließ sich nicht lesen/.test(await page.$eval("#syncNote", d => d.textContent).catch(() => "")) && (await page.evaluate(() => location.hash)) === "#/heute");
  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
