async page => {
  const FILE = globalThis.B1_FILE;
  const K = "b1VocabStories_v1";
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  const st = () => page.evaluate(k => JSON.parse(localStorage.getItem(k) || "{}"), K);
  const n = o => Object.keys(o || {}).length;
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  let S = await st();
  ok("a new browser has no progress, so a shared copy starts empty", !n(S.read) && !n(S.srs) && !!(await page.$("#hideWelcome")));

  await page.click("#hideWelcome");
  await page.click('.sizes button[data-size="2"]');
  await page.click("#bToc");
  await page.click('.toc li[data-n="05"]');
  await page.click('.vsw [data-ver="l"]');
  await page.click("#mark");
  await page.click("#bDay");
  const sizeBefore = (await st()).plan.size;
  await page.click('.task[data-t="w"]');
  if (await page.$("#wShow")) await page.click("#wShow");
  if (await page.$("#wBad")) await page.click("#wBad");
  const today = await page.evaluate(() => { const d = new Date(); return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); });
  await page.evaluate(([k, t]) => {
    const S = JSON.parse(localStorage.getItem(k));
    S.quiz = S.quiz || {}; S.quiz["05"] = { r: [1, 1, 0] };
    S.plan = S.plan || {}; S.plan.log = S.plan.log || {}; S.plan.log[t] = Object.assign(S.plan.log[t] || {}, { wd: 1 });
    S.hres = S.hres || {}; S.hres.U1 = { r: [1, 0], d: t };
    S.mails = S.mails || {}; S.mails.M01 = { t: "Hallo Lena", done: true, d: t };
    localStorage.setItem(k, JSON.stringify(S));
  }, [K, today]);
  await page.reload();
  S = await st();
  ok("there is progress to reset", S.read["05"] === true && n(S.srs) > 0 && !!S.plan.log[today] && !!S.hres.U1 && !!S.mails.M01, "srs " + n(S.srs));

  await page.click("#bToc");
  ok("Themen ends with a reset link", !!(await page.$("a.toReset")));
  await page.click("a.toReset");
  const page1 = await page.$eval("article.reset", e => e.textContent);
  ok("the reset page has its own address and lists what is saved, in correct German", (await page.evaluate(() => location.hash)) === "#/zuruecksetzen" && /1 gelesener Text, 1 Quiz-Ergebnis, \d+ (Wort|Wörter) zum Üben, 1 Lerntag\./.test(page1), page1.slice(0, 160));
  ok("it offers a backup first and has no reset link of its own", !!(await page.$("article.reset #saveProg")) && !(await page.$("article.reset a.toReset")));

  await page.evaluate(() => { window.__asked = ""; window.confirm = m => { window.__asked = m; return false; }; });
  await page.click("#resetPlan");
  S = await st();
  ok("it asks before deleting, and Abbrechen keeps everything", /wirklich/.test(await page.evaluate(() => window.__asked)) && n(S.srs) > 0 && !!S.plan.log[today]);
  await page.evaluate(() => { window.__asked = ""; window.confirm = m => { window.__asked = m; return true; }; });
  await page.click("#resetPlan");
  S = await st();
  ok("„Nur den Tagesplan“ clears words, listening, writing and the day log", !n(S.srs) && !n(S.look) && !n(S.plan.log) && !n(S.hres) && !n(S.mails), JSON.stringify({ srs: n(S.srs), log: n(S.plan.log), hres: n(S.hres), mails: n(S.mails) }));
  ok("… and keeps read texts, quiz results and the chosen day length", S.read["05"] === true && !!S.quiz["05"] && S.welcomed === true && S.plan.size === sizeBefore, "size " + S.plan.size + "/" + sizeBefore);
  ok("… then shows Heute", !!(await page.$(".day .tasks")) && (await page.evaluate(() => location.hash)) === "#/heute");

  await page.goto(FILE + "#/zuruecksetzen");
  await page.reload();
  ok("a reload keeps the reset page", !!(await page.$("article.reset")));
  await page.click("article.reset a.toDay");
  ok("Abbrechen on the page goes to Heute", !!(await page.$(".day .tasks")));
  await page.goBack();
  ok("Back returns to the reset page", !!(await page.$("article.reset")));

  await page.evaluate(() => { window.__asked = ""; window.confirm = m => { window.__asked = m; return false; }; });
  await page.click("#resetAll");
  ok("Abbrechen in the dialog keeps everything", (await st()).read["05"] === true);
  await page.evaluate(() => { window.__asked = ""; window.confirm = m => { window.__asked = m; return true; }; });
  await Promise.all([page.waitForEvent("load"), page.click("#resetAll")]);
  S = await st();
  ok("„Alles zurücksetzen“ deletes all progress", !n(S.read) && !n(S.quiz) && !S.welcomed, JSON.stringify(S).slice(0, 120));
  ok("… and the page starts like new on Heute, with the welcome line", (await page.evaluate(() => location.hash)) === "#/heute" && !!(await page.$("#hideWelcome")));
  await page.click("#bHelp");
  ok("Hilfe explains the reset and links to it", /Fortschritt zurücksetzen/.test(await page.$eval("article", e => e.textContent)) && !!(await page.$("article a.toReset")));
  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
