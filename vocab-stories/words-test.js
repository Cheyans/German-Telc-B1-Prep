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
  const info = await page.evaluate(() => {
    const D = JSON.parse(document.getElementById("data").textContent);
    const sets = D.stories.map(s => s.n).filter(n => D.pq[n]);
    const b1 = Object.keys(D.words).filter(k => D.words[k].l === "B1");
    const inSet = n => b1.filter(k => (D.words[k].ps || []).indexOf(n) >= 0);
    const d = new Date();
    return { sets, set1: inSet(sets[0]), set2: inSet(sets[1]), ps: Object.fromEntries(b1.map(k => [k, D.words[k].ps || []])), t: Math.round(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000) };
  });
  const seed = (keys, doneSets) => page.evaluate(([k, keys, doneSets, t]) => {
    const S = { v: 2, read: {}, en: false, last: null, quiz: {}, syn: false, drill: {}, ver: {}, pread: {}, pq: {}, welcomed: true, srs: {}, look: {}, plan: {}, hres: {}, mails: {} };
    keys.forEach(id => { S.srs[id] = [3, t + 5, t - 10]; });
    doneSets.forEach(n => { S.pq[n] = { A: [1, 1, 1, 1, 1], B: [1, 1, 1, 1, 1] }; });
    localStorage.setItem(k, JSON.stringify(S));
  }, [K, keys, doneSets, info.t]);
  const wordsRow = async () => { await page.goto(FILE + "#/heute"); await page.reload(); return page.$eval('.task[data-t="w"]', e => e.textContent); };
  const learnAll = async () => {
    await page.click('.task[data-t="w"]');
    for (let i = 0; i < 12 && await page.$("#wShow"); i++) { await page.click("#wShow"); await page.click("#wGood"); }
    const S = await page.evaluate(k => JSON.parse(localStorage.getItem(k)), K);
    return Object.keys(S.srs).filter(id => S.srs[id][2] === info.t);
  };

  await seed(info.set1, []);
  let row = await wordsRow();
  ok("when every word of the next reading set is already in practice, new words still come", /5 neue/.test(row), row.replace(/\s+/g, " "));
  let fresh = await learnAll();
  ok("… and they come from the set after it", fresh.length === 5 && fresh.every(id => info.ps[id].indexOf(info.sets[1]) >= 0), fresh.join(" "));

  await seed([], info.sets);
  row = await wordsRow();
  ok("after all reading sets are done, new words still come", /5 neue/.test(row), row.replace(/\s+/g, " "));
  fresh = await learnAll();
  ok("… starting again with the first set", fresh.length === 5 && fresh.every(id => info.ps[id].indexOf(info.sets[0]) >= 0), fresh.join(" "));

  await seed([], [info.sets[0]]);
  row = await wordsRow();
  fresh = await learnAll();
  ok("with reading on track, new words come from the next reading set, as before", /5 neue/.test(row) && fresh.length === 5 && fresh.every(id => info.ps[id].indexOf(info.sets[1]) >= 0), fresh.join(" "));

  ok("no page errors", errors.length === 0, errors.join(" | "));
  return out.join("\n");
}
