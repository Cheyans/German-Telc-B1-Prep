import json, re, sys, os, difflib
BASE = os.path.dirname(os.path.abspath(__file__))
PRIV = os.environ.get("B1_PRIVATE", os.path.join(BASE, "private"))
TR = os.path.join(PRIV, "allango-676865", "transcripts")
TRAPS = {"when", "who", "number", "change", "flip", "overstate", "negation", "paraphrase", "same-word", "none"}
tracks = json.load(open(f"{BASE}/hoeren/tracks.json", encoding="utf-8"))
def sec(t):
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None
def norm(s):
    return re.sub(r"[^\wäöüß]+", " ", s.lower().replace("ß", "ss")).split()
def check(nn):
    err, warn = [], []
    p = f"{BASE}/hoeren/h_{nn}.json"
    if not os.path.exists(p):
        return [f"missing {p}"], []
    H = json.load(open(p, encoding="utf-8"))
    info = tracks[nn]
    lines = []
    tp = f"{TR}/track_{nn}.txt"
    if os.path.exists(tp):
        for ln in open(tp, encoding="utf-8"):
            m = re.match(r"\[(\d\d):(\d\d)\] (.*)", ln)
            if m:
                lines.append((int(m.group(1)) * 60 + int(m.group(2)), m.group(3)))
    else:
        warn.append("transcript not found, evidence not checked")
    for k in ("audio", "mt", "teil", "page"):
        if str(H.get(k)) != str(info[k] if k != "audio" else nn):
            err.append(f"{k} is {H.get(k)}, want {info[k] if k != 'audio' else nn}")
    want_tasks, want_items = (2, 6) if info["teil"] == 2 else (1, 10)
    tasks = H.get("tasks", [])
    if len(tasks) != want_tasks:
        err.append(f"{len(tasks)} tasks, want {want_tasks}")
    prev_to = None
    for ti, t in enumerate(tasks):
        tag = f"task {ti + 1}"
        for k in ("part", "title", "from", "to", "intro", "items"):
            if k not in t:
                err.append(f"{tag}: missing {k}")
        f0, t0 = sec(t.get("from")), sec(t.get("to"))
        if f0 is None or t0 is None or f0 >= t0:
            err.append(f"{tag}: bad from/to {t.get('from')}-{t.get('to')}")
        if info["teil"] == 2 and ti == 1 and prev_to is not None and f0 != prev_to:
            warn.append(f"{tag}: from {t.get('from')} is not the first half's to")
        prev_to = t0
        items = t.get("items", [])
        if len(items) != want_items:
            err.append(f"{tag}: {len(items)} items, want {want_items}")
        trues = sum(1 for it in items if it.get("a") is True)
        lo, hi = (4, 6) if want_items == 10 else (2, 4)
        if not lo <= trues <= hi:
            err.append(f"{tag}: {trues} true of {len(items)}, want {lo}-{hi}")
        run, last, maxrun = 0, None, 0
        for it in items:
            run = run + 1 if it.get("a") == last else 1
            last = it.get("a"); maxrun = max(maxrun, run)
        if maxrun > 3:
            err.append(f"{tag}: {maxrun} equal answers in a row")
        need = 7 if want_items == 10 else 4
        traps = [it.get("trap") for it in items]
        if sum(1 for x in traps if x != "none") < need:
            err.append(f"{tag}: only {sum(1 for x in traps if x != 'none')} trap items, want {need}")
        last_at = -1
        for ii, it in enumerate(items):
            itag = f"{tag} item {ii + 1}"
            for k in ("s", "a", "at", "ev", "why", "trap", "w"):
                if k not in it:
                    err.append(f"{itag}: missing {k}")
            if not isinstance(it.get("a"), bool):
                err.append(f"{itag}: a must be true or false")
            if it.get("trap") not in TRAPS:
                err.append(f"{itag}: unknown trap {it.get('trap')}")
            if len(re.findall(r"\w+", it.get("s", ""))) > 14:
                err.append(f"{itag}: statement over 14 words")
            if len(re.findall(r"\w+", it.get("ev", ""))) > 12:
                err.append(f"{itag}: ev over 12 words")
            if info["teil"] != 2 and it.get("t") not in (1, 2, 3, 4, 5):
                err.append(f"{itag}: t must be 1-5")
            a = sec(it.get("at"))
            if a is None:
                err.append(f"{itag}: bad at {it.get('at')}")
                continue
            if f0 is not None and t0 is not None and not (f0 - 5 <= a <= t0 + 5):
                err.append(f"{itag}: at {it.get('at')} outside {t.get('from')}-{t.get('to')}")
            if a < last_at - 5:
                warn.append(f"{itag}: at {it.get('at')} is earlier than the item before")
            last_at = max(last_at, a)
            if lines and it.get("ev"):
                near = " ".join(x for s, x in lines if a - 20 <= s <= a + 25)
                ev, nw = norm(it["ev"]), norm(near)
                hit = sum(1 for w in ev if w in nw) / max(1, len(ev))
                if hit < 0.7:
                    warn.append(f"{itag}: ev not found near {it.get('at')} ({hit:.0%} of words)")
            for k in ("s", "ev", "intro", "title"):
                v = it.get(k, "") if k in ("s", "ev") else t.get(k, "")
                if "—" in v or "–" in v:
                    err.append(f"{itag}: dash in {k}")
                if '"' in v:
                    err.append(f"{itag}: straight quote in {k}")
        if info["teil"] != 2:
            per = {}
            for it in items:
                per[it.get("t")] = per.get(it.get("t"), 0) + 1
            if any(per.get(n, 0) != 2 for n in range(1, 6)):
                err.append(f"{tag}: want 2 items per text, have {per}")
    return err, warn

