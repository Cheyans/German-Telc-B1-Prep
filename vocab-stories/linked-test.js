async page => {
  const FILE = globalThis.B1_FILE;
  const K = "b1VocabStories_v1";
  const out = [];
  const ok = (name, cond, extra) => out.push((cond ? "PASS " : "FAIL ") + name + (extra ? " | " + extra : ""));
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(FILE);
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  const D = await page.evaluate(() => { const d = JSON.parse(document.getElementById("data").textContent); return { built: d.hoeren.map(h => [h.id, h.items.length]), linked: (d.hlinked || []).map(x => x.id) }; });
  const today = await page.evaluate(() => { const d = new Date(); return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); });
  const st = () => page.evaluate(k => JSON.parse(localStorage.getItem(k) || "{}"), K);
  const seed = (doneLinked) => page.evaluate(([k, built, linked, t]) => {
    const S = { v: 2, read: {}, en: false, last: null, quiz: {}, syn: false, drill: {}, ver: {}, pread: {}, pq: {}, welcomed: true, srs: {}, look: {}, plan: {}, hres: {}, mails: {} };
    built.forEach(([id, n]) => { S.hres[id] = { r: Array(n).fill(1), d: "2026-11-01" }; });
    linked.forEach(id => { S.hres[id] = { s: null, n: null, d: "2026-11-02", x: 1 }; });
    localStorage.setItem(k, JSON.stringify(S));
  }, [K, D.built, doneLinked, today]);
  const hRow = async () => { await page.goto(FILE + "#/heute"); await page.reload(); return (await page.$eval('.task[data-t="h"]', e => e.textContent)).replace(/\s+/g, " "); };
  const body = () => page.$eval("article.hz", e => e.textContent.replace(/\s+/g, " "));

  ok("the file has 114 linked listening tasks after the 23 built-in ones", D.built.length === 23 && D.linked.length === 114, D.built.length + " + " + D.linked.length);
  ok("a new learner still starts with the built-in tasks", /Übungsbuch|Testbuch|Track|Modelltest/.test(await hRow()) && !/Deine Deutschprüfung/.test(await hRow()));

  await seed([]);
  let row = await hRow();
  ok("after the 23 built-in tasks, Hören goes on with the DW preparation", /DW: Deine Deutschprüfung B1 · Vorbereitung: Hören Teil 1/.test(row), row.slice(0, 120));
  await page.click('.task[data-t="h"]');
  ok("the task has its own address", (await page.evaluate(() => location.hash)) === "#/hoeren/DWV1");
  const dwHref = await page.$eval("article.hz .lsteps a", a => a.href + "|" + a.target);
  ok("it links to the exact DW exercise in a new tab", dwHref.startsWith("https://learngerman.dw.com/de/teil-1-die-aufgabe-lesen/l-73044718/e-73045091") && dwHref.endsWith("|_blank"), dwHref);
  ok("an online task has no score box, only Fertig", !(await page.$("#lsc")) && !!(await page.$("#ldone")));
  await page.click("#ldone");
  let S = await st();
  ok("Fertig saves the task and marks Hören done today", !!S.hres.DWV1 && S.hres.DWV1.d === today && S.plan.log[today].h === "DWV1", JSON.stringify(S.hres.DWV1));
  ok("then it shows ✓ and the Weiter bar", /✓ Gemacht/.test(await page.$eval("#lmsg", e => e.textContent)) && !!(await page.$(".nextbar")));
  await page.evaluate(([k, t]) => { const S = JSON.parse(localStorage.getItem(k)); S.plan.log["2026-11-10"] = S.plan.log[t]; delete S.plan.log[t]; localStorage.setItem(k, JSON.stringify(S)); }, [K, today]);
  row = await hRow();
  ok("the next day brings the next linked task", /Vorbereitung: Hören Teil 2/.test(row), row.slice(0, 120));

  await seed(["DWV1", "DWV2", "DWV3"]);
  row = await hRow();
  ok("after the DW preparation comes the free telc test", /telc Deutsch B1 · Übungstest 1: Hörverstehen Teil 1/.test(row), row.slice(0, 120));
  await page.click('.task[data-t="h"]');
  let t = await body();
  ok("the telc task gives the questions page, the audio window, the key and the transcripts", /Aufgaben 41 bis 45/.test(t) && /Seite 16/.test(t) && /telc_deutsch_b1_zd_uebungstest_4\.mp3/.test(t) && /von 0:00 bis 5:40/.test(t) && /Seite 43/.test(t) && /Seite 44/.test(t), t.slice(0, 300));
  ok("Teil 1 says the texts play only once", /nur einmal/.test(t));
  const get = await page.$eval("article.hz details.pbox", d => ({ open: d.open, href: (d.querySelector("a.btn") || {}).href }));
  ok("the download step is open for the first task of a test and links the official ZIP", get.open && get.href === "https://www.telc.net/fileadmin/user_upload/mock_exams/Deutsch/telc_deutsch_b1.zip", JSON.stringify(get));
  await page.fill("#lsc", "4");
  await page.click("#ldone");
  S = await st();
  ok("the score is saved", S.hres.TB1 && S.hres.TB1.s === 4 && S.hres.TB1.n === 5, JSON.stringify(S.hres.TB1));
  ok("and shown with the percentage", /4 von 5 \(80 %\)/.test(await page.$eval("#lmsg", e => e.textContent)));
  await page.goto(FILE + "#/hoeren/TB2");
  await page.reload();
  t = await body();
  ok("Teil 2 continues in the same file and says it plays twice", /von 5:40 bis 15:10/.test(t) && /zweimal/.test(t), t.slice(0, 200));
  ok("the download step is folded once the files are there", !(await page.$eval("article.hz details.pbox", d => d.open)));
  await page.fill("#lsc", "12");
  await page.click("#ldone");
  S = await st();
  ok("a score above the maximum is capped", S.hres.TB2.s === 10, JSON.stringify(S.hres.TB2));

  await page.goto(FILE + "#/hoeren/G1E2");
  await page.reload();
  const g = await page.$$eval("article.hz .lsteps a", l => l.map(a => a.href));
  t = await body();
  ok("a Goethe task links the PDF and opens the audio at the right minute", g.some(h => h === "https://www.goethe.de/pro/relaunch/prf/materialien/B1/b1_modellsatz_erwachsene.pdf") && g.some(h => /pruefungstraining_1_hoeren_b1_erwachsene\.mp4#t=640,909$/.test(h)), g.join(" "));
  ok("… with its own pages and play rule", /Seite 19/.test(t) && /Seite 33/.test(t) && /nur einmal/.test(t));
  const list = await page.$eval("article.hz", a => { const d = [...a.querySelectorAll("details.hlist")].map(x => x.querySelector("summary").textContent); const open = [...a.querySelectorAll("details.hgroup[open] summary")].map(x => x.textContent); return { d, open }; });
  ok("the list shows the linked tasks by test, with the current test open", list.d.some(s => /Mehr Hören/.test(s) && /von 114/.test(s)) && list.open.length === 1 && /Prüfungstraining 1 \(Erwachsene\)/.test(list.open[0]), JSON.stringify(list));

  await seed(D.linked);
  row = await hRow();
  ok("after all 114, there is still a task: DW Top-Thema", /Top-Thema/.test(row), row.slice(0, 120));
  await page.click('.task[data-t="h"]');
  ok("it has a dated id and links to Top-Thema", (await page.evaluate(() => location.hash)) === "#/hoeren/TT-" + today && (await page.$eval("article.hz .lsteps a", a => a.href)).startsWith("https://learngerman.dw.com/de/top-thema/"));
  await page.click("#ldone");
  S = await st();
  ok("doing it marks today done", S.plan.log[today].h === "TT-" + today && !!S.hres["TT-" + today]);
  await page.reload();
  ok("a reload keeps the Top-Thema task open", /Top-Thema/.test(await body()));

  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
