async page => {
  const FILE = globalThis.B1_FILE;
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.goto(FILE);
  const where = () => page.evaluate(() => ({
    hash: location.hash, len: history.length,
    day: !!document.querySelector(".day .tasks"), toc: !!document.querySelector(".toc"),
    title: (document.querySelector("article h2") || {}).textContent || "",
    y: Math.round(window.scrollY)
  }));
  let w = await where();
  ok("the start page is Heute and has its own address", w.day && w.hash === "#/heute", w.hash);
  const lenStart = w.len;
  await page.click("#bDay");
  ok("clicking the page you are on adds no history step", (await where()).len === lenStart);

  await page.click("#bToc");
  w = await where();
  ok("Themen gets #/themen", w.toc && w.hash === "#/themen", w.hash);
  await page.click('.toc li[data-n="05"]');
  w = await where();
  ok("a story gets #/story/05/…", /^#\/story\/05\/[lp]$/.test(w.hash), w.hash);
  const lenStory = w.len;
  await page.click('.vsw [data-ver="l"]');
  w = await where();
  ok("switching to Leicht replaces the step instead of adding one", w.hash === "#/story/05/l" && w.len === lenStory, w.hash + " " + w.len + "/" + lenStory);

  await page.goBack();
  w = await where();
  ok("Back goes from the story to Themen", w.toc && w.hash === "#/themen", w.hash);
  await page.goBack();
  w = await where();
  ok("Back again goes to Heute", w.day && w.hash === "#/heute", w.hash);
  await page.goForward();
  w = await where();
  ok("Forward goes to Themen", w.toc, w.hash);
  await page.goForward();
  w = await where();
  ok("Forward again opens the story in the version you left", w.hash === "#/story/05/l" && /Beim Arzt/.test(w.title), w.hash + " " + w.title);
  await page.reload();
  w = await where();
  ok("a reload keeps the story open", w.hash === "#/story/05/l" && /Beim Arzt/.test(w.title), w.hash);

  await page.click("#bToc");
  await page.evaluate(() => window.scrollTo(0, 900));
  await page.waitForTimeout(100);
  const y0 = (await where()).y;
  await page.evaluate(() => document.querySelector('.toc li[data-n="20"]').click());
  ok("opening a story starts at the top", (await where()).y === 0);
  await page.goBack();
  await page.waitForTimeout(150);
  w = await where();
  ok("Back to Themen restores the scroll position", w.toc && Math.abs(w.y - y0) < 60, "was " + y0 + ", now " + w.y);

  await page.click("#bDay");
  await page.click('.task[data-t="h"]');
  w = await where();
  ok("a listening task gets #/hoeren/…", /^#\/hoeren\/\w+$/.test(w.hash), w.hash);
  await page.goBack();
  w = await where();
  ok("Back from listening goes to Heute", w.day && w.hash === "#/heute", w.hash);

  await page.click('.task[data-t="w"]');
  const lenWords = (await where()).len;
  if (await page.$("#wShow")) await page.click("#wShow");
  if (await page.$("#wBad")) await page.click("#wBad");
  w = await where();
  ok("word cards don't add history steps", w.hash === "#/woerter" && w.len === lenWords, w.hash + " " + w.len + "/" + lenWords);
  await page.goBack();
  ok("Back from the word review goes to Heute", (await where()).day);

  await page.click("#bIdx");
  await page.fill("#search", "Arzt");
  await page.waitForTimeout(100);
  await page.click("#idx a");
  ok("a word-list link opens a story", /^#\/story\//.test((await where()).hash));
  await page.goBack();
  ok("Back returns to the word list with the search still filled in", (await page.$eval("#search", e => e.value)) === "Arzt" && (await where()).hash === "#/wortliste");

  await page.click("#bSyn");
  await page.click("#drillGo");
  ok("the Satzbau drill gets #/satzbau/uebung", (await where()).hash === "#/satzbau/uebung");
  await page.goBack();
  ok("Back from the drill goes to the Satzbau page", (await where()).hash === "#/satzbau" && !!(await page.$("#drillGo")));

  await page.click("#bHelp");
  await page.goBack();
  ok("Back from Hilfe goes to the page before", (await where()).hash === "#/satzbau");
  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
