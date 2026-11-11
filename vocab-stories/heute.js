  var DAY_SIZES = [
    { lab: "50 Min", tip: "Alle vier: Wörter, Hören, Lesen, Schreiben", t: ["w", "h", "l", "s"] },
    { lab: "30 Min", tip: "Wörter, Hören, Schreiben", t: ["w", "h", "s"] },
    { lab: "15 Min", tip: "Wörter und Hören", t: ["w", "h"] },
    { lab: "5 Min", tip: "Nur Wörter üben", t: ["w"] }
  ];
  var TASK_NAMES = { w: "Wörter üben", h: "Hören", l: "Lesen", s: "Schreiben" };
  var TASK_DONE = { w: "wd", h: "h", l: "l", s: "s" };
  var BOX_DAYS = [0, 1, 3, 7, 14, 30, 60];
  var NEW_PER_DAY = 5, MAX_REVIEWS = 30, NO_NEW_ABOVE = 40;
  var TRAPS = {
    when: "plan vs. done, or the wrong day or time",
    who: "the right fact, but the wrong person",
    number: "a number, time, price or place",
    change: "a correction or a change of plan",
    flip: "aber, trotzdem, doch: the sentence turns",
    overstate: "immer, nur, alle, vor allem",
    negation: "nicht or kein comes late in the sentence",
    paraphrase: "the same meaning in other words",
    "same-word": "the same word, but a different claim"
  };
  var fromDay = false, sess = null;

  function ymd(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2); }
  function todayStr() { return ymd(new Date()); }
  function dayNum(s) { var p = s.split("-"); return Math.round(Date.UTC(+p[0], +p[1] - 1, +p[2]) / 86400000); }
  function today() { return dayNum(todayStr()); }
  function plan() {
    if (!state.plan || typeof state.plan !== "object") state.plan = {};
    if (!state.plan.log) state.plan.log = {};
    if (typeof state.plan.size !== "number" || !DAY_SIZES[state.plan.size]) state.plan.size = 0;
    return state.plan;
  }
  function logOf(d) { var p = plan(); if (!p.log[d]) p.log[d] = {}; return p.log[d]; }
  function markDone(t, val) { var L = logOf(todayStr()); L[TASK_DONE[t]] = val; L.size = plan().size; save(); askPersist(); }
  function activeDays() { var L = plan().log; return Object.keys(L).filter(function (d) { var x = L[d]; return x.wd || x.h || x.l || x.s; }); }
  function studyDayNo() { var a = activeDays(); return a.length + (a.indexOf(todayStr()) >= 0 ? 0 : 1); }
  function backLink() { return '<div class="dayback"><a href="#" class="toDay">← Heute</a></div>'; }
  function wireBack() { each(main.querySelectorAll(".toDay:not([data-w])"), function (a) { a.setAttribute("data-w", "1"); a.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); showDay(); }); }); }
  var TASK_MIN = { w: "5 bis 10 Min", h: "10 bis 15 Min", l: "10 bis 15 Min" };
  function taskMin(t) { if (t === "s") { var M = mailToday(); return M && M.kind === "full" ? "30 Min" : "10 Min"; } return TASK_MIN[t]; }
  function nextTask() {
    var p = plan(), L = p.log[todayStr()] || {}, ts = DAY_SIZES[p.size].t;
    for (var i = 0; i < ts.length; i++) if (!L[TASK_DONE[ts[i]]]) return ts[i];
    return null;
  }
  function openTask(t) { if (t === "w") startWords(); else if (t === "h") showHoeren((plan().log[todayStr()] || {}).h); else if (t === "l") openLesen(); else showMail(); }
  function nextBar(top) {
    var t = nextTask();
    if (!t) return '<div class="nextbar"><span class="alldone">Heute alles geschafft ✓</span>' + (top ? "" : ' <a href="#" class="toDay">Zurück zu Heute</a>') + "</div>";
    return '<div class="nextbar"><button class="primary goNext" data-t="' + t + '">Weiter: ' + TASK_NAMES[t] + " (" + taskMin(t) + ") →</button>" + (top ? "" : ' <a href="#" class="toDay">Schluss für heute</a>') + "</div>";
  }
  function wireNext() { each(main.querySelectorAll(".goNext:not([data-w])"), function (b) { b.setAttribute("data-w", "1"); b.addEventListener("click", function (ev) { ev.stopPropagation(); openTask(b.getAttribute("data-t")); }); }); wireBack(); }
  function addNextBar(after) { var d = document.createElement("div"); d.innerHTML = nextBar(false); var el = d.firstChild; if (after && after.parentNode) after.parentNode.insertBefore(el, after.nextSibling); else main.querySelector("article").appendChild(el); wireNext(); }

  function cardInfo(key) {
    if (key.indexOf("o:") === 0) {
      var o = (DATA.off || {})[key.slice(2)];
      return o ? { de: o.d, head: o.d, en: o.g, lvl: "" } : null;
    }
    var w = DATA.words[key];
    return w ? { de: w.d, head: w.d.split(",")[0], en: w.g, lvl: w.l } : null;
  }
  function offKey(form) {
    var O = DATA.off || {}, c = [form, form.toLowerCase(), form.charAt(0).toUpperCase() + form.slice(1)];
    for (var i = 0; i < c.length; i++) if (O[c[i]]) return c[i];
    return null;
  }
  function srsKeyFor(el, form) {
    if (el.classList.contains("p") || el.classList.contains("gw") || el.hasAttribute("data-k")) return null;
    if (el.classList.contains("n")) {
      var k = offKey(form), o = k ? DATA.off[k] : null;
      if (!o) return null;
      if (o.id && DATA.words[o.id]) return o.id;
      return o.k === "word" ? "o:" + k : null;
    }
    var ids = el.getAttribute("data-id");
    if (!ids || el.getAttribute("data-f") === "c") return null;
    var id = ids.split(",")[0];
    return DATA.words[id] ? id : null;
  }
  function starLabel(k) { var e = state.srs[k]; return !e ? "☆ Merken" : e[0] === 0 ? "★ Gemerkt" : "★ Wird geübt"; }
  function starHtml(k) { return '<div class="starrow"><button class="small star' + (state.srs[k] ? " on" : "") + '" data-sk="' + esc(k) + '">' + starLabel(k) + "</button></div>"; }
  function noteLookup(k) { if (!state.srs[k]) { state.look[k] = today(); save(); } }
  function wireStar(box) {
    var b = box.querySelector(".star");
    if (!b) return;
    b.addEventListener("click", function (ev) {
      ev.stopPropagation();
      var k = b.getAttribute("data-sk"), e = state.srs[k], t = today();
      if (!e) state.srs[k] = [0, t, t];
      else if (e[0] === 0) delete state.srs[k];
      save();
      b.textContent = starLabel(k);
      b.classList.toggle("on", !!state.srs[k]);
    });
  }

  var exCache = {};
  function sentenceAround(text, at, len) {
    var s = 0, e = text.length, i;
    for (i = at - 1; i > 0; i--) if (/[.!?]/.test(text.charAt(i)) && /\s/.test(text.charAt(i + 1))) { s = i + 2; break; }
    for (i = at + len; i < text.length; i++) if (/[.!?]/.test(text.charAt(i))) { e = i + 1; if (/[“”«»"]/.test(text.charAt(e))) e++; break; }
    if (e - s > 240) { s = Math.max(s, at - 100); e = Math.min(e, at + len + 100); }
    return [s, e];
  }
  function exampleFor(key) {
    if (exCache[key] !== undefined) return exCache[key];
    var off = key.indexOf("o:") === 0, form = off ? key.slice(2) : "", res = "";
    var re = off ? new RegExp("(^|[^A-Za-zÄÖÜäöüß])(" + form.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + ")(?![A-Za-zÄÖÜäöüß])", "i") : null;
    search:
    for (var i = 0; i < DATA.stories.length; i++) {
      var ps = DATA.stories[i].p;
      for (var j = 0; j < ps.length; j++) {
        var text = "", at = -1, len = 0;
        ps[j].forEach(function (sg) {
          if (typeof sg === "string") {
            if (off && at < 0) { var m = re.exec(sg); if (m) { at = text.length + m.index + m[1].length; len = m[2].length; } }
            text += sg;
          } else {
            if (!off && at < 0 && sg[1] && sg[1].split(",").indexOf(key) >= 0) { at = text.length; len = sg[0].length; }
            text += sg[0];
          }
        });
        if (at >= 0) {
          var r = sentenceAround(text, at, len);
          var snip = text.slice(r[0], r[1]), open = (snip.match(/„/g) || []).length - (snip.match(/“/g) || []).length;
          res = (r[0] > 0 && text.charAt(r[0] - 1) !== " " ? "…" : "") + esc(text.slice(r[0], at)) + "<b>" + esc(text.slice(at, at + len)) + "</b>" + esc(text.slice(at + len, r[1])) + (open > 0 ? " …“" : "");
          break search;
        }
      }
    }
    exCache[key] = res;
    return res;
  }

  function srsDue(t) {
    return Object.keys(state.srs).filter(function (k) { var e = state.srs[k]; return e[0] >= 1 && e[1] <= t && cardInfo(k); })
      .sort(function (a, b) { return state.srs[a][1] - state.srs[b][1] || state.srs[a][0] - state.srs[b][0]; });
  }
  function lesenNext() {
    for (var i = 0; i < DATA.stories.length; i++) {
      var n = DATA.stories[i].n;
      if (!DATA.pq[n]) continue;
      var r = state.pq[n] || {};
      if (!r.A) return { n: n, part: "A" };
      if (!r.B) return { n: n, part: "B" };
    }
    return null;
  }
  function newCandidates(limit) {
    var out = [], seen = {};
    function add(k) { if (out.length < limit && !seen[k] && cardInfo(k)) { seen[k] = 1; out.push(k); } }
    Object.keys(state.srs).filter(function (k) { return state.srs[k][0] === 0; })
      .sort(function (a, b) { return state.srs[a][2] - state.srs[b][2]; }).forEach(add);
    Object.keys(state.look).filter(function (k) { return !state.srs[k]; })
      .sort(function (a, b) { return state.look[b] - state.look[a]; }).forEach(add);
    var ln = lesenNext(), sets = DATA.stories.map(function (s) { return s.n; }).filter(function (n) { return DATA.pq[n]; });
    var from = ln ? Math.max(0, sets.indexOf(ln.n)) : 0, ids = Object.keys(DATA.words);
    for (var i = 0; i < sets.length && out.length < limit; i++) {
      var n = sets[(from + i) % sets.length];
      for (var j = 0; j < ids.length && out.length < limit; j++) { var w = DATA.words[ids[j]]; if (w.l === "B1" && !state.srs[ids[j]] && (w.ps || []).indexOf(n) >= 0) add(ids[j]); }
    }
    return out;
  }
  function wordsPlan() {
    var t = today(), L = (plan().log[todayStr()] || {}), due = srsDue(t);
    var room = due.length > NO_NEW_ABOVE ? 0 : Math.max(0, NEW_PER_DAY - (L.wn || 0));
    return { due: due.slice(0, MAX_REVIEWS), dueAll: due.length, fresh: newCandidates(room) };
  }

  function startWords() {
    var wp = wordsPlan();
    sess = { q: wp.due.map(function (k) { return { k: k, m: "rev" }; }).concat(wp.fresh.map(function (k) { return { k: k, m: "new" }; })), i: 0, open: false, r: 0, ok: 0, n: 0, again: {} };
    showWords();
  }
  function wordsSummary() {
    var h = '<div class="wsum"><b>Fertig für heute.</b> ' + (sess.r ? sess.r + " wiederholt (" + sess.ok + " gewusst)" : "Keine Wiederholungen fällig") + (sess.n ? ", " + sess.n + (sess.n === 1 ? " neues Wort." : " neue Wörter.") : ".") + "</div>";
    var total = Object.keys(state.srs).filter(function (k) { return state.srs[k][0] < 6 || state.srs[k][1] - today() < 365; }).length;
    h += '<p class="hint">Du übst jetzt ' + total + (total === 1 ? " Wort." : " Wörter.") + " Neue Wörter kommen von ☆ Merken auf einer Wortkarte, von Wörtern, die du beim Lesen nachgeschlagen hast, und aus den nächsten Lesetexten.</p>";
    if (total) h += '<p><button class="small" id="anki">Für Anki exportieren</button></p>';
    return h;
  }
  function showWords() {
    setRoute("#/woerter");
    current = null; hideCard(); setNav("bDay");
    var h = '<article class="wz">' + backLink() + "<h2>Wörter üben</h2>", done = false;
    if (!sess || !sess.q.length) {
      h += '<p class="hint">Heute gibt es nichts zu wiederholen und keine neuen Wörter. Tippe beim Lesen auf Wörter oder klicke auf einer Wortkarte auf ☆ Merken. Dann kommen sie hierher.</p>';
      if (!(plan().log[todayStr()] || {}).wd) markDone("w", { r: 0, n: 0 });
      h += wordsSummary(); done = true;
    } else if (sess.i >= sess.q.length) {
      markDone("w", { r: sess.r, n: sess.n });
      h += wordsSummary(); done = true;
    } else {
      var c = sess.q[sess.i], info = cardInfo(c.k), e = state.srs[c.k], prod = c.m === "rev" && e && e[0] >= 3;
      if (sess.undo) h += '<div class="undo">„' + esc(sess.undo.head) + '“ wird nicht mehr geübt. <a href="#" id="wUndo">Rückgängig</a></div>';
      h += '<div class="sub">Karte ' + (sess.i + 1) + " von " + sess.q.length + (c.m === "new" ? " · neues Wort" : c.m === "again" ? " · noch einmal" : " · Wiederholung") + "</div>";
      h += '<div class="wcard"><div class="wfront">' + esc(prod ? info.en : info.head) + "</div>";
      if (!sess.open) h += '<div class="wask">' + (prod ? "Wie heißt das auf Deutsch? Mit Artikel und Plural, wenn es ein Nomen ist." : "Was bedeutet das? Denk zuerst nach.") + '</div><div class="wbtns"><button id="wShow">Zeigen</button></div>';
      else {
        var ex = exampleFor(c.k);
        h += '<div class="wback">' + (info.lvl ? '<span class="lvl lvl-' + info.lvl + '">' + lvlName(info.lvl) + "</span> " : "") + '<span class="dict">' + esc(info.de) + '</span><div class="en">' + esc(info.en) + "</div>" + (ex ? '<div class="wex">' + ex + "</div>" : "") + "</div>";
        h += '<div class="wbtns">' + (c.m === "new"
          ? '<button id="wBad">Neu für mich <span class="key">1</span></button><button id="wGood">Kenne ich schon <span class="key">2</span></button>'
          : c.m === "again" ? '<button id="wGood">Weiter <span class="key">2</span></button>'
          : '<button id="wBad">Nicht gewusst <span class="key">1</span></button><button id="wGood">Gewusst <span class="key">2</span></button>') + "</div>";
      }
      h += "</div>";
      h += '<p class="hint"><span class="keys">Tasten: Leertaste zeigt, 1 und 2 antworten. </span>' + (c.m === "rev" || c.m === "new" ? '<a href="#" id="wDrop">Dieses Wort nicht mehr üben</a>' : "") + "</p>";
    }
    h += "</article>";
    main.innerHTML = h;
    wireBack();
    if (done) addNextBar(main.querySelector(".wsum"));
    var a = document.getElementById("anki");
    if (a) a.addEventListener("click", function (ev) { ev.stopPropagation(); exportAnki(); });
    var sh = document.getElementById("wShow");
    if (sh) sh.addEventListener("click", function (ev) { ev.stopPropagation(); sess.open = true; showWords(); });
    var g = document.getElementById("wGood"), bd = document.getElementById("wBad"), dr = document.getElementById("wDrop"), un = document.getElementById("wUndo");
    if (g) g.addEventListener("click", function (ev) { ev.stopPropagation(); gradeWord(true); });
    if (bd) bd.addEventListener("click", function (ev) { ev.stopPropagation(); gradeWord(false); });
    if (dr) dr.addEventListener("click", function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      var c = sess.q[sess.i];
      sess.undo = { k: c.k, m: c.m, prev: state.srs[c.k], look: state.look[c.k], head: (cardInfo(c.k) || {}).head || c.k, i: sess.i };
      state.srs[c.k] = [6, today() + 3650, today()]; delete state.look[c.k]; save();
      sess.i++; sess.open = false; showWords();
    });
    if (un) un.addEventListener("click", function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      var u = sess.undo; sess.undo = null;
      if (u.prev) state.srs[u.k] = u.prev; else delete state.srs[u.k];
      if (u.look !== undefined) state.look[u.k] = u.look;
      save();
      sess.i = u.i; sess.open = false; showWords();
    });
  }
  document.addEventListener("keydown", function (ev) {
    if (!sess || !main.querySelector(".wz") || ev.ctrlKey || ev.metaKey || ev.altKey) return;
    var tag = ev.target && ev.target.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || tag === "BUTTON" || tag === "A") return;
    var map = { " ": "wShow", Enter: "wShow", "1": "wBad", "2": "wGood" }, id = map[ev.key];
    var el = id && document.getElementById(id);
    if (el) { ev.preventDefault(); el.click(); }
  });
  function gradeWord(good) {
    var c = sess.q[sess.i], t = today(), e = state.srs[c.k] || [0, t, t], L = logOf(todayStr());
    if (c.m === "new") {
      state.srs[c.k] = good ? [4, t + BOX_DAYS[4], e[2] || t] : [1, t + 1, e[2] || t];
      if (!good) sess.q.push({ k: c.k, m: "again" });
      delete state.look[c.k];
      sess.n++; L.wn = (L.wn || 0) + 1;
    } else if (c.m === "rev") {
      var nb = good ? Math.min(6, e[0] + 1) : 1;
      state.srs[c.k] = [nb, t + BOX_DAYS[nb], e[2] || t];
      if (!good) sess.q.push({ k: c.k, m: "again" });
      sess.r++; if (good) sess.ok++;
    }
    save();
    sess.i++; sess.open = false; sess.undo = null;
    showWords();
  }
  function download(name, text, type) {
    var blob = new Blob([text], { type: type || "text/plain" }), a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  function exportAnki() {
    var rows = Object.keys(state.srs).map(function (k) {
      var c = cardInfo(k);
      if (!c) return null;
      var ex = exampleFor(k);
      return [c.de, esc(c.en) + (ex ? "<br><i>" + ex + "</i>" : ""), "b1-geschichten"].join("\t").replace(/\n/g, " ");
    }).filter(Boolean);
    download("b1-meine-woerter-" + todayStr() + ".txt", "#separator:tab\n#html:true\n#tags column:3\n" + rows.join("\n") + "\n");
  }

  var TT_URL = "https://learngerman.dw.com/de/top-thema/s-55861562";
  function hLinked() { return DATA.hlinked || []; }
  function isLinked(T) { return !!T && !!T.set && !!T.part; }
  function topThema(id) { return { id: id, src: "dw", set: "DW: Top-Thema mit Vokabeln", part: "Die neueste Folge", what: "Nachrichten mit Fragen", do: "Hör die neueste Folge, oder eine, die du noch nicht kennst, und mach die Fragen dazu.", url: TT_URL, go: "Top-Thema öffnen", min: 10 }; }
  function hoerenById(id) {
    var H = (DATA.hoeren || []).concat(hLinked());
    for (var i = 0; i < H.length; i++) if (H[i].id === id) return H[i];
    return hLinked().length && /^TT-\d{4}-\d\d-\d\d$/.test(id || "") ? topThema(id) : null;
  }
  function hoerenNext() {
    var H = (DATA.hoeren || []).concat(hLinked());
    for (var i = 0; i < H.length; i++) if (!state.hres[H[i].id]) return H[i];
    return hLinked().length ? topThema("TT-" + todayStr()) : null;
  }
  function hTitle(T) { return T.head; }
  function hEv(it) {
    var tr = TRAPS[it.trap] ? '<div class="trap">Falle: ' + esc(TRAPS[it.trap]) + "</div>" : "";
    var w = (it.w || []).length ? '<div class="hw">' + it.w.map(function (x) { return "<b>" + esc(x[0]) + "</b> = " + esc(x[1]); }).join(" · ") + "</div>" : "";
    return '<div class="ev">' + (it.tr ? "Track " + esc(it.tr) + ", bei " : "Bei ") + "<b>" + esc(it.at) + "</b> im Audio: „" + esc(String(it.ev).replace(/^„|“$/g, "")) + "“</div>" + '<div class="why">' + esc(it.why) + "</div>" + tr + w;
  }
  function audioBtn(a, lab) { return '<a class="btn audio" href="' + esc(a.url) + '" target="_blank" rel="noopener">▶ ' + esc(lab) + " ↗</a>"; }
  function showHoeren(id) {
    var T = (id && hoerenById(id)) || hoerenNext();
    setRoute("#/hoeren" + (T ? "/" + T.id : ""));
    current = null; hideCard(); setNav("bDay");
    if (isLinked(T)) { showLinked(T); return; }
    var h = '<article class="hz">' + backLink();
    if (!T) {
      main.innerHTML = h + '<h2>Hören</h2><p class="hint">' + ((DATA.hoeren || []).length ? "Du hast alle Hörübungen gemacht. Sehr gut! Mach sie nach ein paar Wochen noch einmal, oder hör die Texte ohne Aufgaben, nur zum Verstehen." : "Noch keine Hörübungen in dieser Version.") + "</p>" + hoerenList() + "</article>";
      wireBack(); wireHList();
      return;
    }
    var prev = state.hres[T.id], U = T.book === "U";
    var read = U ? "Lies zuerst die Aussagen." : T.teil === 1 ? "Lies zuerst die Aussagen (in der Prüfung: 30 Sekunden)." : T.teil === 2 ? "Lies zuerst die Aussagen (in der Prüfung: eine Minute)." : "Lies vor jedem Text seine Aussagen.";
    var play = U ? "Dann hör jeden Track einmal ganz." : "Dann hör das Audio von <b>" + esc(T.from) + "</b> bis <b>" + esc(T.to) + "</b>" + (T.teil === 1 ? ", nur einmal und ohne Pause." : T.teil === 2 ? ". Das Gespräch kommt zweimal: Entscheide beim ersten Hören." : ". Jeder Text kommt zweimal: Entscheide beim ersten Hören.");
    h += "<h2>Hören · " + esc(T.head) + '</h2><div class="sub">' + esc(T.title) + (U ? "" : " · Testbuch S. " + T.page) + "</div>";
    h += '<div class="task"><p>' + esc(T.intro) + "</p></div>";
    h += '<p class="howto">' + read + " " + play + "</p>";
    if (!U) h += '<p class="abtns">' + audioBtn(T.audios[0], "Audio " + T.audios[0].n + " anhören") + "</p>";
    h += '<details class="pbox"><summary>So geht der Audio-Player</summary><p class="hint">Der Knopf öffnet allango.net in einem neuen Tab. Schließ dort zuerst das Cookie-Fenster, dann startest du mit ▶. Die Pfeile neben ▶ springen 10 Sekunden zurück oder vor, und rechts steht die Zeit. Das Audio gehört zu deinem Buch <i>' + (U ? "Mit Erfolg zum Zertifikat Deutsch B1, Übungsbuch" : "Mit Erfolg zu telc Deutsch B1, Testbuch") + "</i> (Klett). " + (U ? "Die Aussagen hier sind neu, nicht die Übungen aus dem Buch." : "Hast du diesen Hörtext im Buch noch nicht gemacht? Dann mach zuerst die Aufgaben im Buch, wie in der echten Prüfung. Die Aussagen hier sind neu und schwieriger.") + "</p></details>";
    h += '<section class="quiz" id="hq"><h3>Richtig oder falsch?</h3><p class="hint">' + EXAM_HINT + " Das Wichtige steht oft am Satzende.</p>" + lastHtml(prev && prev.r, T.items.length);
    var lastG = null;
    T.items.forEach(function (it, k) {
      var g = U ? it.tr : it.t;
      if (g && g !== lastG) {
        var a = U ? T.audios.filter(function (x) { return x.n === it.tr; })[0] : null;
        h += '<h4 class="htext">' + (U ? "Track " + esc(it.tr) + (a && a.name ? ": " + esc(a.name) : "") + (a ? " " + audioBtn(a, "Anhören" + (a.len ? " (" + a.len + ")" : "")) : "") : "Text " + g) + "</h4>";
        lastG = g;
      }
      h += '<div class="qq rq" data-k="' + k + '"><div class="qt"><b>' + (k + 1) + ".</b> " + esc(it.s) + '</div><div class="rfb"><button class="opt" data-rf="1">richtig</button><button class="opt" data-rf="0">falsch</button></div><div class="fb"></div></div>';
    });
    h += '<div class="score"></div></section>' + checkBar("hcheck") + hoerenList(T.id) + "</article>";
    main.innerHTML = h;
    wireBack(); wireHList();
    examQuiz(T.id, [{ sec: document.getElementById("hq"), kind: "rf", items: T.items, lab: "" }], document.getElementById("hcheck"), function (res) {
      state.hres[T.id] = { r: res[0], d: todayStr() };
      if (!(plan().log[todayStr()] || {}).h) markDone("h", T.id); else save();
      addNextBar(main.querySelector(".checkbar"));
    }, { ev: hEv, again: function () { showHoeren(T.id); } });
    window.scrollTo(0, 0);
  }
  function hoerenList(cur) {
    var H = DATA.hoeren || [], X = hLinked(), h = "";
    if (H.length) {
      h += '<details class="hlist"><summary>Hörübungen mit dem Klett-Audio (' + H.filter(function (T) { return state.hres[T.id]; }).length + " von " + H.length + " gemacht)</summary><ul>";
      H.forEach(function (T) {
        var r = state.hres[T.id];
        h += '<li><a href="#" data-h="' + T.id + '"' + (T.id === cur ? ' class="cur"' : "") + ">" + esc(hTitle(T)) + ": " + esc(T.title) + "</a>" + (r && r.r ? ' <span class="meta">' + total(r.r) + "/" + r.r.length + "</span>" : "") + "</li>";
      });
      h += "</ul></details>";
    }
    if (X.length) {
      var groups = [], done = function (T) { return !!state.hres[T.id]; };
      X.forEach(function (T) { var g = groups[groups.length - 1]; if (!g || g.set !== T.set) groups.push(g = { set: T.set, items: [] }); g.items.push(T); });
      h += '<details class="hlist"' + (X.some(function (T) { return T.id === cur; }) ? " open" : "") + "><summary>Mehr Hören von telc, ÖSD, Goethe und DW (" + X.filter(done).length + " von " + X.length + " gemacht)</summary>";
      groups.forEach(function (g) {
        h += '<details class="hgroup"' + (g.items.some(function (T) { return T.id === cur; }) ? " open" : "") + "><summary>" + esc(g.set) + ' <span class="meta">' + g.items.filter(done).length + "/" + g.items.length + "</span></summary><ul>"
          + g.items.map(function (T) { var r = state.hres[T.id]; return '<li><a href="#" data-h="' + T.id + '"' + (T.id === cur ? ' class="cur"' : "") + ">" + esc(T.part) + "</a>" + (r ? ' <span class="meta">' + (r.s != null && r.n ? r.s + "/" + r.n : "✓") + "</span>" : "") + "</li>"; }).join("") + "</ul></details>";
      });
      h += "</details>";
    }
    return h;
  }
  function linkA(url, lab) { return '<a class="btn audio" href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(lab) + " ↗</a>"; }
  function mmssSecs(x) { var p = String(x).split(":"); return +p[0] * 60 + +p[1]; }
  function doneText(r) { return "✓ Gemacht" + (r.s != null && r.n ? ": " + r.s + " von " + r.n + " (" + Math.round(100 * r.s / r.n) + " %)" : "") + "."; }
  function showLinked(T) {
    var prev = state.hres[T.id], X = hLinked();
    var first = !X.some(function (x) { return x.set === T.set && x.id !== T.id && state.hres[x.id]; });
    var h = '<article class="hz">' + backLink();
    h += "<h2>Hören · " + esc(T.set) + '</h2><div class="sub">' + esc(T.part) + (T.what ? " · " + esc(T.what) : "") + " · etwa " + T.min + " Minuten</div>";
    if (T.task) h += '<div class="task"><p>' + esc(T.task) + "</p></div>";
    var st = [];
    if (T.url) st.push(linkA(T.url, T.go || "Öffnen") + " " + esc(T.do || ""));
    else {
      st.push(T.pdf.url ? linkA(T.pdf.url, "PDF öffnen") + " Aufgaben " + esc(T.items) + " auf <b>Seite " + T.pdf.q + "</b>." : "Aufgaben " + esc(T.items) + " im PDF „" + esc(T.pdf.name) + "“ auf <b>Seite " + T.pdf.q + "</b>.");
      var a = T.audio, au = a.url ? linkA(a.url + "#t=" + mmssSecs(a.from) + "," + mmssSecs(a.to), "Audio öffnen") + " " : "Audio „" + esc(a.file) + "“ ";
      st.push(au + "von <b>" + esc(a.from) + "</b> bis <b>" + esc(a.to) + "</b>. " + (a.note ? esc(a.note) + " " : "") + (T.plays === 2 ? "Die Aufnahme spielt alles zweimal: Entscheide beim ersten Hören, prüf beim zweiten." : "Du hörst alles nur einmal, also ohne Pause durchhören.") + " Die Zeit zum Lesen ist schon in der Aufnahme.");
      st.push("Danach vergleichen: die Lösungen auf <b>Seite " + T.pdf.key + "</b>" + (T.pdf.tr ? ", die Hörtexte zum Nachlesen auf Seite " + T.pdf.tr : "") + ".");
    }
    h += '<ol class="lsteps">' + st.map(function (x) { return "<li>" + x + "</li>"; }).join("") + "</ol>";
    if (T.get) h += '<details class="pbox"' + (first && !prev ? " open" : "") + "><summary>Zuerst: die Dateien holen (nur einmal)</summary><p class=\"hint\">" + linkA(T.get, T.getlab || "Herunterladen") + " Entpacke die ZIP-Datei. Darin sind das PDF und " + (T.src === "osd" ? "drei MP3-Dateien, eine für jede Aufgabe" : "eine MP3-Datei") + '. Die Dateien sind gratis und kommen direkt von <a href="' + esc(T.page) + '" target="_blank" rel="noopener">' + (T.src === "telc" ? "telc.net" : "osd.at") + "</a>.</p></details>";
    else if (T.src === "goethe") h += '<p class="hint">Gratis vom Goethe-Institut (<a href="' + esc(T.page) + '" target="_blank" rel="noopener">goethe.de</a>). Das PDF und das Audio öffnen sich in einem neuen Tab, das Audio gleich an der richtigen Stelle.</p>';
    h += '<div class="lscore">' + (T.n ? '<label>Wie viele hast du richtig? <input type="number" id="lsc" min="0" max="' + T.n + '" inputmode="numeric"' + (prev && prev.s != null ? ' value="' + prev.s + '"' : "") + "> von " + T.n + "</label> " : "")
      + '<button class="primary" id="ldone">' + (prev ? "Speichern" : "Fertig") + '</button> <span class="hint" id="lmsg" role="status">' + (prev ? doneText(prev) : "") + "</span></div>";
    h += hoerenList(T.id) + "</article>";
    main.innerHTML = h;
    wireBack(); wireHList();
    document.getElementById("ldone").addEventListener("click", function (ev) {
      ev.stopPropagation();
      var inp = document.getElementById("lsc"), v = inp && inp.value !== "" ? Math.round(+inp.value) : null;
      if (v !== null && (isNaN(v) || !T.n)) v = null;
      if (v !== null) v = Math.max(0, Math.min(T.n, v));
      if (inp && v !== null) inp.value = v;
      state.hres[T.id] = { s: v, n: T.n || null, d: todayStr(), x: 1 };
      if (!(plan().log[todayStr()] || {}).h) markDone("h", T.id); else save();
      document.getElementById("lmsg").textContent = doneText(state.hres[T.id]);
      this.textContent = "Speichern";
      if (!main.querySelector(".nextbar")) addNextBar(main.querySelector(".lscore"));
    });
    window.scrollTo(0, 0);
  }
  function wireHList() { each(main.querySelectorAll(".hlist a[data-h]"), function (a) { a.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); showHoeren(a.getAttribute("data-h")); }); }); }

  function mailById(id) { var M = DATA.mail || []; for (var i = 0; i < M.length; i++) if (M[i].id === id) return M[i]; return null; }
  function mailNext(kind) { var M = DATA.mail || []; for (var i = 0; i < M.length; i++) { var x = state.mails[M[i].id]; if ((!kind || M[i].kind === kind) && !(x && x.done)) return M[i]; } return null; }
  function mailToday() { var L = plan().log[todayStr()] || {}; return (L.s && mailById(L.s)) || (L.sp && mailById(L.sp)) || mailNext(); }
  function mailTask(M) {
    return "Aufgabe (" + (M.kind === "full" ? "telc Deutsch B1, Schreiben, 30 Minuten" : "Mini-Übung, 10 Minuten") + ")\n" + M.from + ":\n„" + M.mail.replace(/^„|“$/g, "") + "“\n"
      + (M.kind === "full" ? "Antworten Sie auf die E-Mail. Schreiben Sie etwas zu allen vier Punkten. Überlegen Sie sich vor dem Schreiben eine passende Reihenfolge der Punkte, eine passende Anrede, Einleitung und einen passenden Schluss." : "Schreiben Sie eine kurze E-Mail (3 bis 5 Sätze).")
      + " Register: " + (M.reg === "du" ? "du (informell)" : "Sie") + ".\n" + M.points.map(function (p) { return "- " + p; }).join("\n");
  }
  function graderPrompt(M, text, flag) {
    var G = DATA.grader || {}, g = (M.kind === "full" ? G.full : G.mini) || "";
    var focus = (M.focus || []).length ? "\n\nCheck these typical B1 errors for this task in particular:\n" + M.focus.map(function (f) { return "- " + f; }).join("\n") : "";
    return g.replace("{{FLAG}}", flag ? G.flag || "" : "") + focus + "\n---\n" + mailTask(M) + "\n---\nMeine E-Mail:\n\n" + text.trim() + "\n";
  }
  function copyText(text, done) {
    var ok = false, ta = document.createElement("textarea");
    function onCopy(e) { if (e.clipboardData) { e.clipboardData.setData("text/plain", text); e.preventDefault(); ok = true; } }
    ta.value = text; ta.setAttribute("readonly", ""); ta.style.position = "absolute"; ta.style.left = "-9999px"; ta.style.top = window.scrollY + "px";
    document.body.appendChild(ta); ta.select();
    document.addEventListener("copy", onCopy, true);
    try { document.execCommand("copy"); } catch (e) {}
    document.removeEventListener("copy", onCopy, true);
    ta.remove();
    if (ok || !(navigator.clipboard && navigator.clipboard.writeText)) return done(ok);
    try { navigator.clipboard.writeText(text).then(function () { done(true); }, function () { done(false); }); } catch (e) { done(false); }
  }
  function wordCount(t) { var m = t.match(/[A-Za-zÄÖÜäöüß]+/g); return m ? m.length : 0; }
  var mailTimer = null, MIN_WORDS = 15;
  var CHECKS = ["Ein Register bis zur letzten Zeile (du: kein höfliches Sie, Ihnen, Ihr. Sie: kein du, dir, dein).", "Nach weil, dass, wenn, ob steht das konjugierte Verb am Ende.", "Im Hauptsatz: Modalverb … Infinitiv am Ende, haben oder sein … Partizip am Ende.", "Jeder Punkt der Aufgabe hat mindestens einen Satz.", "Die meisten Sätze beginnen nicht mit „Ich“ oder „Wir“ (besser: Leider, Am Samstag, Deshalb …).", "Anrede mit Komma, danach klein weiter. Gruß ohne Komma (Viele Grüße)."];
  function showMail(id) {
    var M = (id && mailById(id)) || mailToday(), h = '<article class="mz">' + backLink();
    setRoute("#/schreiben" + (M ? "/" + M.id : ""));
    current = null; hideCard(); setNav("bDay");
    if (mailTimer) { clearInterval(mailTimer); mailTimer = null; }
    if (!M) { main.innerHTML = h + '<h2>Schreiben</h2><p class="hint">' + ((DATA.mail || []).length ? "Du hast alle E-Mail-Aufgaben geschrieben. Schreib sie nach ein paar Wochen noch einmal und vergleiche." : "Noch keine E-Mail-Aufgaben in dieser Version.") + "</p></article>"; wireBack(); return; }
    var full = M.kind === "full", mins = full ? 30 : 10, saved = state.mails[M.id] || {};
    h += "<h2>Schreiben · " + (full ? "Prüfungs-E-Mail" : "Mini-E-Mail") + '</h2><div class="sub">' + esc(M.theme) + " · " + (M.reg === "du" ? "informell (du)" : "Sie") + " · " + mins + " Minuten" + (saved.done ? " · ✓ geschrieben" : "") + "</div>";
    h += '<div class="task"><div class="from">' + esc(M.from) + ':</div><blockquote>' + esc(M.mail).replace(/\n/g, "<br>") + "</blockquote><p>"
      + (full ? "Antworten Sie auf die E-Mail. Schreiben Sie etwas zu allen vier Punkten. Überlegen Sie sich vor dem Schreiben eine passende Reihenfolge der Punkte, eine passende Anrede, Einleitung und einen passenden Schluss." : "Schreiben Sie eine kurze E-Mail (3 bis 5 Sätze).")
      + "</p><ul>" + M.points.map(function (p) { return "<li>" + esc(p) + "</li>"; }).join("") + "</ul></div>";
    var other = full ? mailNext("mini") : null;
    if (other && !saved.done) h += '<p class="hint">Heute keine Zeit für 30 Minuten? <a href="#" id="mSwap">Lieber eine Mini-E-Mail</a></p>';
    h += '<textarea id="mtext" rows="' + (full ? 14 : 8) + '" spellcheck="false" placeholder="' + (M.reg === "du" ? "Liebe … / Lieber … / Hallo …," : "Liebe Frau … / Sehr geehrte Damen und Herren,") + '">' + esc(saved.t || "") + "</textarea>";
    h += '<div class="mrow"><span class="hint" id="mcount"></span><button class="small" id="tStart">Timer (' + mins + " Min)</button> <span id=\"tLeft\" class=\"hint\"></span></div>";
    h += '<details class="selfcheck"><summary>Checkliste vor dem Feedback</summary><ul>' + CHECKS.map(function (x) { return '<li><label><input type="checkbox"> ' + esc(x) + "</label></li>"; }).join("") + "</ul></details>";
    h += '<div class="fbox"><div class="fhead">Feedback</div><label class="hint"><input type="checkbox" id="flagFirst"> Erst nur die Fehler markieren lassen, ich verbessere selbst</label>'
      + '<div class="fbtns"><button id="toClaude">Feedback mit Claude</button><button id="toGpt">Feedback mit ChatGPT</button></div>'
      + '<div class="cmsg" id="cmsg" role="status"></div>'
      + '<p class="hint">Ab ' + MIN_WORDS + ' Wörtern kopieren die Knöpfe deine E-Mail mit der Aufgabe und einer Korrektur-Anleitung nach den telc-Kriterien. Im neuen Tab einfügen (Strg+V, am Mac Cmd+V) und abschicken. <a href="#" id="mDone">Fertig ohne Feedback</a></p>'
      + '<details class="pbox" id="pboxWrap"><summary>Einfügen klappt nicht?</summary><p class="hint">Du brauchst ein eigenes Konto bei Claude oder ChatGPT. Wenn das Einfügen nicht klappt, kopiere den Text hier unten selbst.</p><p><button class="small" id="copyOnly">Nur kopieren</button></p><textarea id="pbox" rows="8" readonly></textarea></details></div>';
    h += '<div id="mtraps">' + (saved.done ? trapsHtml(M) : "") + "</div>";
    h += mailList(M.id) + "</article>";
    main.innerHTML = h;
    wireBack();
    var ta = document.getElementById("mtext"), cnt = document.getElementById("mcount"), cmsg = document.getElementById("cmsg");
    function note(text, warn) { cmsg.textContent = text; cmsg.className = "cmsg" + (warn ? " warn" : ""); }
    function upd() { var n = wordCount(ta.value); cnt.textContent = n + (n === 1 ? " Wort" : " Wörter") + " (Richtwert: " + (full ? "100 bis 120" : "40 bis 60") + ")"; }
    ta.addEventListener("input", function () { var s = state.mails[M.id] || {}; s.t = ta.value; state.mails[M.id] = s; save(); upd(); if (cmsg.classList.contains("warn") && wordCount(ta.value) >= MIN_WORDS) note("", false); });
    upd();
    var sw = document.getElementById("mSwap");
    if (sw) sw.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); logOf(todayStr()).sp = other.id; save(); showMail(other.id); });
    document.getElementById("tStart").addEventListener("click", function (ev) {
      ev.stopPropagation();
      var end = Date.now() + mins * 60000, left = document.getElementById("tLeft");
      if (mailTimer) clearInterval(mailTimer);
      mailTimer = setInterval(function () {
        var s = Math.max(0, Math.round((end - Date.now()) / 1000));
        if (!document.getElementById("tLeft")) { clearInterval(mailTimer); mailTimer = null; return; }
        left.textContent = s ? "Noch " + Math.floor(s / 60) + ":" + ("0" + (s % 60)).slice(-2) : "Die Zeit ist um. Schreib den Satz zu Ende und geh die Checkliste durch.";
        if (!s) { clearInterval(mailTimer); mailTimer = null; }
      }, 1000);
      left.textContent = "Noch " + mins + ":00";
    });
    function finish() {
      var s = state.mails[M.id] || {}; s.t = ta.value; s.done = true; s.d = todayStr(); state.mails[M.id] = s;
      if (!(plan().log[todayStr()] || {}).s) markDone("s", M.id); else save();
      document.getElementById("mtraps").innerHTML = trapsHtml(M);
      if (!main.querySelector(".nextbar")) addNextBar(document.getElementById("mtraps"));
    }
    function tooShort() {
      var n = wordCount(ta.value);
      if (n >= MIN_WORDS) return false;
      note(n ? "Noch zu kurz: erst " + n + (n === 1 ? " Wort" : " Wörter") + ". Schreib mindestens " + MIN_WORDS + " Wörter." : "Schreib zuerst deine E-Mail (mindestens " + MIN_WORDS + " Wörter).", true);
      return true;
    }
    function send(site) {
      if (tooShort()) return;
      var text = graderPrompt(M, ta.value, document.getElementById("flagFirst").checked);
      document.getElementById("pbox").value = text;
      copyText(text, function (ok) {
        if (!document.body.contains(cmsg)) return;
        note(ok ? (site ? "Kopiert. Füge den Text im neuen Tab ein und schick ihn ab." : "Kopiert.") : "Kopieren hat nicht geklappt. Öffne „Einfügen klappt nicht?“ und kopiere den Text dort.", !ok);
        if (!ok) document.getElementById("pboxWrap").open = true;
      });
      if (site) window.open(site === "claude" ? "https://claude.ai/new" : "https://chatgpt.com/", "_blank", "noopener");
      finish();
    }
    document.getElementById("toClaude").addEventListener("click", function (ev) { ev.stopPropagation(); send("claude"); });
    document.getElementById("toGpt").addEventListener("click", function (ev) { ev.stopPropagation(); send("gpt"); });
    document.getElementById("copyOnly").addEventListener("click", function (ev) { ev.stopPropagation(); send(null); });
    document.getElementById("mDone").addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); if (tooShort()) return; finish(); note("Erledigt. Gut gemacht!", false); });
    wireMList();
    window.scrollTo(0, 0);
  }
  function trapsHtml(M) {
    if (!(M.focus || []).length) return "";
    return '<details class="selfcheck" open><summary>Typische Fallen bei dieser Aufgabe</summary><ul>' + M.focus.map(function (f) { return "<li>" + esc(f) + "</li>"; }).join("") + '</ul><p class="hint">Vergleiche mit deiner E-Mail. Das Feedback von Claude oder ChatGPT achtet auch darauf.</p></details>';
  }
  function mailList(cur) {
    var M = DATA.mail || [], done = M.filter(function (x) { return (state.mails[x.id] || {}).done; });
    if (!done.length) return "";
    return '<details class="hlist"><summary>Deine E-Mails (' + done.length + ")</summary><ul>" + done.map(function (x) {
      var s = state.mails[x.id];
      return '<li><a href="#" data-m="' + x.id + '"' + (x.id === cur ? ' class="cur"' : "") + ">" + esc(x.theme) + " (" + esc(x.reg) + ", " + (x.kind === "full" ? "Prüfung" : "mini") + ")</a> <span class=\"meta\">" + esc((s.d || "").split("-").reverse().join(".")) + " · " + wordCount(s.t || "") + " Wörter</span></li>";
    }).join("") + "</ul></details>";
  }
  function wireMList() { each(main.querySelectorAll(".hlist a[data-m]"), function (a) { a.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); showMail(a.getAttribute("data-m")); }); }); }

  function lesenToday() {
    var L = plan().log[todayStr()] || {}, m = /^(\d\d)(A|B|AB|L)$/.exec(L.l || "");
    return m ? { n: m[1], part: m[2] } : lesenNext();
  }
  function openLesen() {
    var x = lesenToday();
    if (!x) { showToc(); return; }
    fromDay = true;
    if (x.part === "L") showStory(x.n, "l");
    else if (x.part === "AB") showStory(x.n, "p");
    else showStory(x.n, "p", x.part);
  }
  function partLabel(n, part) {
    var Q = DATA.pq[n];
    if (part === "A") return "Teil A: Artikel mit 5 Fragen";
    var B = Q && Q[1];
    return "Teil B: " + (!B ? "" : B.t === "rf" ? "Meinungen oder Interview, richtig/falsch" : B.kind === "headlines" ? "Kurznachrichten und Überschriften" : "Anzeigen und Situationen");
  }
  function taskInfo(t, L) {
    if (t === "w") {
      var wp = wordsPlan();
      return { done: !!L.wd, meta: L.wd ? "Heute: " + (L.wd.r || 0) + " wiederholt, " + (L.wd.n || 0) + " neue" : (wp.due.length ? wp.due.length + " zum Wiederholen" : "nichts zum Wiederholen") + " · " + wp.fresh.length + " neue" };
    }
    if (t === "h") {
      var T = (L.h && hoerenById(L.h)) || hoerenNext();
      if (!T) return { done: !!L.h, meta: (DATA.hoeren || []).length ? "Alle Hörübungen gemacht" : "Noch keine Hörübungen in dieser Version" };
      var r = state.hres[T.id];
      if (isLinked(T)) return { done: !!L.h, meta: T.set + ": " + T.part + (L.h && r && r.s != null && r.n ? " · " + r.s + "/" + r.n : "") };
      return { done: !!L.h, meta: hTitle(T) + ": " + T.title + " · " + T.items.length + " Aussagen" + (L.h && r && r.r ? " · " + total(r.r) + "/" + r.r.length : "") };
    }
    if (t === "l") {
      var x = lesenToday();
      if (!x) return { done: !!L.l, meta: "Alle Prüfungssets gemacht" };
      var s = DATA.stories[byNum(x.n)];
      var what = x.part === "L" ? "Leichte Geschichte" : x.part === "AB" ? "Prüfung Teil A und B" : "Prüfung " + partLabel(x.n, x.part);
      return { done: !!L.l, meta: x.n + " " + s.t + " · " + what };
    }
    var M = mailToday();
    if (!M) return { done: !!L.s, meta: (DATA.mail || []).length ? "Alle E-Mail-Aufgaben geschrieben" : "Noch keine E-Mail-Aufgaben in dieser Version" };
    return { done: !!L.s, meta: (M.kind === "full" ? "Prüfungs-E-Mail" : "Mini-E-Mail") + " (" + M.reg + "): " + M.theme };
  }
  function weekStrip() {
    var now = new Date(), wd = (now.getDay() + 6) % 7, names = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"], h = '<div class="week"><span class="lbl">Diese Woche:</span>';
    for (var i = 0; i < 7; i++) {
      var d = ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() - wd + i)), L = plan().log[d];
      var n = L ? ["wd", "h", "l", "s"].filter(function (k) { return L[k]; }).length : 0, need = L && DAY_SIZES[L.size] ? DAY_SIZES[L.size].t.length : 4;
      h += '<span class="wd' + (d === todayStr() ? " today" : "") + '" title="' + d + '">' + names[i] + " " + (!n ? "○" : n >= need ? "●" : "◐") + "</span>";
    }
    return h + "</div>";
  }
  function daySummary() {
    var p = plan(), L = p.log[todayStr()] || {}, ts = DAY_SIZES[p.size].t, done = ts.filter(function (t) { return L[TASK_DONE[t]]; }).length;
    return done >= ts.length ? "Heute alles geschafft ✓" : done + " von " + ts.length + (ts.length === 1 ? " Aufgabe" : " Aufgaben") + " erledigt";
  }
  function showDay() {
    setRoute("#/heute");
    current = null; hideCard(); fromDay = false; sess = null; setNav("bDay");
    var p = plan(), size = DAY_SIZES[p.size], L = p.log[todayStr()] || {};
    var dl = new Date().toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long" });
    var h = '<article class="day">';
    if (!state.welcomed) h += '<div class="welcome line"><b>Neu hier?</b> <a href="#" id="openHelp">Kurze Anleitung (Englisch) ›</a> <button class="small" id="hideWelcome">Ausblenden</button></div>';
    h += '<h2>Heute</h2><div class="sub">' + esc(dl) + " · Lerntag " + studyDayNo() + " · " + esc(daySummary()) + "</div>";
    h += '<div class="sizes"><span class="lbl">Wie viel Zeit hast du heute?</span>' + DAY_SIZES.map(function (s, i) { return '<button class="small' + (i === p.size ? " on" : "") + '" data-size="' + i + '" title="' + esc(s.tip) + '" aria-pressed="' + (i === p.size) + '">' + s.lab + "</button>"; }).join("") + "</div>";
    h += nextBar(true);
    h += '<ul class="tasks">';
    ["w", "h", "l", "s"].forEach(function (t, i) {
      var inPlan = size.t.indexOf(t) >= 0, info = taskInfo(t, L);
      h += '<li class="task' + (info.done ? " done" : "") + (inPlan ? "" : " off") + '" data-t="' + t + '" role="button" tabindex="0"><span class="tick">' + (info.done ? "✓" : i + 1) + '</span><span class="tt"><b>' + TASK_NAMES[t] + (inPlan ? "" : ' <span class="opt-l">(heute frei)</span>') + '</b><span class="meta">' + esc(info.meta) + (info.done ? "" : " · " + taskMin(t)) + '</span></span><span class="chev" aria-hidden="true">›</span></li>';
    });
    h += "</ul>" + weekStrip() + shareHtml();
    h += '<p class="hint">An einem müden Tag reichen 5 Minuten. Verpasste Tage sind kein Problem: Der Plan macht dort weiter, wo du aufgehört hast. Sprechen übst du am besten mit einer Partnerin oder einem Partner.</p></article>';
    main.innerHTML = h;
    wireShare();
    each(main.querySelectorAll(".sizes button"), function (b) { b.addEventListener("click", function (ev) { ev.stopPropagation(); plan().size = +b.getAttribute("data-size"); save(); showDay(); }); });
    each(main.querySelectorAll(".task"), function (li) {
      function go(ev) { ev.stopPropagation(); openTask(li.getAttribute("data-t")); }
      li.addEventListener("click", go);
      li.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(ev); } });
    });
    wireNext();
    var oh = document.getElementById("openHelp"), hw = document.getElementById("hideWelcome");
    if (oh) oh.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); showHelp(); });
    if (hw) hw.addEventListener("click", function (ev) { ev.stopPropagation(); state.welcomed = true; save(); showDay(); });
    window.scrollTo(0, 0);
  }
  document.getElementById("bDay").addEventListener("click", showDay);
