async page => {
  const FILE = globalThis.B1_FILE;
  const KEY = "b1VocabStories_v1";
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const D = await page.evaluate(() => JSON.parse(document.getElementById("data").textContent));
  const st = () => page.evaluate(k => JSON.parse(localStorage.getItem(k) || "{}"), KEY);
  const setSt = s => page.evaluate(([k, v]) => localStorage.setItem(k, JSON.stringify(v)), [KEY, s]);
  const txt = sel => page.$eval(sel, e => e.innerText.replace(/\s+/g, " "));
  const ymd = d => d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2);
  const today = ymd(new Date()), yesterday = ymd(new Date(Date.now() - 86400000));
  const dayNum = s => { const p = s.split("-"); return Math.round(Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000); };
  const T0 = dayNum(today);

  ok("the page opens on Heute, and Heute is marked in the menu", !!(await page.$(".day .tasks")) && await page.$eval("#bDay", b => b.classList.contains("cur")));
  ok("Heute has one Weiter button for the next task", /^Weiter: Wörter üben/.test(await txt(".day .goNext")));
  const tasks = await page.$$eval(".tasks .task", l => l.map(x => x.getAttribute("data-t") + (x.classList.contains("off") ? "-off" : "")));
  ok("Heute lists the 4 tasks, all in the plan by default", JSON.stringify(tasks) === JSON.stringify(["w", "h", "l", "s"]), JSON.stringify(tasks));
  ok("50 Min (all four tasks) is the default size", /50 Min/.test(await txt(".sizes button.on")));
  await page.click('.sizes button[data-size="2"]');
  const t2 = await page.$$eval(".tasks .task", l => l.map(x => x.classList.contains("off")));
  ok("Kurz keeps Wörter and Hören and frees Lesen and Schreiben", JSON.stringify(t2) === "[false,false,true,true]" && (await st()).plan.size === 2, JSON.stringify(t2));
  await page.click('.sizes button[data-size="0"]');

  await page.click("#bToc");
  await page.click('.toc li[data-n="05"]');
  if (await page.$('.vsw [data-ver="l"]')) await page.click('.vsw [data-ver="l"]');
  const wEl = page.locator("article .w").first();
  await wEl.scrollIntoViewIfNeeded();
  await wEl.click();
  ok("a word card has ☆ Merken", /☆ Merken/.test(await txt("#card")));
  await page.click("#card .star");
  let S = await st();
  const starred = Object.keys(S.srs || {}).find(k => S.srs[k][0] === 0);
  ok("Merken puts the word in Meine Wörter as new", !!starred && /★ Gemerkt/.test(await txt("#card")), starred);
  await page.keyboard.press("Escape");
  const w2 = page.locator("article .w").nth(3);
  await w2.scrollIntoViewIfNeeded();
  await w2.click();
  S = await st();
  ok("tapping a word notes it as looked up", Object.keys(S.look || {}).length >= 1, JSON.stringify(S.look));
  await page.keyboard.press("Escape");

  await page.click("#bDay");
  await page.click('.task[data-t="w"]');
  const front = await txt(".wfront");
  const info = D.words[starred];
  ok("Wörter üben starts with the starred word (German first)", front === info.d.split(",")[0].trim(), front + " vs " + info.d);
  await page.click("#wShow");
  ok("Zeigen shows the meaning and an example sentence", (await txt(".wback")).includes(info.g) && !!(await page.$(".wex b")), (await txt(".wback")).slice(0, 120));
  await page.click("#wBad");
  let guard = 0;
  while (!(await page.$(".wsum")) && guard++ < 40) {
    if (await page.$("#wShow")) await page.click("#wShow");
    if (await page.$("#wBad")) await page.click("#wBad");
    else if (await page.$("#wGood")) await page.click("#wGood");
  }
  S = await st();
  ok("the session ends with a summary", !!(await page.$(".wsum")), await txt("main"));
  ok("a new word marked Neu für mich is due tomorrow in box 1", S.srs[starred][0] === 1 && S.srs[starred][1] === T0 + 1, JSON.stringify(S.srs[starred]));
  ok("words done is logged for today", !!(S.plan.log[today] || {}).wd, JSON.stringify(S.plan.log[today]));
  const nNew = Object.keys(S.srs).length;
  ok("up to 5 new words a day", nNew >= 1 && nNew <= 5, String(nNew));

  S.srs[starred] = [2, T0 - 1, T0 - 5];
  const other = Object.keys(S.srs).find(k => k !== starred);
  if (other) S.srs[other] = [3, T0, T0 - 9];
  delete S.plan.log[today].wd;
  await setSt(S);
  await page.reload();
  await page.click("#bDay");
  await page.click('.task[data-t="w"]');
  ok("a due word comes back as a review", /Wiederholung/.test(await txt(".sub")), await txt(".sub"));
  await page.click("#wShow");
  await page.click("#wGood");
  S = await st();
  ok("Gewusst moves the word up a box and spaces it out (box 3, in 7 days)", S.srs[starred][0] === 3 && S.srs[starred][1] === T0 + 7, JSON.stringify(S.srs[starred]));
  if (other) {
    const f2 = await txt(".wfront");
    ok("from box 3 on, the card asks for the German (English first)", f2 === (D.words[other] || { g: D.off[other.slice(2)] && D.off[other.slice(2)].g }).g, f2);
  }
  await page.evaluate(() => { window.__blobs = []; const o = URL.createObjectURL; URL.createObjectURL = b => { window.__blobs.push(b); return o.call(URL, b); }; });
  guard = 0;
  while (!(await page.$(".wsum")) && guard++ < 40) {
    if (await page.$("#wShow")) await page.click("#wShow");
    if (await page.$("#wGood")) await page.click("#wGood");
  }
  await page.click("#anki");
  const anki = await page.evaluate(async () => window.__blobs.length ? await window.__blobs[window.__blobs.length - 1].text() : "");
  ok("Für Anki exportieren makes a tab-separated file", /^#separator:tab/.test(anki) && anki.split("\n").filter(l => l.split("\t").length === 3).length >= 1, anki.slice(0, 160));

  if ((D.hoeren || []).length) {
    await page.click("#bDay");
    const T = D.hoeren[0];
    await page.click('.task[data-t="h"]');
    const a = await page.$eval("#hq .btn.audio, .abtns .btn.audio", e => ({ href: e.href, target: e.target }));
    ok("Hören opens the first task with an allango link in a new tab", a.href.startsWith("https://www.allango.net/") && a.target === "_blank", JSON.stringify(a));
    ok("all statements show, checking is off until all are answered", (await page.$$("#hq .qq")).length === T.items.length && await page.$eval("#hcheck", b => b.disabled));
    for (let k = 0; k < T.items.length; k++) {
      const want = k === 0 ? !T.items[k].a : T.items[k].a;
      await page.click('#hq .qq[data-k="' + k + '"] .opt[data-rf="' + (want ? "1" : "0") + '"]');
    }
    ok("no right or wrong shows before checking", (await page.$$("#hq .opt.yes, #hq .opt.no")).length === 0);
    await page.click("#hcheck");
    const sc = await txt(".checkbar .left");
    ok("the score counts one wrong answer", new RegExp("Ergebnis: " + (T.items.length - 1) + " von " + T.items.length).test(sc), sc);
    const fb = await txt('#hq .qq[data-k="0"] .fb');
    ok("each answer shows the time in the audio and the reason", /im Audio/.test(fb) && fb.length > 40, fb.slice(0, 160));
    S = await st();
    ok("the result is saved and Hören is done today", !!S.hres[T.id] && S.plan.log[today].h === T.id);
    ok("after checking, Weiter leads to the next task", /^Weiter: Lesen/.test(await txt("main .nextbar .goNext")), await txt("main .nextbar"));
  } else ok("SKIP Hören: no verified listening tasks in this build", true);

  await page.click("#bDay");
  await page.click('.task[data-t="l"]');
  const parts = await page.$$eval("article .part", l => l.length);
  ok("Lesen opens one part of the next Prüfung set, with a link back to Heute", parts === 1 && !!(await page.$("#pqA")) && !(await page.$("#pqB")) && !!(await page.$(".toDay")), "parts " + parts);
  const n0 = D.stories.find(s => D.pq[s.n]).n, QA = D.pq[n0][0];
  for (let k = 0; k < QA.items.length; k++) await page.click('#pqA .qq[data-k="' + k + '"] .opt[data-j="' + QA.items[k].a + '"]');
  await page.click("#pcheck");
  S = await st();
  ok("checking Teil A saves only Teil A and marks Lesen done", !!S.pq[n0].A && !S.pq[n0].B && S.plan.log[today].l === n0 + "A", JSON.stringify(S.pq[n0]));

  if ((D.mail || []).length) {
    await page.click("#bDay");
    await page.click('.task[data-t="s"]');
    const M = D.mail[0];
    ok("Schreiben shows the first task with its points", (await txt(".mz .task")).includes(M.points[0]), M.id);
    await page.fill("#mtext", "Liebe Lena, vielen Dank für deine Einladung. Leider kann ich am Samstag nicht kommen, weil ich arbeiten muss. Hast du am Sonntag Zeit? Wir könnten zusammen frühstücken. Viele Grüße, Sam");
    S = await st();
    ok("the email is saved while typing", /vielen Dank/.test((S.mails[M.id] || {}).t || ""));
    await page.evaluate(() => { window.__opened = []; window.open = u => { window.__opened.push(u); return null; }; });
    await page.click("#toClaude");
    const copied = await page.$eval("#pbox", e => e.value);
    const opened = await page.evaluate(() => window.__opened);
    ok("Feedback mit Claude builds the prompt with grader, task and email", /telc Deutsch B1/.test(copied) && copied.includes(M.points[0]) && copied.includes("Leider kann ich am Samstag"), copied.slice(0, 120));
    ok("it opens Claude in a new tab", opened[0] === "https://claude.ai/new", JSON.stringify(opened));
    ok("the mini grader is used for a mini task", M.kind !== "mini" || (/mini task/.test(copied) && !/out of 45/.test(copied)));
    await page.check("#flagFirst");
    await page.click("#toGpt");
    ok("ChatGPT works too, and the flag-first option adds the self-correction round", (await page.evaluate(() => window.__opened))[1] === "https://chatgpt.com/" && /First round only/.test(await page.$eval("#pbox", e => e.value)));
    S = await st();
    ok("the email is marked done and Schreiben is done today", S.mails[M.id].done === true && S.plan.log[today].s === M.id);
  } else ok("SKIP Schreiben: no mail prompts in this build", true);

  await page.click("#bDay");
  const week = await txt(".week");
  ok("the week strip marks today", /●|◐/.test(await page.$eval(".week .wd.today", e => e.textContent)), week);
  ok("the summary counts today's tasks", /erledigt|geschafft/.test(await txt("article .sub")), await txt("article .sub"));

  S = await st();
  S.plan.log[yesterday] = S.plan.log[today];
  delete S.plan.log[today];
  await setSt(S);
  await page.reload();
  await page.click("#bDay");
  const nextL = await txt('.task[data-t="l"] .meta');
  ok("the next day, Lesen moves on to Teil B of the same set", nextL.includes(n0) && /Teil B/.test(nextL), nextL);
  if ((D.hoeren || []).length > 1) {
    const nextH = await txt('.task[data-t="h"] .meta');
    ok("the next day, Hören moves on to the next task", nextH.includes(D.hoeren[1].title), nextH);
  }
  ok("Lerntag counts days with activity", /Lerntag 2/.test(await txt("article .sub")), await txt("article .sub"));

  await page.click("#bToc");
  await page.evaluate(() => { window.__blobs = []; const o = URL.createObjectURL; URL.createObjectURL = b => { window.__blobs.push(b); return o.call(URL, b); }; });
  await page.click("#saveProg");
  const bk = JSON.parse(await page.evaluate(async () => await window.__blobs[0].text()));
  ok("the backup file includes the daily plan, words, listening and emails", !!bk.state.srs && !!bk.state.plan && !!bk.state.hres && !!bk.state.mails && Object.keys(bk.state.srs).length > 0);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await page.click("#bToc");
  await page.evaluate(t => { const dt = new DataTransfer(); dt.items.add(new File([t], "b.json", { type: "application/json" })); const i = document.getElementById("loadProg"); i.files = dt.files; i.dispatchEvent(new Event("change", { bubbles: true })); }, JSON.stringify(bk));
  await page.waitForTimeout(300);
  S = await st();
  ok("loading the backup brings the words and the plan back", Object.keys(S.srs || {}).length === Object.keys(bk.state.srs).length && !!(S.plan.log || {})[yesterday], Object.keys(S.srs || {}).length + " words");
  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