TRU = os.path.join(PRIV, "allango-676830", "official")
utracks = json.load(open(f"{BASE}/hoeren/tracks_u.json", encoding="utf-8"))
uplan = {str(x["task"]): x for x in json.load(open(f"{BASE}/hoeren/u_plan.json", encoding="utf-8"))}
def official(tr):
    p = f"{TRU}/track_{tr}.txt"
    if not os.path.exists(p):
        return ""
    t = open(p, encoding="utf-8").read()
    return t.split("## Official transcript", 1)[-1].split("## Whisper", 1)[0]
def check_u(n):
    err, warn = [], []
    p = f"{BASE}/hoeren/u_{n}.json"
    if not os.path.exists(p):
        return [f"missing {p}"], []
    H = json.load(open(p, encoding="utf-8"))
    P = uplan.get(n)
    if not P:
        return [f"task {n} not in u_plan.json"], []
    if H.get("book") != "U" or str(H.get("task")) != n:
        err.append("book must be U and task must match the file")
    if H.get("tracks") != P["tracks"]:
        err.append(f"tracks {H.get('tracks')}, want {P['tracks']}")
    for k in ("title", "intro"):
        if not H.get(k):
            err.append(f"missing {k}")
        elif "—" in H[k] or "–" in H[k] or '"' in H[k]:
            err.append(f"dash or straight quote in {k}")
    items = H.get("items", [])
    want = P["items"]
    if len(items) != want:
        err.append(f"{len(items)} items, want {want}")
    trues = sum(1 for it in items if it.get("a") is True)
    lo, hi = (3, 5) if want == 8 else (4, 6)
    if not lo <= trues <= hi:
        err.append(f"{trues} true of {len(items)}, want {lo}-{hi}")
    run, last, maxrun = 0, None, 0
    for it in items:
        run = run + 1 if it.get("a") == last else 1
        last = it.get("a"); maxrun = max(maxrun, run)
    if maxrun > 3:
        err.append(f"{maxrun} equal answers in a row")
    need = 5 if want == 8 else 7
    if sum(1 for it in items if it.get("trap") != "none") < need:
        err.append(f"fewer than {need} trap items")
    per = {}
    order = [P["tracks"].index(it.get("tr")) if it.get("tr") in P["tracks"] else -1 for it in items]
    if order != sorted(order):
        err.append("items are not in track order")
    for ii, it in enumerate(items):
        itag = f"item {ii + 1}"
        for k in ("tr", "s", "a", "at", "ev", "why", "trap", "w"):
            if k not in it:
                err.append(f"{itag}: missing {k}")
        if it.get("tr") not in P["tracks"]:
            err.append(f"{itag}: tr {it.get('tr')} not in this task")
            continue
        per[it["tr"]] = per.get(it["tr"], 0) + 1
        if not isinstance(it.get("a"), bool):
            err.append(f"{itag}: a must be true or false")
        if it.get("trap") not in TRAPS:
            err.append(f"{itag}: unknown trap {it.get('trap')}")
        if len(re.findall(r"\w+", it.get("s", ""))) > 14:
            err.append(f"{itag}: statement over 14 words")
        if len(re.findall(r"\w+", it.get("ev", ""))) > 12:
            err.append(f"{itag}: ev over 12 words")
        if sec(it.get("at")) is None:
            err.append(f"{itag}: bad at {it.get('at')}")
        for k in ("s", "ev"):
            v = it.get(k, "")
            if "—" in v or "–" in v:
                err.append(f"{itag}: dash in {k}")
            if '"' in v:
                err.append(f"{itag}: straight quote in {k}")
        off = official(it["tr"])
        if off and it.get("ev"):
            ev, nw = norm(it["ev"]), norm(off)
            hit = sum(1 for w in ev if w in nw) / max(1, len(ev))
            if hit < 0.8:
                warn.append(f"{itag}: ev words not in the official transcript of track {it['tr']} ({hit:.0%})")
    for tr in P["tracks"]:
        if not per.get(tr):
            err.append(f"no item for track {tr}")
    if n == "3" and any(per.get(tr, 0) != 2 for tr in P["tracks"]):
        err.append(f"task 3 needs 2 items per track, has {per}")
    return err, warn

nums = sys.argv[1:] or sorted(n for n in tracks if os.path.exists(f"{BASE}/hoeren/h_{n}.json"))
total = 0
for nn in nums:
    e, w = check_u(nn[1:]) if nn.startswith("u") else check(nn)
    total += len(e)
    print(f"audio {nn}: {len(e)} errors, {len(w)} warnings")
    for x in e:
        print("  ERROR", x)
    for x in w:
        print("  warn ", x)
print("total errors:", total)
