import datetime
import glob
import json
import os
import random
from collections import defaultdict
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quizlib import layout, order, player
import check_pruefung

BASE = os.path.dirname(os.path.abspath(__file__))

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(BASE, "..", "b1-wortschatz-geschichten.html"))
MARK = re.compile(r"\[\[([^\[\]|]+)\|([WGXR]\d{3,4})\]\]")
TOPICS = {
    "01": "Prüfung", "02": "Wohnen", "03": "Arbeit", "04": "Behörden", "05": "Gesundheit", "06": "Einkaufen",
    "07": "Verkehr", "08": "Freizeit", "09": "Diskussion", "10": "Medien", "11": "Lernen", "12": "Familie",
    "13": "Essen", "14": "Arbeit", "15": "Wohnen", "16": "Gesundheit", "17": "Bank und Post", "18": "Geld",
    "19": "Reisen", "20": "Essen", "21": "Medien", "22": "Beziehungen", "23": "Gefühle", "24": "Kultur",
    "25": "Natur", "26": "Umwelt", "27": "Politik", "28": "Kriminalität",
}


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s).replace(" ", " ")).strip()


def seg_text(segs):
    return "".join(x if isinstance(x, str) else x[0] for x in segs)


REG = r"(?:D|A|CH)(?:,\s*(?:D|A|CH))*"


def display(e):
    t = e["text"]
    t = re.sub(r"\s*→.*$", "", t)
    t = re.sub(r"\s*\(" + REG + r"\)\s*", " ", t)
    t = re.sub(r"\s+" + REG + r"\s*:.*$", "", t)
    t = re.sub(r"(,\s*(?:¨?-\w*|\w+))\s+(die\s+[A-ZÄÖÜ][\wäöüß]*in\b)", r"\1 / \2", t)
    return re.sub(r"\s+", " ", t).strip(" ,;")


inputs = sorted(glob.glob(f"{BASE}/stories/story_*.md")) + sorted(glob.glob(f"{BASE}/quiz/quiz_*.json")) + sorted(glob.glob(f"{BASE}/pruefung/set_*.md")) + sorted(glob.glob(f"{BASE}/pquiz/pq_*.json"))
ann_path = f"{BASE}/annotated.json"
if not os.path.exists(ann_path):
    sys.exit("annotated.json is missing: run annotate.py first")
if any(os.path.getmtime(p) > os.path.getmtime(ann_path) for p in inputs):
    print("WARNING: stories, sets or quizzes changed after annotated.json, run annotate.py again")
ann = json.load(open(ann_path, encoding="utf-8"))

entries = {e["id"]: e for e in json.load(open(f"{BASE}/final_entries.json", encoding="utf-8"))}
glosses = {}
for path in sorted(glob.glob(f"{BASE}/glosses/agent_*.json")) + sorted(glob.glob(f"{BASE}/glosses/basics_P*.json")):
    glosses.update(json.load(open(path, encoding="utf-8")))

titles = dict(ann.get("titles") or {})
if not titles:
    for path in sorted(glob.glob(f"{BASE}/stories/story_*.md")):
        m = re.match(r"#\s*(\d+)\s+(.*)", open(path, encoding="utf-8").readline())
        titles[m.group(1).zfill(2)] = m.group(2).strip()
stories, used = [], {}
for num in sorted(titles):
    title = titles[num]
    paras = ann["stories"][num]
    b1 = set()
    for p in paras:
        for seg in p:
            if isinstance(seg, list) and seg[1]:
                for i in seg[1].split(","):
                    used.setdefault(i, set())
                    if (seg[2] if len(seg) > 2 else "") != "c":
                        used[i].add(num)
                        if entries[i]["level"] == "B1":
                            b1.add(i)
    words = sum(len(re.findall(r"\w+", seg_text(p))) for p in paras)
    stories.append({"n": num, "t": title, "topic": TOPICS.get(num, ""), "w": words, "k": len(b1), "p": paras})
stories.sort(key=lambda s: s["n"])

quiz = {}
verified_path = f"{BASE}/quiz/verified.json"
verified = set(json.load(open(verified_path))) if os.path.exists(verified_path) else set()
for path in sorted(glob.glob(f"{BASE}/quiz/quiz_*.json")):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print("skipping", os.path.basename(path), e)
        continue
    num = d["story"]
    if num not in verified:
        continue
    segs = ann["quiz"].get(num)
    if not segs or len(segs) != len(d["questions"]):
        print("skipping quiz", num, "(not annotated yet)")
        continue
    paras = [norm(seg_text(p)) for p in ann["stories"][num]]
    items = []
    for k, ((q, a), (right, perm)) in enumerate(zip(zip(d["questions"], segs), layout(num, len(segs)))):
        opts = order(a["right"], a["wrong"], right, perm)
        ev = norm(q["evidence"])
        pi = next((i for i, p in enumerate(paras) if ev in p), -1)
        items.append({"q": a["q"], "o": opts, "a": right, "ev": ev, "why": q["why"], "pi": pi})
        for seg in a["q"] + [x for o in opts for x in o]:
            if isinstance(seg, list) and seg[1]:
                for i in seg[1].split(","):
                    used.setdefault(i, set())
    quiz[num] = items

extras = {x["id"]: x for x in json.load(open(f"{BASE}/extras.json", encoding="utf-8"))}
pverified_path = f"{BASE}/pquiz/verified.json"
pverified = set(json.load(open(pverified_path))) if os.path.exists(pverified_path) else set()


def rf_order(num, answers):
    want = int(num) // 3 % 2 == 0
    for seed in range(200):
        p = list(range(len(answers)))
        random.Random(int(num) * 1009 + seed).shuffle(p)
        if answers[p[0]] == want and p != sorted(p):
            return p
    return list(range(len(answers)))


def finder(blocks):
    texts = [norm(seg_text(b["s"])) for b in blocks]

    def where(ev):
        ev = norm(ev)
        for cand in [ev] + re.split(r"(?<=[.!?…])\s+", ev):
            for k, t in enumerate(texts):
                if len(cand) > 8 and cand in t:
                    return k
        return -1
    return where


pr, pq, pused = {}, {}, {}
for num, st in sorted(ann.get("pruefung", {}).items()):
    if num not in pverified:
        continue
    if os.path.exists(f"{BASE}/pruefung/set_{num}.md"):
        errs, _ = check_pruefung.check(num)
        if errs:
            print("skipping Prüfung set", num, "| checker errors:", len(errs))
            continue
    inp = json.load(open(f"{BASE}/pruefung_inputs/set_{num}.json", encoding="utf-8"))
    gpath = f"{BASE}/pruefung/gloss_{num}.json"
    go = json.load(open(gpath, encoding="utf-8")) if os.path.exists(gpath) else {}
    b1, ex = set(), set()
    for b in st["blocks"]:
        for seg in b["s"]:
            if isinstance(seg, list) and seg[1]:
                for i in seg[1].split(","):
                    used.setdefault(i, set())
                    if (seg[2] if len(seg) > 2 else "") != "c":
                        pused.setdefault(i, set()).add(num)
                        if i in extras:
                            ex.add(i)
                        elif entries.get(i, {}).get("level") == "B1":
                            b1.add(i)
    letters = [re.match(r"([a-h])\)", seg_text(b["s"])).group(1) for b in st["blocks"] if b["k"] == "h3" and b["part"] == "B" and re.match(r"([a-h])\)", seg_text(b["s"]))]
    wc = sum(len(re.findall(r"\w+", seg_text(b["s"]))) for b in st["blocks"])
    pr[num] = {"b": inp["part_b"], "blocks": st["blocks"], "w": wc, "k": len(b1), "x": len(ex), "go": go}
    a = ann.get("pquiz", {}).get(num)
    d = json.load(open(f"{BASE}/pquiz/pq_{num}.json", encoding="utf-8"))
    if not a or len(a) != len(d["parts"]):
        print("skipping Prüfung quiz", num, "(not annotated yet)")
        continue
    where = finder(st["blocks"])
    parts = []
    for part, ap in zip(d["parts"], a):
        if part["type"] == "abc":
            items = []
            for (it, at), (right, perm) in zip(zip(part["items"], ap["items"]), player(num, len(part["items"]))):
                items.append({"q": at["q"], "o": order(at["right"], at["wrong"], right, perm), "a": right, "ev": norm(it["evidence"]), "why": it["why"], "pi": where(it["evidence"])})
            parts.append({"t": "abc", "items": items})
        elif part["type"] == "rf":
            items = [{"s": sg, "a": it["answer"], "ev": norm(it["evidence"]), "why": it["why"], "pi": where(it["evidence"])} for it, sg in zip(part["items"], ap["items"])]
            parts.append({"t": "rf", "items": [items[i] for i in rf_order(num, [x["a"] for x in items])]})
        else:
            opts = [{"id": o["id"], "s": sg} for o, sg in zip(part.get("options", []), ap["options"])]
            lets = [o["id"] for o in opts] if part["kind"] == "headlines" else letters + ["x"]
            parts.append({"t": "match", "kind": part["kind"], "opts": opts, "lets": lets,
                          "items": [{"id": x["id"], "s": sg, "a": x["answer"], "ev": norm(x["evidence"]), "why": x["why"], "pi": where(x["evidence"])} for x, sg in zip(part["prompts"], ap["prompts"])]})
        for it in parts[-1]["items"]:
            for seg in [x for v in ([it["q"]] + it["o"] if "q" in it else [it["s"]]) for x in v]:
                if isinstance(seg, list) and seg[1]:
                    for i in seg[1].split(","):
                        used.setdefault(i, set())
        for o in parts[-1].get("opts", []):
            for seg in o["s"]:
                if isinstance(seg, list) and seg[1]:
                    for i in seg[1].split(","):
                        used.setdefault(i, set())
    pq[num] = parts

lemma_map = defaultdict(list)
for e in entries.values():
    lem = re.sub(r"^sich\s+", "", re.sub(r"^\([^)]*\)\s*", "", e["lemma"]).strip())
    keys = {lem.lower(), re.sub(r"^\(?sich\)?\s+", "", e["lemma"]).strip().lower()}
    parts = [x.strip() for x in re.split(r"[/,]", lem) if x.strip()]
    if len(parts) > 1 and all(" " not in x for x in parts):
        keys.update(x.rstrip("-").lower() for x in parts)
    for m in re.finditer(r"(?:der|die|das)\s+([A-ZÄÖÜ][\wäöüß-]+)", e["text"]):
        keys.add(m.group(1).lower())
    for k in keys:
        lemma_map[k].append(e)


def head_of(d):
    d = d.split("=")[-1].strip() if "=" in d else d
    d = re.sub(r"\([^)]*\)", "", d).strip().split(",")[0].strip()
    m = re.match(r"^(der|die|das)(?:/(?:der|die|das))?\s+", d)
    art = m.group(1) if m else ""
    d = re.sub(r"^sich\s+", "", d[m.end():] if m else d)
    return art, (d.split() or [""])[0]


off = {}
for path in sorted(glob.glob(f"{BASE}/offlist/gloss_*.json")):
    for form, v in json.load(open(path, encoding="utf-8")).items():
        item = {"d": v["d"], "g": v["g"], "k": v.get("k", "word")}
        if item["k"] == "word":
            art, w = ("", v["base"]) if "base" in v else head_of(v["d"])
            cands = [e for e in lemma_map.get(w.lower(), []) if e["id"] not in ("W2818", "W0943")] if w else []
            if cands:
                pick = next((e for e in cands if art and e["text"].startswith(art + " ")), cands[0])
                item["id"] = pick["id"]
                used.setdefault(pick["id"], set())
        off[form] = item

words = {}
for i in sorted(used):
    e, x = entries.get(i), extras.get(i)
    if x:
        w = {"d": x["word"], "g": x["gloss"], "l": "X" if x["kind"] == "extra" else "AT"}
        if x.get("de"):
            w["de"] = x["de"]
    elif e:
        w = {"d": display(e), "g": glosses.get(i, ""), "l": e["level"]}
        if e["level"] == "B1":
            w["s"] = sorted(used[i])
    else:
        continue
    if i in pused:
        w["ps"] = sorted(pused[i])
    words[i] = w

conn = json.load(open(f"{BASE}/connectors.json", encoding="utf-8"))
drill = json.load(open(f"{BASE}/syn_drill.json", encoding="utf-8"))
syn = {"drill": drill, "items": conn["items"], "families": conn["families"], "counts": ann.get("syntax", {}).get("counts", {}), "examples": ann.get("syntax", {}).get("examples", {})}
HDIR = f"{BASE}/hoeren"
verified_h = set(json.load(open(f"{HDIR}/verified.json", encoding="utf-8"))) if os.path.exists(f"{HDIR}/verified.json") else set()
if os.environ.get("HOEREN_PREVIEW"):
    verified_h |= {os.path.basename(f)[2:-5] for f in glob.glob(f"{HDIR}/h_*.json")} | {"u" + os.path.basename(f)[2:-5] for f in glob.glob(f"{HDIR}/u_*.json")}
tracks_t = json.load(open(f"{HDIR}/tracks.json", encoding="utf-8"))
tracks_u = json.load(open(f"{HDIR}/tracks_u.json", encoding="utf-8"))
uplan = json.load(open(f"{HDIR}/u_plan.json", encoding="utf-8"))
ITEM_KEYS = ("s", "a", "at", "ev", "why", "trap", "w", "t", "tr")
htasks = {}
for nn, info in tracks_t.items():
    fp = f"{HDIR}/h_{nn}.json"
    if nn not in verified_h or not os.path.exists(fp):
        continue
    H = json.load(open(fp, encoding="utf-8"))
    for t in H["tasks"]:
        tid = f"H{nn}" + ("ab"[t["part"] - 1] if info["teil"] == 2 else "")
        htasks[tid] = {"id": tid, "book": "T", "teil": info["teil"], "mt": info["mt"], "part": t["part"],
                       "head": f"Modelltest {info['mt']}, Teil {info['teil']}" + (f" ({t['part']}. Hälfte)" if info["teil"] == 2 else ""),
                       "src": f"Testbuch S. {info['page']} · Audio {nn}", "title": re.sub(r"\s*\([12]\. Hälfte\)\s*$", "", t["title"]), "intro": t["intro"], "from": t["from"], "to": t["to"],
                       "audios": [{"n": nn, "url": info["url"], "lab": f"Audio {nn} öffnen (allango)"}],
                       "items": [{k: it[k] for k in ITEM_KEYS if k in it} for it in t["items"]]}
for u in uplan:
    n = str(u["task"])
    fp = f"{HDIR}/u_{n}.json"
    if "u" + n not in verified_h or not os.path.exists(fp):
        continue
    U = json.load(open(fp, encoding="utf-8"))
    pages = sorted({tracks_u[tr]["page"] for tr in U["tracks"]})
    def tname(tr):
        m = re.search(r"Übung (\w+) S (\d+)", tracks_u[tr]["desc"])
        return f"Übung {m.group(1)}, S. {m.group(2)}" if m else ""
    htasks["U" + n] = {"id": "U" + n, "book": "U", "teil": 0,
                       "head": "Übungsbuch, S. " + (str(pages[0]) if len(pages) == 1 else f"{pages[0]} bis {pages[-1]}"),
                       "src": "Übungsbuch · Track " + (U["tracks"][0] if len(U["tracks"]) == 1 else f"{U['tracks'][0]} bis {U['tracks'][-1]}"),
                       "title": U["title"], "intro": U["intro"],
                       "audios": [{"n": tr, "url": tracks_u[tr]["url"], "lab": f"Track {tr} öffnen ({tracks_u[tr]['len']})", "name": tname(tr), "len": tracks_u[tr]["len"]} for tr in U["tracks"]],
                       "items": [{k: it[k] for k in ITEM_KEYS if k in it} for it in U["items"]]}
HORDER = ["U1", "H01", "U2", "H02a", "U3", "H02b", "U4", "H03", "U5", "H07", "U6", "H08a", "U7", "H08b", "H09", "H13", "H14a", "H14b", "H15", "H16", "H17a", "H17b", "H18"]
hoeren = [htasks[t] for t in HORDER if t in htasks] + [htasks[t] for t in sorted(htasks) if t not in HORDER]
hlinked = json.load(open(f"{HDIR}/linked.json", encoding="utf-8")) if os.path.exists(f"{HDIR}/linked.json") else []
MDIR = f"{BASE}/mail"
mail = json.load(open(f"{MDIR}/prompts.json", encoding="utf-8")) if os.path.exists(f"{MDIR}/prompts.json") else []
grader = {k: open(f"{MDIR}/{f}", encoding="utf-8").read().strip() for k, f in (("full", "grader_full.txt"), ("mini", "grader_mini.txt"), ("flag", "flag_first.txt"))}
data = {"stories": stories, "words": words, "quiz": quiz, "syn": syn, "pr": pr, "pq": pq, "off": off, "hoeren": hoeren, "hlinked": hlinked, "mail": mail, "grader": grader, "built": datetime.date.today().isoformat()}
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

page = r"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>B1-Wortschatz in Geschichten</title>
<style>
:root { --bg:#fbfaf7; --fg:#1f2328; --muted:#6a737d; --card:#ffffff; --line:#e4e1da; --accent:#1a6fb3; --mark:#0b4f8a; --markbg:#e8f1fb; --done:#2e7d32; --bad:#c62828; --badbg:#fdecea; --okbg:#e8f5e9; --flash:#fff3c4; }
@media (prefers-color-scheme: dark) { :root { --bg:#16181c; --fg:#e6e6e6; --muted:#9aa4ad; --card:#1f2228; --line:#30343b; --accent:#6cb2f0; --mark:#9fd0ff; --markbg:#203246; --done:#7cc47f; --bad:#ef9a9a; --badbg:#3a2224; --okbg:#1f3323; --flash:#4a4120; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font: 17px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
header { position:sticky; top:0; z-index:5; background:var(--bg); border-bottom:1px solid var(--line); }
.bar { max-width:760px; margin:0 auto; padding:10px 16px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.bar h1 { font-size:17px; margin:0 auto 0 0; }
button, .btn { font:inherit; font-size:15px; padding:6px 12px; border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--fg); cursor:pointer; }
button.on { background:var(--accent); color:#fff; border-color:var(--accent); }
main { max-width:760px; margin:0 auto; padding:16px 16px 140px; }
.hint { color:var(--muted); font-size:15px; }
.progress { height:8px; background:var(--line); border-radius:4px; overflow:hidden; margin:8px 0 18px; }
.progress div { height:100%; background:var(--done); }
.toc { list-style:none; padding:0; margin:0; }
.toc li { display:flex; align-items:center; gap:12px; padding:12px; margin:8px 0; background:var(--card); border:1px solid var(--line); border-radius:10px; cursor:pointer; }
.toc .num { font-weight:700; color:var(--muted); width:2.2em; }
.toc .tt { flex:1; }
.toc .tt b { display:block; }
.toc .meta { color:var(--muted); font-size:14px; display:block; }
.toc .chk { font-size:20px; color:var(--done); width:1.4em; text-align:center; }
article h2 { font-size:24px; margin:6px 0 2px; }
article .sub { color:var(--muted); font-size:14px; margin-bottom:18px; }
article p { margin:0 0 1em; border-radius:6px; transition:background .4s; }
article p.flash { background:var(--flash); }
.w { font-weight:700; color:var(--mark); border-bottom:1px dotted var(--mark); cursor:pointer; border-radius:3px; }
.b, .n, .p, .gw { cursor:pointer; border-radius:3px; }
@media (hover: hover) { .b:hover, .n:hover, .p:hover, .gw:hover { text-decoration:underline dotted; } }
.w.sel, .b.sel, .n.sel, .p.sel, .gw.sel { background:var(--markbg); }
.gl { display:none; font-weight:400; font-size:12px; color:var(--muted); margin-left:3px; }
body.showen .gl { display:inline; }
.nav { display:flex; gap:8px; justify-content:space-between; margin-top:24px; flex-wrap:wrap; }
#card { position:absolute; left:0; top:0; z-index:10; width:min(420px, calc(100vw - 16px)); background:var(--card); border:2px solid var(--accent); border-radius:12px; box-shadow:0 6px 24px rgba(0,0,0,.28); display:none; }
#card .in { padding:10px 44px 12px 14px; position:relative; }
#card .form { font-size:14px; color:var(--muted); }
#card .entry { margin-top:4px; }
#card .dict { font-size:18px; font-weight:700; }
#card .en { font-size:17px; }
#card .more { font-size:13px; color:var(--muted); margin-top:4px; }
#card .x { position:absolute; right:6px; top:6px; padding:2px 9px; }
.lvl { display:inline-block; font-size:11px; font-weight:700; padding:0 6px; border-radius:6px; border:1px solid var(--line); color:var(--muted); vertical-align:2px; }
.lvl-B1 { color:var(--mark); border-color:var(--mark); }
.quiz { margin-top:28px; padding-top:8px; border-top:2px solid var(--line); }
.quiz h3 { font-size:20px; margin:10px 0 4px; }
.qq { margin:18px 0; }
.qt { margin-bottom:8px; }
.opts { display:flex; flex-direction:column; gap:6px; }
.opt { text-align:left; line-height:1.45; padding:8px 12px; }
.opt.no { background:var(--badbg); border-color:var(--bad); color:var(--muted); text-decoration:line-through; cursor:default; }
.opt.yes { background:var(--okbg); border-color:var(--done); font-weight:600; }
.opt.locked { cursor:default; }
.fb { margin-top:8px; font-size:15px; }
.fb .ok { color:var(--done); font-weight:700; }
.fb .sol { color:var(--bad); font-weight:700; }
.fb .try { color:var(--bad); }
.fb .ev { font-style:italic; margin:4px 0; }
.fb .why { color:var(--muted); }
.fb a, .quiz a { color:var(--accent); cursor:pointer; }
.score { font-weight:700; margin-top:8px; }
.sk, .sv { border-radius:3px; }
:root { --sA:#d35400; --sB:#7f8c8d; --sC:#8e44ad; --sD:#a0522d; --sZ:#00897b; --sR:#c2185b; --sW:#1e6fd9; --sE:#2e7d32; }
@media (prefers-color-scheme: dark) { :root { --sA:#ffb74d; --sB:#9aa4ad; --sC:#ce93d8; --sD:#d7a17a; --sZ:#4db6ac; --sR:#f48fb1; --sW:#64b5f6; --sE:#81c784; } }
body.showsyn .sk-A, .synsel.sk-A, .syn .sk-A { box-shadow:inset 0 -3px 0 var(--sA); background:color-mix(in srgb, var(--sA) 16%, transparent); }
body.showsyn .sk-C, .synsel.sk-C, .syn .sk-C { box-shadow:inset 0 -3px 0 var(--sC); background:color-mix(in srgb, var(--sC) 16%, transparent); }
body.showsyn .sk-Cm, .synsel.sk-Cm, .syn .sk-Cm { box-shadow:inset 0 -2px 0 var(--sC); }
body.showsyn .sk-B:not([data-key="und"]):not([data-key="oder"]), .synsel.sk-B, .syn .sk-B { box-shadow:inset 0 -2px 0 var(--sB); }
body.showsyn .sk-D, .synsel.sk-D, .syn .sk-D { box-shadow:inset 0 -3px 0 var(--sD); background:color-mix(in srgb, var(--sD) 16%, transparent); }
body.showsyn .sk-Z, .synsel.sk-Z, .syn .sk-Z { box-shadow:inset 0 -3px 0 var(--sZ); background:color-mix(in srgb, var(--sZ) 16%, transparent); }
body.showsyn .sk-R, .synsel.sk-R, .syn .sk-R { box-shadow:inset 0 -3px 0 var(--sR); background:color-mix(in srgb, var(--sR) 16%, transparent); }
body.showsyn .sk-Wd, body.showsyn .sk-Wi, .synsel.sk-Wd, .synsel.sk-Wi, .syn .sk-Wd, .syn .sk-Wi { box-shadow:inset 0 -3px 0 var(--sW); background:color-mix(in srgb, var(--sW) 16%, transparent); }
body.showsyn .sk-E, .synsel.sk-E, .syn .sk-E { box-shadow:inset 0 -3px 0 var(--sE); background:color-mix(in srgb, var(--sE) 16%, transparent); }
body.showsyn .sv-A, .synsel.sv-A, .syn .sv-A, body.showsyn .sv-R, .synsel.sv-R, .syn .sv-R { outline:2px solid var(--sA); outline-offset:1px; }
body.showsyn .sv-R, .synsel.sv-R, .syn .sv-R { outline-color:var(--sR); }
body.showsyn .sv-C, .synsel.sv-C, .syn .sv-C { outline:2px solid var(--sC); outline-offset:1px; }
body.showsyn .sv-D, .synsel.sv-D, .syn .sv-D { outline:2px solid var(--sD); outline-offset:1px; }
body.showsyn .sv-Z, .synsel.sv-Z, .syn .sv-Z { outline:2px solid var(--sZ); outline-offset:1px; }
body.showsyn .sv-Wd, body.showsyn .sv-Wi, .synsel.sv-Wd, .synsel.sv-Wi, .syn .sv-Wd, .syn .sv-Wi { outline:2px solid var(--sW); outline-offset:1px; }
.synbox { margin-top:8px; padding:6px 8px; border-left:4px solid var(--sB); background:color-mix(in srgb, var(--line) 40%, transparent); border-radius:6px; font-size:15px; }
.synbox.sb-A { border-color:var(--sA); } .synbox.sb-C, .synbox.sb-Cm { border-color:var(--sC); } .synbox.sb-D { border-color:var(--sD); }
.synbox.sb-Z { border-color:var(--sZ); } .synbox.sb-R { border-color:var(--sR); } .synbox.sb-Wd, .synbox.sb-Wi { border-color:var(--sW); } .synbox.sb-E { border-color:var(--sE); }
.synbox a { color:var(--accent); cursor:pointer; display:inline-block; margin-top:2px; }
button.small { font-size:13px; padding:3px 9px; margin-left:8px; vertical-align:1px; }
.syn h3 { margin:22px 0 6px; }
.syn details { margin:10px 0; border:1px solid var(--line); border-radius:10px; padding:6px 12px; background:var(--card); }
.syn summary { cursor:pointer; font-weight:700; font-size:17px; padding:4px 0; }
.syn .dot { display:inline-block; width:12px; height:12px; border-radius:6px; margin-right:6px; vertical-align:0; }
.syn .rule { color:var(--muted); margin:4px 0 8px; }
.syn ul { list-style:none; padding:0; margin:0; }
.syn li { padding:8px 0; border-top:1px solid var(--line); }
.syn .kw { font-size:18px; }
.syn .note { color:var(--muted); font-size:15px; }
.syn .cnt { color:var(--muted); font-size:13px; margin-left:6px; }
.syn .ex { font-size:15px; margin:4px 0 0 10px; }
.syn .ex a { color:var(--accent); cursor:pointer; margin-left:6px; white-space:nowrap; }
.syn .exl { color:var(--muted); font-size:13px; }
.famwrap { overflow-x:auto; }
.mail { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 16px; line-height:1.9; }
.gap { font-weight:700; color:var(--accent); white-space:nowrap; }
.gap.filled { color:var(--done); }
.tbadge { display:inline-block; font-size:12px; font-weight:700; padding:0 7px; border-radius:8px; color:#fff; margin-right:6px; }
.drill .qt .blank { font-weight:700; color:var(--accent); }
table.fam { border-collapse:collapse; font-size:14px; min-width:640px; }
table.fam th, table.fam td { border:1px solid var(--line); padding:5px 7px; text-align:left; vertical-align:top; }
table.fam th { background:var(--card); }
table.fam td.tA { color:var(--sA); } table.fam td.tB { color:var(--sB); } table.fam td.tC { color:var(--sC); } table.fam td.tZ { color:var(--sZ); } table.fam td.tE { color:var(--sE); }
#search { width:100%; font:inherit; padding:8px 12px; border-radius:8px; border:1px solid var(--line); background:var(--card); color:var(--fg); margin-bottom:12px; }
.idx { list-style:none; padding:0; margin:0; }
.idx li { padding:8px 4px; border-bottom:1px solid var(--line); }
.idx .d { font-weight:600; }
.idx .g { color:var(--muted); }
.idx a { color:var(--accent); font-size:14px; margin-left:6px; cursor:pointer; }
.vsw { display:flex; gap:6px; align-items:center; margin:2px 0 8px; }
.vsw .lbl { color:var(--muted); font-size:14px; }
.vsw button { font-size:14px; padding:4px 12px; }
.toc .ptag { display:inline-block; font-size:12px; font-weight:700; padding:0 7px; border-radius:8px; border:1px solid var(--accent); color:var(--accent); margin-left:6px; vertical-align:1px; }
.part { margin:26px 0 10px; }
.plabel { font-size:13px; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:var(--muted); border-bottom:1px solid var(--line); padding-bottom:3px; margin-bottom:10px; }
.ph { font-size:21px; line-height:1.35; margin:6px 0 12px; }
.item { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:8px 14px 2px; margin:12px 0; }
.item h4 { margin:2px 0 6px; font-size:17px; }
.sp { color:var(--muted); }
article .flash { background:var(--flash); }
.heads { list-style:none; padding:0; margin:6px 0 14px; }
.heads li { padding:4px 0; border-bottom:1px solid var(--line); }
.lets { display:flex; flex-wrap:wrap; gap:6px; }
.let { min-width:2.8em; text-align:center; padding:6px 10px; }
.opt.picked { border-color:var(--accent); box-shadow:inset 0 0 0 2px var(--accent); background:var(--markbg); }
.checkbar { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin:22px 0 6px; padding-top:12px; border-top:2px solid var(--line); }
.checkbar .check { font-weight:700; padding:8px 16px; }
.checkbar .check:disabled { opacity:.5; cursor:default; }
.checkbar .left { color:var(--muted); }
.rfb { display:flex; gap:8px; }
.rfb .opt { min-width:6.5em; text-align:center; }
.lvl-X { color:var(--sC); border-color:var(--sC); }
.lvl-AT { color:var(--sR); border-color:var(--sR); }
.lvl-off { color:var(--muted); border-style:dashed; }
.saverow { margin:22px 0 6px; padding-top:12px; border-top:1px solid var(--line); display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.saverow label.btn { display:inline-block; }
.welcome { background:var(--markbg); border:1px solid var(--accent); border-radius:10px; padding:10px 14px; margin:4px 0 14px; line-height:1.5; }
.welcome button { margin:6px 6px 0 0; }
.help h3 { margin:22px 0 6px; }
.help ul, .help ol { padding-left:22px; margin:6px 0; }
.help li { margin:5px 0; }
/*__HEUTE_CSS__*/
</style>
</head>
<body>
<header><div class="bar">
  <h1>B1-Wortschatz in Geschichten</h1>
  <nav class="tabs">
  <button id="bDay">Heute</button>
  <button id="bToc">Themen</button>
  <button id="bIdx">Wortliste</button>
  <button id="bSyn">Satzbau</button>
  <button id="bHelp" title="How to use this page">Hilfe</button>
  </nav>
</div></header>
<main id="main"></main>
<div id="card"><div class="in">
  <button class="x" id="cardX" aria-label="Schließen">✕</button>
  <div id="cBody"></div>
</div></div>
<script type="application/json" id="data">__DATA__</script>
<script>
(function () {
  var DATA = JSON.parse(document.getElementById("data").textContent);
  var KEY = "b1VocabStories_v1";
  var state = { read: {}, en: false, last: null, quiz: {}, syn: false, drill: {}, ver: {}, pread: {}, pq: {}, welcomed: false, srs: {}, look: {}, plan: {}, hres: {}, mails: {} };
  var lastRaw = null;
  function loadState(raw) { try { if (raw === undefined) raw = localStorage.getItem(KEY); lastRaw = raw; var s = JSON.parse(raw || "{}"); state.read = s.read || {}; state.en = !!s.en; state.last = s.last || null; state.quiz = s.quiz || {}; state.syn = !!s.syn; state.drill = s.drill || {}; state.ver = s.ver || {}; state.pread = s.pread || {}; state.pq = s.pq || {}; state.welcomed = !!s.welcomed; state.mark = s.mark || null; state.srs = s.srs || {}; state.look = s.look || {}; state.plan = s.plan || {}; state.hres = s.hres || {}; state.mails = s.mails || {}; state.pa = !!s.pa; state.lastSave = s.lastSave || null; } catch (e) {} }
  loadState();
  var storeOk = (function () { try { localStorage.setItem(KEY + "_t", "1"); localStorage.removeItem(KEY + "_t"); return true; } catch (e) { return false; } })();
  var SYN = {
    A: { name: "Typ A · Verb ans Ende", rule: "Subordinate clause: the conjugated verb goes to the end of the clause." },
    B: { name: "Typ B · Position 0 (ADUSO)", rule: "Joins two main clauses, or two words or phrases. It doesn't count as position 1, so the word order stays normal." },
    C: { name: "Typ C · Inversion", rule: "This word is in position 1, so the verb comes right after it and the subject follows." },
    Cm: { name: "Typ C · mitten im Satz", rule: "Here the word is not in position 1, so nothing flips. The verb is already in position 2." },
    D: { name: "Typ D · zweiteilig", rule: "Two-part connector. For je … desto, the je-part has the verb at the end and the desto-part flips." },
    Z: { name: "zu + Infinitiv", rule: "No subject in this part. zu + the infinitive goes to the end." },
    R: { name: "Relativsatz", rule: "Relative clause: the conjugated verb goes to the end." },
    Wd: { name: "W-Frage", rule: "Direct question: the question word is in position 1 and the verb comes next." },
    Wi: { name: "Indirekte Frage", rule: "Indirect question after a comma: the conjugated verb goes to the end." },
    E: { name: "Typ E · Präposition", rule: "Preposition + noun, not a clause, so it moves no verb. Watch the case." }
  };
  var GROUPS = [
    ["A", "Typ A · Verb ans Ende", "Subordinating conjunctions start a side clause. The conjugated verb goes to the end, and there's a comma between the clauses. If the side clause comes first, the main clause starts with its verb (verb, verb).", "Weil ich krank bin, bleibe ich zu Hause."],
    ["B", "Typ B · Position 0 (ADUSO)", "aber, denn, und, sondern, oder (+ doch). They join two main clauses (or two words or phrases) but don't count as position 1, so nothing changes.", "Ich bleibe zu Hause, denn ich bin krank."],
    ["C", "Typ C · Inversion (FLIP)", "Adverbs that link sentences. In position 1 they push the verb right after them, and the subject comes after the verb. In the middle of a clause nothing flips.", "Ich bin krank. Deshalb bleibe ich zu Hause."],
    ["D", "Typ D · Zweiteilige Konnektoren", "Two parts that belong together.", "Je länger ich lerne, desto besser verstehe ich."],
    ["Z", "zu + Infinitiv", "Only when both parts have the same subject. No subject in the zu-part, and zu + infinitive goes to the end. With a different subject use damit, ohne dass, statt dass (A).", "Ich lerne viel, um die Prüfung zu bestehen."],
    ["R", "Relativsätze", "A relative clause describes a noun. The conjugated verb goes to the end.", "Die Frau, die neben mir wohnt, ist sehr nett."],
    ["W", "W-Wörter: direkte und indirekte Fragen", "Direct question: W-word in position 1, then the verb. Indirect question (after a comma, Ich weiß nicht, …): the verb goes to the end.", "Warum kommst du? / Ich weiß nicht, warum er kommt."],
    ["E", "Typ E · Präpositionen statt Nebensatz", "These take a noun (watch the case), not a clause. They move no verb. At the start, the preposition and its noun together fill position 1, so the verb comes next.", "Trotz des Regens gehen wir spazieren."],
    ["X", "Nur erkennen (B2)", "Not on the B1 list. You may see them in texts, so it's enough to recognize them.", ""]
  ];
  function save() { state.v = 2; try { var raw = JSON.stringify(state); localStorage.setItem(KEY, raw); lastRaw = raw; } catch (e) { storeOk = false; storeWarn(); } }
  function syncFromStorage() {
    var raw;
    try { raw = localStorage.getItem(KEY); } catch (e) { return; }
    if (raw === lastRaw) return;
    loadState(raw); sess = null; popping = true;
    try { renderRoute(); } finally { popping = false; }
  }
  function storeWarn() {
    if (storeOk || document.getElementById("storeWarn")) return;
    var d = document.createElement("div"), m = document.getElementById("main");
    d.id = "storeWarn"; d.className = "storewarn"; d.setAttribute("role", "alert");
    d.textContent = "Achtung: Dieser Browser speichert gerade keinen Fortschritt, zum Beispiel in einem privaten Fenster. Sichere ihn mit „Fortschritt sichern“ (unten bei Themen), bevor du die Seite schließt.";
    m.parentNode.insertBefore(d, m);
  }
  function askPersist() {
    if (state.pa || !storeOk || !/^https?:$/.test(location.protocol) || !(navigator.storage && navigator.storage.persist)) return;
    state.pa = true; save();
    try { navigator.storage.persist().catch(function () {}); } catch (e) {}
  }

  function exportProgress() {
    state.lastSave = todayStr(); save();
    var data = { app: "b1VocabStories", v: 2, saved: new Date().toISOString(), built: DATA.built, state: state };
    var blob = new Blob([JSON.stringify(data, null, 1)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "b1-fortschritt-" + new Date().toISOString().slice(0, 10) + ".json";
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  function mergeState(s) {
    ["read", "pread"].forEach(function (k) { var o = s[k] || {}; Object.keys(o).forEach(function (n) { if (o[n]) state[k][n] = true; }); });
    ["quiz", "pq", "drill", "ver"].forEach(function (k) { var o = s[k] || {}; Object.keys(o).forEach(function (n) { if (state[k][n] === undefined) state[k][n] = o[n]; }); });
    if (!state.last && s.last) state.last = s.last;
    if (s.en) state.en = true;
    if (s.syn) state.syn = true;
    if (s.welcomed) state.welcomed = true;
    if (!state.mark && s.mark) state.mark = s.mark;
    var ss = s.srs || {};
    Object.keys(ss).forEach(function (k) { var a = state.srs[k], b = ss[k]; if (!a || (b[1] > a[1] && b[0] >= 1)) state.srs[k] = b; });
    var lk = s.look || {};
    Object.keys(lk).forEach(function (k) { if (!state.look[k] || lk[k] > state.look[k]) state.look[k] = lk[k]; });
    ["hres", "mails"].forEach(function (k) { var o = s[k] || {}; Object.keys(o).forEach(function (n) { if (state[k][n] === undefined || (o[n].done && !state[k][n].done)) state[k][n] = o[n]; }); });
    var pl = s.plan || {};
    if (!state.plan || typeof state.plan !== "object") state.plan = {};
    if (typeof state.plan.size !== "number" && typeof pl.size === "number") state.plan.size = pl.size;
    state.plan.log = state.plan.log || {};
    Object.keys(pl.log || {}).forEach(function (d) { var a = state.plan.log[d] || {}, b = pl.log[d]; Object.keys(b).forEach(function (k) { if (a[k] === undefined) a[k] = b[k]; }); state.plan.log[d] = a; });
  }

  function importProgress(file, done) {
    var r = new FileReader();
    r.onload = function () {
      try {
        var d = JSON.parse(r.result);
        if (!d || d.app !== "b1VocabStories" || typeof d.state !== "object") throw new Error("not a backup");
        mergeState(d.state);
        save();
        done(true);
      } catch (e) { done(false); }
    };
    r.onerror = function () { done(false); };
    r.readAsText(file);
  }

  function progressTools(noReset) {
    return '<div class="saverow"><button id="saveProg" title="Lädt eine kleine Sicherungsdatei herunter">Fortschritt sichern</button><label class="btn" title="Eine Sicherungsdatei auswählen">Fortschritt laden<input type="file" id="loadProg" accept=".json,application/json" style="display:none"></label><span class="hint" id="progMsg"></span></div>'
      + '<p class="hint">' + (state.lastSave ? "Zuletzt gesichert: " + state.lastSave.split("-").reverse().join(".") + ". " : "Noch nie gesichert. ") + "Version vom " + DATA.built.split("-").reverse().join(".") + ". " + (/^https?:$/.test(location.protocol) ? "Auf der Website kommt jede neue Version von selbst." : "Neue Version bekommen? Vorher „Fortschritt sichern“, dann in der neuen Datei „Fortschritt laden“.") + ' Details unter „Hilfe“.</p>' + (noReset ? "" : '<p class="hint"><a href="#" class="toReset">Fortschritt zurücksetzen …</a></p>');
  }

  function wireProgressTools(after) {
    var sp = document.getElementById("saveProg"), lp = document.getElementById("loadProg"), msg = document.getElementById("progMsg");
    each(main.querySelectorAll(".toReset"), function (a) { a.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); showReset(); }); });
    if (sp) sp.addEventListener("click", function (ev) { ev.stopPropagation(); exportProgress(); msg.textContent = "Gesichert: Die Datei ist in deinem Download-Ordner."; });
    if (lp) lp.addEventListener("change", function () {
      if (!lp.files || !lp.files[0]) return;
      importProgress(lp.files[0], function (ok) {
        if (ok) after();
        var m = document.getElementById("progMsg");
        if (m) m.textContent = ok ? "Geladen: Dein Fortschritt ist wieder da." : "Das ist keine Sicherungsdatei von dieser Seite.";
      });
    });
  }
  var main = document.getElementById("main");
  var card = document.getElementById("card");
  var cBody = document.getElementById("cBody");
  var current = null, curVer = "l", curOnly = null, openWord = null;
  var WORD = /[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*/g;
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function each(list, fn) { Array.prototype.forEach.call(list, fn); }
  function byNum(n) { for (var i = 0; i < DATA.stories.length; i++) if (DATA.stories[i].n === n) return i; return -1; }
  function readCount() { var c = 0; DATA.stories.forEach(function (s) { if (state.read[s.n]) c++; }); return c; }
  function total(r) { return r.reduce(function (a, b) { return a + b; }, 0); }
  function markOf() { return state.mark || (state.syn ? "syn" : state.en ? "en" : "b1"); }
  function setMark(m) {
    state.mark = m; state.en = m === "en"; state.syn = m === "syn";
    document.body.classList.toggle("showen", state.en);
    document.body.classList.toggle("showsyn", state.syn);
    document.body.classList.toggle("plainw", m === "off");
    each(document.querySelectorAll(".markSel"), function (x) { x.value = m; });
    each(document.querySelectorAll(".synT"), function (b) { b.textContent = "Satzbau: " + (state.syn ? "an" : "aus"); b.classList.toggle("on", state.syn); });
    save();
  }
  function setEn(on) { setMark(on ? "en" : state.syn ? "syn" : "b1"); }
  var booted = false, popping = false, lastQuery = "";
  function setRoute(h, replace) {
    if (popping) return;
    try {
      if (!booted) { history.replaceState({ y: 0 }, "", h); return; }
      if (location.hash === h) return;
      history.replaceState({ y: window.scrollY }, "", location.href);
      if (replace) history.replaceState({ y: 0 }, "", h); else history.pushState({ y: 0 }, "", h);
    } catch (e) { if (location.hash !== h) location.hash = h; }
  }
  function routeParts() { return (location.hash || "").replace(/^#\/?/, "").split("/"); }
  function renderRoute() {
    var m = routeParts(), v = m[0] || "heute";
    if (v === "themen") showToc();
    else if ((v === "story" || v === "lesen") && m[1] && byNum(m[1]) >= 0) {
      fromDay = v === "lesen";
      showStory(m[1], v === "lesen" ? "p" : m[2] === "l" || m[2] === "p" ? m[2] : undefined, v === "lesen" && (m[2] === "A" || m[2] === "B") ? m[2] : undefined);
    }
    else if (v === "wortliste") showIndex();
    else if (v === "satzbau") { if (m[1] === "uebung") showSynDrill(); else showSyntax(); }
    else if (v === "hilfe") showHelp();
    else if (v === "zuruecksetzen") showReset();
    else if (v === "woerter") { if (sess) showWords(); else startWords(); }
    else if (v === "hoeren") showHoeren(m[1]);
    else if (v === "schreiben") showMail(m[1]);
    else showDay();
  }
  window.addEventListener("popstate", function (ev) {
    popping = true;
    try { renderRoute(); } finally { popping = false; }
    var y = ev.state && ev.state.y;
    if (y) window.scrollTo(0, y);
  });
  function setNav(id) { each(document.querySelectorAll(".tabs button"), function (b) { b.classList.toggle("cur", b.id === id); if (b.id === id) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); }); }
  function isB1(ids) { return ids.split(",").some(function (i) { var w = DATA.words[i]; return w && (w.l === "B1" || w.l === "X" || w.l === "AT"); }); }
  function glossOf(id) { var go = curVer === "p" && DATA.pr[current] ? DATA.pr[current].go : null; return (go && go[id]) || (DATA.words[id] || {}).g || ""; }
  function lvlName(l) { return l === "X" ? "extra" : l; }
  function verOf(n) { return DATA.pr[n] ? state.ver[n] || "p" : "l"; }
  function pqTotal(n) { var r = state.pq[n] || {}, a = 0, c = 0; ["A", "B"].forEach(function (k) { if (r[k]) { a += total(r[k]); c += r[k].length; } }); return c ? a + "/" + c : ""; }

  function plain(text) {
    var out = "", last = 0, m;
    WORD.lastIndex = 0;
    while ((m = WORD.exec(text))) {
      out += esc(text.slice(last, m.index)) + (m[0].length < 2 ? esc(m[0]) : '<span class="n">' + esc(m[0]) + "</span>");
      last = m.index + m[0].length;
    }
    return out + esc(text.slice(last));
  }

  function roleOf(role) {
    if (!role) return { cls: "", attr: "" };
    var m = role.split(":"), t = m[0].slice(1);
    if (role.charAt(0) === "k") return { cls: " sk sk-" + t, attr: ' data-k="' + m[1] + '" data-kt="' + t + '" data-key="' + esc(m.slice(2).join(":")) + '"' };
    return { cls: " sv sv-" + t, attr: ' data-v="' + m[1] + '"' };
  }

  function renderSegs(segs, tap) {
    return segs.map(function (seg) {
      if (typeof seg === "string") return tap ? plain(seg) : esc(seg);
      var form = seg[0], ids = seg[1], flag = seg[2] || "";
      if (!tap) return esc(form);
      var r = roleOf(seg[4]);
      if (flag === "p") return '<span class="p' + r.cls + '"' + r.attr + ' data-form="' + esc(form) + '">' + esc(form) + "</span>";
      if (flag === "g") return '<span class="gw' + r.cls + '"' + r.attr + ' data-form="' + esc(form) + '" data-g="' + esc(seg[3] || "") + '">' + esc(form) + "</span>";
      if (flag === "r") return '<span class="n' + r.cls + '"' + r.attr + ' data-form="' + esc(form) + '">' + esc(form) + "</span>";
      var bold = flag !== "c" && isB1(ids);
      var g = bold ? glossOf(ids.split(",")[0]) : "";
      return '<span class="' + (bold ? "w" : "b") + r.cls + '"' + r.attr + ' data-id="' + ids + '" data-f="' + flag + '" data-form="' + esc(form) + '">' + esc(form) + (bold ? '<span class="gl">(' + esc(g) + ")</span>" : "") + "</span>";
    }).join("");
  }

  function setSyn(on) { setMark(on ? "syn" : state.en ? "en" : "b1"); }

  function itemFor(key, kt) {
    var t = kt === "Cm" ? "C" : (kt === "Wd" || kt === "Wi") ? "W" : kt;
    var list = DATA.syn.items;
    for (var i = 0; i < list.length; i++) if (list[i].w === key && list[i].t === t) return list[i];
    for (var j = 0; j < list.length; j++) if (list[j].w === key) return list[j];
    return null;
  }

  function synBox(el) {
    var link = el.getAttribute("data-k"), kt = el.getAttribute("data-kt"), key = el.getAttribute("data-key");
    var info = SYN[kt] || { name: "", rule: "" };
    var verbs = main.querySelectorAll('[data-v="' + link + '"]');
    var vt = Array.prototype.map.call(verbs, function (x) { return x.getAttribute("data-form") || x.textContent; }).join(" … ");
    each(verbs, function (x) { x.classList.add("synsel"); });
    el.classList.add("synsel");
    return '<div class="synbox sb-' + kt + '"><b>' + esc(info.name) + "</b><div>" + esc(info.rule) + "</div>" + (vt ? "<div>Verb hier: <b>" + esc(vt) + "</b></div>" : "") + '<a class="synmore" data-key="' + esc(key) + '" data-kt="' + kt + '">Mehr dazu in „Satzbau“</a></div>';
  }

  function verbBox(el) {
    var k = main.querySelector('[data-k="' + el.getAttribute("data-v") + '"]');
    if (!k) return "";
    var kt = k.getAttribute("data-kt"), info = SYN[kt] || { rule: "" };
    k.classList.add("synsel"); el.classList.add("synsel");
    return '<div class="synbox sb-' + kt + '">Dieses Verb steht hier wegen <b>' + esc(k.getAttribute("data-form") || k.textContent) + "</b>. " + esc(info.rule) + "</div>";
  }

  function showToc() {
    setRoute("#/themen");
    current = null; hideCard(); fromDay = false; setNav("bToc");
    var done = readCount(), all = DATA.stories.length;
    var pn = Object.keys(DATA.pr).length, pdone = Object.keys(DATA.pr).filter(function (n) { return state.pread[n]; }).length;
    var h = '<article class="themen"><h2>Themen</h2><p class="hint">' + all + ' Themen für die B1-Prüfung, jedes zweimal: als <b>leichte Geschichte</b> und als <b>Prüfungsversion</b> wie im telc-Test. Tippe auf ein Wort, dann siehst du die Bedeutung.</p>';
    h += '<div class="hint">Gelesen: Leicht ' + done + ' von ' + all + (pn ? " · Prüfung " + pdone + " von " + pn : "") + '</div><div class="progress"><div style="width:' + Math.round(100 * done / all) + '%"></div></div><ul class="toc">';
    DATA.stories.forEach(function (s) {
      var q = state.quiz[s.n], Q = DATA.quiz[s.n], P = DATA.pr[s.n], pt = pqTotal(s.n);
      var lc = '<span class="chip lchip' + (state.read[s.n] ? " done" : "") + '">Leicht' + (state.read[s.n] ? " ✓" : "") + (q && q.r && Q ? " · Quiz " + total(q.r) + "/" + Q.length : "") + "</span>";
      var pc = P ? '<span class="chip pchip' + (state.pread[s.n] ? " done" : "") + '">Prüfung' + (state.pread[s.n] ? " ✓" : "") + (pt ? " · Quiz " + pt : "") + "</span>" : "";
      h += '<li data-n="' + s.n + '"><span class="num">' + s.n + '</span><span class="tt"><b>' + esc(s.t) + '</b><span class="meta chips">' + lc + pc + "</span></span></li>";
    });
    h += "</ul>" + progressTools() + "</article>";
    main.innerHTML = h;
    each(main.querySelectorAll(".toc li"), function (li) { li.addEventListener("click", function () { showStory(li.getAttribute("data-n")); }); });
    wireProgressTools(showToc);
    window.scrollTo(0, 0);
  }

  function showReset() {
    setRoute("#/zuruecksetzen");
    current = null; hideCard(); setNav("");
    var nRead = Object.keys(state.read).length + Object.keys(state.pread).length, nQuiz = Object.keys(state.quiz).length + Object.keys(state.pq).length;
    var nWords = Object.keys(state.srs || {}).length, nDays = Object.keys((state.plan || {}).log || {}).length;
    function n(k, one, many) { return k + " " + (k === 1 ? one : many); }
    var h = '<article class="reset"><h2>Fortschritt zurücksetzen</h2>'
      + "<p>" + (nRead + nQuiz + nWords + nDays ? "In diesem Browser gespeichert: " + n(nRead, "gelesener Text", "gelesene Texte") + ", " + n(nQuiz, "Quiz-Ergebnis", "Quiz-Ergebnisse") + ", " + n(nWords, "Wort zum Üben", "Wörter zum Üben") + ", " + n(nDays, "Lerntag", "Lerntage") + "." : "In diesem Browser ist noch kein Fortschritt gespeichert.") + "</p>"
      + '<p class="hint">Sichere deinen Fortschritt zuerst, dann kannst du ihn später wieder laden.</p>' + progressTools(true)
      + '<div class="rbtns"><button id="resetPlan">Nur den Tagesplan zurücksetzen</button><button id="resetAll" class="danger">Alles zurücksetzen</button></div>'
      + '<p class="hint"><b>Nur den Tagesplan:</b> Wörter üben, Hören, Schreiben und die Lerntage fangen von vorn an. Gelesene Texte und Quiz-Ergebnisse bleiben. <b>Alles:</b> Die Seite ist danach wie neu.</p>'
      + '<p><a href="#" class="toDay">Abbrechen</a></p></article>';
    main.innerHTML = h;
    wireProgressTools(showReset);
    wireBack();
    document.getElementById("resetPlan").addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (!window.confirm("Den Tagesplan wirklich zurücksetzen? Wörter üben, Hören, Schreiben und die Lerntage werden gelöscht.")) return;
      state.srs = {}; state.look = {}; state.plan = { size: plan().size, log: {} }; state.hres = {}; state.mails = {}; sess = null;
      save();
      showDay();
    });
    document.getElementById("resetAll").addEventListener("click", function (ev) {
      ev.stopPropagation();
      if (!window.confirm("Wirklich alles zurücksetzen? Dein ganzer Fortschritt in diesem Browser wird gelöscht.")) return;
      try { localStorage.removeItem(KEY); } catch (e) {}
      try { history.replaceState(null, "", "#/heute"); } catch (e) {}
      location.reload();
    });
    window.scrollTo(0, 0);
  }

  function showHelp() {
    setRoute("#/hilfe");
    current = null; hideCard(); setNav("bHelp");
    state.welcomed = true; save();
    var np = Object.keys(DATA.pr).length;
    var h = '<article class="help"><h2>How to use this page</h2>';
    h += '<p class="hint">Kurz auf Deutsch: Thema wählen, lesen, unbekannte Wörter antippen, dann die Aufgaben lösen und „Antworten prüfen“. Dein Fortschritt bleibt in diesem Browser gespeichert.</p>';
    h += "<h3>What this is</h3><p>Reading practice for the B1 exam (telc, Goethe or ÖSD). There are " + DATA.stories.length + " topics, and each one comes in two versions:</p><ul>"
      + "<li><b>Leicht</b>: an easy story with the everyday words of the topic.</li>"
      + (np ? "<li><b>Prüfung</b>: a harder set like the telc reading test: a newspaper article plus short news, ads, an interview or opinions, with exam-style tasks.</li>" : "")
      + "</ul><p>Together they contain every word of the official B1 word list (Goethe-Institut and ÖSD, 2016): the 1,847 new B1 words plus the A1 and A2 words. The Prüfung sets also use some common exam words that aren't on the list, and some Austrian words. The texts and tasks were written for practice. They are not official exam material.</p>";
    h += "<h3>The daily plan (Heute)</h3><ul>"
      + "<li><b>Heute</b> (the first button at the top, and the start page) gives you a small set of tasks for today: <b>Wörter üben</b> (spaced review), <b>Hören</b> (a listening mini test), <b>Lesen</b> (one part of a Prüfung set) and <b>Schreiben</b> (a mini email, and once a week a full exam email).</li>"
      + "<li>Pick how much time you have: 50, 30, 15 or 5 minutes. <b>Weiter</b> takes you from one task to the next. Missed days don't pile up. The plan just continues where you stopped.</li>"
      + "<li><b>Wörter üben</b>: words come from <b>☆ Merken</b> on a word card, from words you tapped while reading, and from the next reading texts, in order. Think of the meaning first, then click <b>Zeigen</b>. Words you know come back after longer and longer breaks (1, 3, 7, 14, 30, 60 days). <b>Für Anki exportieren</b> saves your words for the Anki app.</li>"
      + "<li><b>Hören</b> uses the audio of your Klett books <i>Mit Erfolg zu telc Deutsch B1, Testbuch</i> and <i>Mit Erfolg zum Zertifikat Deutsch B1, Übungsbuch</i>. The button opens the track on allango.net in a new tab. The statements here are new and written like the exam, with its traps. Each answer shows where it is in the audio (minute and second). After these 23 tasks, Hören goes on with free practice from the exam makers and DW: the DW telc B1 course, the official telc and ÖSD mock tests, the Goethe practice tests and then the DW course <i>Nicos Weg B1</i>. They open on the original website. The task tells you which questions to do, where the audio starts and stops, and where the answers are. Afterwards, type how many you got right.</li>"
      + "<li><b>Schreiben</b>: write your email in the page. <b>Feedback mit Claude</b> or <b>mit ChatGPT</b> copies your email together with the task and a grading guide (the official telc criteria), and opens the site. They work once your email has at least 15 words. Paste it there (Ctrl+V, on a Mac Cmd+V) and send it. You need your own account there.</li>"
      + "<li>Speaking isn't part of the plan. Practice it with a partner.</li></ul>";
    h += "<h3>Getting started</h3><ol>"
      + "<li>Start with <b>Heute</b> and follow <b>Weiter</b>. To read freely, click <b>Themen</b> and pick a topic. The most important exam topics come first.</li>"
      + "<li>At the top of a topic, choose <b>Leicht</b> or <b>Prüfung</b>. New to B1? Start with Leicht. Preparing for the exam? Use Prüfung, and switch to Leicht when a text feels too hard.</li>"
      + "<li>Click <b>Als gelesen markieren</b> at the end. A ✓ then shows in <b>Themen</b>. Use ← and → on the keyboard to go to the previous or next topic.</li></ol>";
    h += '<h3>Reading and looking up words</h3><ul>'
      + '<li><b class="w">Marked words</b> are the B1 words to learn. Try to guess the meaning from the sentence first.</li>'
      + "<li><b>Tap or click any word</b>, bold or not, to see its dictionary form and the English meaning. <b>Esc</b> or ✕ closes the card.</li>"
      + '<li>Words that aren\'t on the B1 list still get their meaning, marked <span class="lvl lvl-off">nicht auf der Liste</span>. They\'re good to understand, because exam texts use some of them too, but you don\'t need to learn them actively. If only the form is new (like <i>mussten</i>), the card also shows the list word (<i>müssen</i>).</li>'
      + '<li>The card shows the word\'s level on the official list: <span class="lvl">A1</span> <span class="lvl">A2</span> <span class="lvl lvl-B1">B1</span>. <span class="lvl lvl-X">extra</span> means it\'s not on the list, but typical for exam texts. <span class="lvl lvl-AT">AT</span> is an Austrian word, and the card shows the word used in Germany.</li>'
      + "<li><b>Markieren</b> (at the top of a topic) changes the marks: <i>B1-Wörter</i> (the default), <i>B1-Wörter mit Englisch</i> (the English next to each marked word, for review, not for a first read), <i>Satzbau</i> (connectors and the verbs they move) or <i>Nichts, wie in der Prüfung</i> (a clean text, every word still tappable).</li></ul>";
    h += "<h3>The quizzes work like the exam</h3><ul>"
      + "<li><b>Leicht</b>: 5 questions with a, b or c, like Leseverstehen Teil 2.</li>"
      + (np ? "<li><b>Prüfung</b>: Teil A has 5 questions with a, b or c on the article. Teil B matches headlines to short news (like Teil 1), matches ads to situations, where <b>x</b> means no ad fits (like Teil 3), or asks richtig or falsch about an interview or opinions.</li>" : "")
      + "<li>Click your answers. Nothing shows right or wrong yet, and you can change your mind. When every question has an answer, <b>Antworten prüfen</b> turns on.</li>"
      + "<li>Then you see everything at once: green is right, red is your wrong pick. Each question shows the sentence from the text that proves the answer and a short reason in English. <b>Stelle im Text zeigen</b> jumps to that spot. <b>Nochmal von vorn</b> starts again.</li>"
      + "<li>Your scores show in <b>Themen</b>, so you can see which topics need another round.</li></ul>";
    h += "<h3>Satzbau and Wortliste</h3><ul>"
      + "<li><b>Satzbau</b> lists the connectors that move the verb (<i>weil, deshalb, trotzdem, obwohl</i> …), with example sentences from the stories, and a 20-gap drill like the Sprachbausteine. <b>Markieren: Satzbau</b> colors these words in the texts and boxes the verb they move.</li>"
      + "<li><b>Wortliste</b> searches the whole word list in German or English. The numbers after a word link to where it appears: <b>05</b> is Leicht story 5, <b>P05</b> is the Prüfung version of topic 5.</li></ul>";
    h += "<h3>Your progress</h3><ul>"
      + "<li>Read marks, quiz scores and settings are saved automatically <b>in this browser on this device</b>. There's no account, nothing is uploaded, and the page works offline. Only Hören and the email feedback need the internet.</li>"
      + "<li>A different browser or device starts fresh. Clearing your browser data deletes the progress.</li>"
      + "<li><b>Fortschritt sichern</b> downloads a small backup file of your progress. <b>Fortschritt laden</b> reads it back in, and it only adds: nothing you already have is lost.</li>"
      + "<li><b>Fortschritt zurücksetzen</b> (the link below, and at the bottom of Themen) starts over: only the daily plan, or everything. Save a backup first if you might want it back.</li>"
      + "<li><b>File or website:</b> the page works as a downloaded file and as a website. Each one keeps its own progress in the browser. To move your progress, click <b>Fortschritt sichern</b> in the one and <b>Fortschritt laden</b> in the other.</li>"
      + "<li><b>iPhone and iPad:</b> Safari can delete the data of a website you haven't opened for 7 days. Add the page to your Home Screen, or save a backup now and then. The date of your last backup is next to the buttons.</li></ul>"
      + "<h3>Getting a newer version</h3><p>On the website you always get the newest version, and your progress stays. For the downloaded file:</p><ol>"
      + "<li>In the old file, click <b>Fortschritt sichern</b> (at the bottom of Themen or here).</li>"
      + "<li>Save the new file with <b>the same name in the same folder</b>, so it replaces the old one, and open it in the same browser. Usually your progress is simply still there.</li>"
      + "<li>If anything is missing, click <b>Fortschritt laden</b> in the new file and pick the backup from step 1.</li></ol>"
      + progressTools();
    h += "<h3>A good routine</h3><ol>"
      + "<li>Open <b>Heute</b> every day, even if it's only for 5 minutes.</li>"
      + "<li>In a Prüfung part, do the tasks first and look up words afterwards, like in the exam.</li>"
      + "<li>Read the reasons after <b>Antworten prüfen</b>, and click <b>☆ Merken</b> on the words you want to keep. They come back in <b>Wörter üben</b>.</li></ol>";
    h += "<h3>Opening the file</h3><ul>"
      + "<li>Best on a laptop or computer: double-click the file and it opens in your browser (Chrome, Firefox, Safari or Edge).</li>"
      + "<li>On a phone, the preview inside WhatsApp or Mail may show an empty page. Save the file and open it in a browser, or use a computer.</li></ul>";
    h += '<p><button id="helpToc">Zu den Themen</button></p></article>';
    main.innerHTML = h;
    document.getElementById("helpToc").addEventListener("click", function (ev) { ev.stopPropagation(); showToc(); });
    wireProgressTools(showHelp);
    window.scrollTo(0, 0);
  }

  function lastHtml(r, n) { return r ? '<p class="hint">Letztes Ergebnis: ' + total(r) + " von " + n + ".</p>" : ""; }

  var EXAM_HINT = "Du siehst erst am Ende, was richtig ist. Bis dahin kannst du deine Antworten noch ändern, wie in der Prüfung.";

  function abcHtml(sid, scoreId, Q, title, hint, prev) {
    var h = '<section class="quiz" id="' + sid + '"><h3>' + title + '</h3><p class="hint">' + hint + "</p>" + lastHtml(prev, Q.length);
    Q.forEach(function (q, k) {
      h += '<div class="qq" data-k="' + k + '"><div class="qt"><b>' + (k + 1) + ".</b> " + renderSegs(q.q, true) + '</div><div class="opts">';
      q.o.forEach(function (o, j) { h += '<button class="opt" data-j="' + j + '"><b>' + "abc".charAt(j) + ')</b> <span class="ot">' + renderSegs(o, false) + "</span></button>"; });
      h += '</div><div class="fb"></div></div>';
    });
    return h + '<div class="score" id="' + scoreId + '"></div></section>';
  }

  function checkBar(id) {
    return '<div class="checkbar"><button class="check" id="' + id + '" disabled>Antworten prüfen</button><span class="left"></span></div>';
  }

  function renderQuiz(n, Q) {
    var prev = state.quiz[n];
    return abcHtml("quiz", "qscore", Q, "Verständnisfragen", "Wie im Test (Leseverstehen, Teil 2): Welche Lösung ist richtig, a, b oder c? " + EXAM_HINT, prev && prev.r) + checkBar("qcheck");
  }

  function flashPara(pi) {
    var p = document.getElementById("p" + pi);
    if (!p) return;
    p.scrollIntoView({ block: "center", behavior: "smooth" });
    p.classList.add("flash");
    setTimeout(function () { p.classList.remove("flash"); }, 2600);
  }

  function wireQuiz(n) {
    var Q = DATA.quiz[n];
    if (!Q) return;
    examQuiz(n, [{ sec: document.getElementById("quiz"), kind: "abc", items: Q, lab: "" }], document.getElementById("qcheck"), function (res) { state.quiz[n] = { r: res[0] }; if (!(plan().log[todayStr()] || {}).l) markDone("l", n + "L"); else save(); });
  }

  function showLink(fb, pi) {
    var a = fb.querySelector(".show");
    if (a && pi >= 0) a.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); flashPara(pi); });
    else if (a) a.style.display = "none";
  }

  function evHtml(q) { var quoted = /^„/.test(q.ev); return '<div class="ev">' + (quoted ? "" : "„") + esc(q.ev) + (quoted ? "" : "“") + '</div><div class="why">' + esc(q.why) + '</div><a class="show" href="#">Stelle im Text zeigen</a>'; }

  function pickOf(kind, b) { return kind === "abc" ? +b.getAttribute("data-j") : kind === "rf" ? b.getAttribute("data-rf") === "1" : b.getAttribute("data-l"); }

  function answerName(kind, a) { return kind === "abc" ? "abc".charAt(a) + ")" : kind === "rf" ? (a ? "richtig" : "falsch") : a === "x" ? "x (keine Anzeige passt)" : a; }

  function examQuiz(n, parts, btn, onDone, opt) {
    var left = btn.parentNode.querySelector(".left"), checked = false;
    var picks = parts.map(function (p) { return p.items.map(function () { return null; }); });
    function open() { var c = 0; picks.forEach(function (r) { r.forEach(function (x) { if (x === null) c++; }); }); return c; }
    function update() {
      var c = open();
      btn.disabled = c > 0;
      left.innerHTML = c ? '<a href="#" class="toOpen">Noch ' + c + (c === 1 ? " Frage" : " Fragen") + " offen ›</a>" : "Alle Fragen beantwortet.";
      var to = left.querySelector(".toOpen");
      if (to) to.addEventListener("click", function (ev) {
        ev.preventDefault(); ev.stopPropagation();
        for (var pi = 0; pi < picks.length; pi++) for (var k = 0; k < picks[pi].length; k++) if (picks[pi][k] === null) {
          var box = parts[pi].sec.querySelector('.qq[data-k="' + k + '"]');
          if (box) { box.scrollIntoView({ block: "center", behavior: "smooth" }); box.classList.add("flashq"); setTimeout(function () { box.classList.remove("flashq"); }, 1600); }
          return;
        }
      });
    }
    parts.forEach(function (p, pi) {
      each(p.sec.querySelectorAll(".qq"), function (box) {
        var k = +box.getAttribute("data-k");
        each(box.querySelectorAll(".opt"), function (b) {
          b.addEventListener("click", function () {
            if (checked) return;
            picks[pi][k] = pickOf(p.kind, b);
            each(box.querySelectorAll(".opt"), function (x) { x.classList.toggle("picked", x === b); });
            update();
          });
        });
      });
    });
    btn.addEventListener("click", function () {
      if (checked || open()) return;
      checked = true;
      var res = parts.map(function (p, pi) {
        var r = p.items.map(function (it, k) {
          var box = p.sec.querySelector('.qq[data-k="' + k + '"]'), fb = box.querySelector(".fb"), mine = picks[pi][k], ok = mine === it.a;
          each(box.querySelectorAll(".opt"), function (b) {
            var v = pickOf(p.kind, b);
            b.classList.remove("picked");
            b.classList.add("locked");
            if (v === it.a) b.classList.add("yes");
            else if (v === mine) b.classList.add("no");
            if (p.kind === "abc") b.querySelector(".ot").innerHTML = renderSegs(it.o[v], true);
          });
          fb.innerHTML = (ok ? '<div class="ok">Richtig!</div>' : p.kind === "rf" ? '<div class="sol">Falsch. Die Aussage ist ' + (it.a ? "richtig" : "falsch") + ".</div>" : '<div class="sol">Falsch. Richtig ist ' + esc(answerName(p.kind, it.a)) + ".</div>") + (opt && opt.ev ? opt.ev(it) : evHtml(it));
          showLink(fb, it.pi);
          return ok ? 1 : 0;
        });
        p.sec.querySelector(".score").textContent = "Ergebnis: " + total(r) + " von " + r.length + ".";
        return r;
      });
      onDone(res);
      var all = [].concat.apply([], res);
      btn.style.display = "none";
      left.innerHTML = "<b>Ergebnis: " + total(all) + " von " + all.length + "</b>" + (parts.length > 1 ? " (" + parts.map(function (p, i) { return p.lab + ": " + total(res[i]) + " von " + res[i].length; }).join(" · ") + ")" : "") + ' <button class="small again">Nochmal von vorn</button>';
      var ver = curVer, only = curOnly;
      left.querySelector(".again").addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (opt && opt.again) { opt.again(); return; }
        showStory(n, ver, only);
        var q = main.querySelector(".quiz");
        if (q) q.scrollIntoView();
      });
    });
    update();
  }

  function rfHtml(sid, P, prev) {
    var h = '<section class="quiz" id="' + sid + '"><h3>Teil B · Richtig oder falsch?</h3><p class="hint">Lies das Interview oder die Meinungen. Ist die Aussage richtig oder falsch? Pass auf Wörter wie <i>nur, immer, vor allem, trotzdem, angeblich</i> auf.</p>' + lastHtml(prev, P.items.length);
    P.items.forEach(function (it, k) {
      h += '<div class="qq rq" data-k="' + k + '"><div class="qt"><b>' + (k + 1) + ".</b> " + renderSegs(it.s, true) + '</div><div class="rfb"><button class="opt" data-rf="1">richtig</button><button class="opt" data-rf="0">falsch</button></div><div class="fb"></div></div>';
    });
    return h + '<div class="score" id="' + sid + '-score"></div></section>';
  }

  function matchHtml(sid, P, prev) {
    var heads = P.kind === "headlines";
    var h = '<section class="quiz" id="' + sid + '"><h3>Teil B · ' + (heads ? "Welche Überschrift passt?" : "Welche Anzeige passt?") + '</h3><p class="hint">' + (heads
      ? "Wie Leseverstehen Teil 1: Zu jedem Text passt genau eine Überschrift. Drei Überschriften bleiben übrig."
      : "Wie Leseverstehen Teil 3: Welche Anzeige passt zu welcher Situation? Jede Anzeige passt höchstens einmal. Für eine Situation gibt es keine passende Anzeige. Dann wähle <b>x</b>. Prüfe alle Details: Tag, Uhrzeit, Preis, Ort, Alter.") + "</p>" + lastHtml(prev, P.items.length);
    if (heads) h += '<ul class="heads">' + P.opts.map(function (o) { return "<li><b>" + o.id + ")</b> " + renderSegs(o.s, true) + "</li>"; }).join("") + "</ul>";
    P.items.forEach(function (it, k) {
      h += '<div class="qq mq" data-k="' + k + '"><div class="qt"><b>' + (heads ? "Text " + esc(it.id) : (k + 1) + ".") + "</b> " + (it.s.length ? renderSegs(it.s, true) : "") + '</div><div class="lets">';
      P.lets.forEach(function (l) { h += '<button class="opt let" data-l="' + l + '">' + l + "</button>"; });
      h += '</div><div class="fb"></div></div>';
    });
    return h + '<div class="score" id="' + sid + '-score"></div></section>';
  }

  function verSwitch(n, v) {
    var h = '<div class="tools">';
    if (DATA.pr[n]) h += '<div class="vsw" role="group" aria-label="Version"><button class="small' + (v === "l" ? " on" : "") + '" data-ver="l">Leicht</button><button class="small' + (v === "p" ? " on" : "") + '" data-ver="p">Prüfung</button></div>';
    h += '<label class="mk">Markieren: <select class="markSel"><option value="b1">B1-Wörter</option><option value="en">B1-Wörter mit Englisch</option><option value="syn">Satzbau (Verbposition)</option><option value="off">Nichts, wie in der Prüfung</option></select></label>';
    return h + "</div>";
  }

  function setHtml(n, s, only) {
    var P = DATA.pr[n];
    var h = "<article class=\"pr\"><h2>" + esc(s.t) + "</h2>" + verSwitch(n, "p") + '<div class="sub">' + n + " · " + esc(s.topic) + " · " + P.w + " Wörter · " + P.k + " B1-Wörter</div>";
    if (only) h += '<p class="hint onlyp">Heute nur Teil ' + only + '. <a href="#" id="allParts">Ganzes Set zeigen</a></p>';
    var inPart = false, inItem = false, partNow = null;
    P.blocks.forEach(function (b, k) {
      if (b.k === "h2") partNow = b.part;
      if (only && partNow !== only) return;
      if (b.k === "h2") {
        if (inItem) h += "</div>";
        if (inPart) h += "</section>";
        inPart = true; inItem = false;
        h += '<section class="part"><div class="plabel">Teil ' + b.part + " · " + esc(b.label) + "</div>" + (b.s.length ? '<h3 class="ph" id="p' + k + '">' + renderSegs(b.s, true) + "</h3>" : "");
      } else if (b.k === "h3") {
        if (inItem) h += "</div>";
        inItem = true;
        var t = seg_text(b.s), lab = /^\d+$/.test(t.trim()) ? "Text " + esc(t.trim()) : renderSegs(b.s, b.label !== "Meinungen");
        h += '<div class="item"><h4 id="p' + k + '">' + lab + "</h4>";
      } else {
        h += '<p id="p' + k + '">' + (b.sp ? '<b class="sp">' + esc(b.sp) + ":</b> " : "") + renderSegs(b.s, true) + "</p>";
      }
    });
    if (inItem) h += "</div>";
    if (inPart) h += "</section>";
    h += "</article>";
    var Q = DATA.pq[n], prev = state.pq[n] || {};
    if (Q) {
      Q.forEach(function (part, j) {
        var sid = j === 0 ? "pqA" : "pqB";
        if (only && (j === 0 ? "A" : "B") !== only) return;
        if (part.t === "abc") h += abcHtml(sid, sid + "-score", part.items, "Teil A · Aufgaben zum Artikel", "Wie Leseverstehen Teil 2: Welche Lösung ist richtig, a, b oder c? Die falschen Lösungen benutzen oft Wörter aus dem Text. " + EXAM_HINT + (only ? "" : " Am Ende prüfst du Teil A und Teil B zusammen."), prev.A);
        else if (part.t === "rf") h += rfHtml(sid, part, prev.B);
        else h += matchHtml(sid, part, prev.B);
      });
      h += checkBar("pcheck");
    }
    return h;
  }

  function wireSet(n, only) {
    var Q = DATA.pq[n];
    if (!Q) return;
    var parts = Q.map(function (part, j) { return { sec: document.getElementById(j === 0 ? "pqA" : "pqB"), kind: part.t, items: part.items, lab: j === 0 ? "Teil A" : "Teil B", key: j === 0 ? "A" : "B" }; })
      .filter(function (p) { return !only || p.key === only; });
    examQuiz(n, parts, document.getElementById("pcheck"), function (res) {
      var r = state.pq[n] || {};
      parts.forEach(function (p, i) { r[p.key] = res[i]; });
      state.pq[n] = r;
      if (!(plan().log[todayStr()] || {}).l) markDone("l", n + (only || "AB")); else save();
    });
    var ap = document.getElementById("allParts");
    if (ap) ap.addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); showStory(n, "p"); });
  }

  function seg_text(segs) { return segs.map(function (x) { return typeof x === "string" ? x : x[0]; }).join(""); }

  function showStory(n, ver, only) {
    var i = byNum(n); if (i < 0) return;
    var s = DATA.stories[i]; current = n; state.last = n; save(); hideCard();
    var v = ver && DATA.pr[n] ? ver : verOf(n);
    if (v !== "p") only = null;
    var rp = routeParts();
    setRoute(fromDay && only ? "#/lesen/" + n + "/" + only : "#/story/" + n + "/" + v, (rp[0] === "story" || rp[0] === "lesen") && rp[1] === n);
    curVer = v; curOnly = only || null;
    var h, rd = v === "p" ? state.pread : state.read;
    if (v === "p") h = setHtml(n, s, only);
    else {
      h = "<article><h2>" + esc(s.t) + "</h2>" + verSwitch(n, "l") + '<div class="sub">' + s.n + " · " + esc(s.topic) + " · " + s.w + " Wörter · " + s.k + " B1-Wörter</div>";
      s.p.forEach(function (p, k) { h += '<p id="p' + k + '">' + renderSegs(p, true) + "</p>"; });
      h += "</article>";
      if (DATA.quiz[n] && DATA.quiz[n].length) h += renderQuiz(n, DATA.quiz[n]);
    }
    h += '<div class="nav">';
    h += i > 0 ? '<button id="prev">← ' + DATA.stories[i - 1].n + "</button>" : "<span></span>";
    h += '<button id="mark">' + (rd[n] ? "✓ Gelesen" : "Als gelesen markieren") + "</button>";
    h += i < DATA.stories.length - 1 ? '<button id="next">' + DATA.stories[i + 1].n + " →</button>" : "<span></span>";
    h += "</div>";
    if (fromDay && curOnly) h = backLink() + h;
    main.innerHTML = h;
    setNav(fromDay && curOnly ? "bDay" : "bToc");
    wireBack();
    wireSynToggles();
    each(main.querySelectorAll(".markSel"), function (x) { x.value = markOf(); x.addEventListener("change", function () { setMark(x.value); hideCard(); }); });
    if (v === "p") wireSet(n, only); else wireQuiz(n);
    each(main.querySelectorAll(".vsw button"), function (b) {
      b.addEventListener("click", function (ev) { ev.stopPropagation(); state.ver[n] = b.getAttribute("data-ver"); save(); showStory(n); });
    });
    var p = document.getElementById("prev"), nx = document.getElementById("next");
    if (p) p.addEventListener("click", function () { showStory(DATA.stories[i - 1].n); });
    if (nx) nx.addEventListener("click", function () { showStory(DATA.stories[i + 1].n); });
    document.getElementById("mark").addEventListener("click", function () {
      rd[n] = !rd[n]; save();
      this.textContent = rd[n] ? "✓ Gelesen" : "Als gelesen markieren";
    });
    window.scrollTo(0, 0);
  }

  function offOf(form) {
    var O = DATA.off || {};
    return O[form] || O[form.toLowerCase()] || O[form.charAt(0).toUpperCase() + form.slice(1)] || null;
  }

  function offHtml(form) {
    var o = offOf(form);
    if (!o) return '<div class="more">Nicht auf der B1-Wortliste.</div>';
    var badge = o.k === "name" ? "Name" : o.k === "abbr" ? "Abkürzung" : o.k === "interj" ? "Ausdruck" : o.id ? "" : "nicht auf der Liste";
    var h = '<div class="entry">' + (badge ? '<span class="lvl lvl-off">' + badge + "</span> " : "") + '<span class="dict">' + esc(o.d) + '</span><div class="en">' + esc(o.g) + "</div></div>";
    if (o.id && DATA.words[o.id]) h += '<div class="more">Das Grundwort steht auf der Liste:</div>' + entryHtml(o.id, {});
    else if (o.k !== "name") h += '<div class="more">Nicht auf der B1-Wortliste: gut zu verstehen, aber du musst es nicht aktiv lernen.</div>';
    return h;
  }

  function entryHtml(id, seen) {
    var w = DATA.words[id];
    if (!w) return "";
    var key = w.d + "|" + w.g;
    if (seen[key]) return "";
    seen[key] = 1;
    var note = w.l === "X" ? '<div class="more">Nicht auf der B1-Liste, aber typisch für Prüfungstexte.</div>' : w.l === "AT" ? '<div class="more">Österreich. In Deutschland: ' + esc(w.de || "") + "</div>" : "";
    return '<div class="entry"><span class="lvl lvl-' + w.l + '">' + lvlName(w.l) + '</span> <span class="dict">' + esc(w.d) + '</span><div class="en">' + esc(glossOf(id)) + "</div>" + note + "</div>";
  }

  function showCard(el) {
    each(main.querySelectorAll(".sel"), function (x) { x.classList.remove("sel"); });
    var form = el.getAttribute("data-form") || el.textContent;
    var h = '<div class="form">im Text: ' + esc(form) + "</div>";
    if (el.classList.contains("p")) {
      h += '<div class="en">Name (Person, Ort oder Firma)</div>';
      el.classList.add("sel");
    } else if (el.classList.contains("gw")) {
      h += '<div class="en">' + esc(el.getAttribute("data-g")) + '</div><div class="more">Grammatikwort. Es steht nicht einzeln in der Wortliste, gehört aber zur B1-Grammatik.</div>';
      el.classList.add("sel");
    } else if (el.classList.contains("n") && el.hasAttribute("data-k")) {
      var it = itemFor(el.getAttribute("data-key"), el.getAttribute("data-kt"));
      h += '<div class="entry"><span class="lvl">' + esc(it ? it.lvl : "") + '</span> <span class="dict">' + esc(el.getAttribute("data-key")) + '</span><div class="en">' + esc(it ? it.en : "") + '</div></div><div class="more">Nicht auf der B1-Wortliste, aber häufig.</div>';
      el.classList.add("sel");
    } else if (el.classList.contains("n")) {
      h += offHtml(form);
      el.classList.add("sel");
    } else {
      var ids = el.getAttribute("data-id"), flag = el.getAttribute("data-f") || "", seen = {};
      if (flag === "c") h += '<div class="more">Zusammengesetztes Wort. Diese Teile stehen auf der Liste:</div>';
      ids.split(",").forEach(function (id) { h += entryHtml(id, seen); });
      var w = DATA.words[ids.split(",")[0]], where = w && (curVer === "p" ? w.ps : w.s);
      if (flag !== "c" && where) {
        var others = where.filter(function (x) { return x !== current; });
        if (others.length) h += '<div class="more">auch in ' + (curVer === "p" ? "Prüfung " : "Geschichte ") + others.join(", ") + "</div>";
      }
      if (flag === "c") el.classList.add("sel");
      else each(main.querySelectorAll('[data-id="' + ids + '"]'), function (x) { if (x.getAttribute("data-f") !== "c") x.classList.add("sel"); });
      el.classList.add("sel");
    }
    if (el.hasAttribute("data-k")) h += synBox(el);
    else if (el.hasAttribute("data-v")) h += verbBox(el);
    var sk = srsKeyFor(el, form);
    if (sk) { noteLookup(sk); h += starHtml(sk); }
    cBody.innerHTML = h;
    wireStar(cBody);
    var more = cBody.querySelector(".synmore");
    if (more) more.addEventListener("click", function (ev) { ev.stopPropagation(); showSyntax(more.getAttribute("data-key"), more.getAttribute("data-kt")); });
    card.style.display = "block";
    openWord = el;
    placeCard(el);
  }
  function placeCard(el) {
    var r = el.getBoundingClientRect();
    var vw = document.documentElement.clientWidth, vh = window.innerHeight;
    var cw = card.offsetWidth, ch = card.offsetHeight;
    var left = Math.max(8, Math.min(r.left, vw - cw - 8));
    var top = r.bottom + 6;
    if (top + ch > vh - 8 && r.top - ch - 6 > 64) top = r.top - ch - 6;
    card.style.left = Math.round(left + window.scrollX) + "px";
    card.style.top = Math.round(top + window.scrollY) + "px";
  }
  function hideCard() { card.style.display = "none"; openWord = null; each(main.querySelectorAll(".sel"), function (x) { x.classList.remove("sel"); }); each(main.querySelectorAll(".synsel"), function (x) { x.classList.remove("synsel"); }); }

  function wireSynToggles() {
    each(main.querySelectorAll(".synT"), function (b) { b.addEventListener("click", function (ev) { ev.stopPropagation(); setSyn(!state.syn); }); });
  }

  function exHtml(ex, t) {
    var s = ex.t, marks = [[ex.k[0], ex.k[1], "xk sk-" + t]];
    ex.v.forEach(function (v) { marks.push([v[0], v[1], "xv sv-" + t]); });
    marks.sort(function (a, b) { return a[0] - b[0]; });
    var out = "", last = 0;
    marks.forEach(function (m) { if (m[0] < last) return; out += esc(s.slice(last, m[0])) + '<b class="' + m[2] + '">' + esc(s.slice(m[0], m[1])) + "</b>"; last = m[1]; });
    out += esc(s.slice(last));
    return '<div class="ex">„' + out + '“ <a class="exgo" data-n="' + ex.n + '" data-p="' + ex.p + '">→ Geschichte ' + ex.n + "</a></div>";
  }

  function examplesFor(it) {
    var keys = it.t === "C" ? [["C", ""], ["Cm", "mitten im Satz, keine Inversion:"]] : it.t === "W" ? [["Wd", "direkte Frage:"], ["Wi", "indirekte Frage:"]] : it.t === "R" && it.w !== "der, die, das" ? [] : [[it.t, ""]];
    var h = "", total = 0;
    keys.forEach(function (k) {
      var key = k[0] + "|" + it.w, ex = DATA.syn.examples[key] || [], c = DATA.syn.counts[key] || 0;
      total += c;
      var lim = k[0] === "Cm" ? 1 : 2;
      ex.slice(0, lim).forEach(function (e, i) { h += (i === 0 && k[1] ? '<div class="exl">' + k[1] + "</div>" : "") + exHtml(e, k[0]); });
    });
    return { html: h, total: total };
  }

  function typeBadge(t) {
    var info = SYN[t] || { name: t };
    var color = t === "Wi" || t === "Wd" ? "--sW" : "--s" + t;
    return '<span class="tbadge" style="background:var(' + color + ')">' + esc(info.name) + "</span>";
  }

  function showSynDrill() {
    setRoute("#/satzbau/uebung");
    current = null; hideCard(); setNav("bSyn");
    var D = DATA.syn.drill.texts;
    var h = '<article class="syn drill"><h2>Übung: Welches Wort passt?</h2><p><a id="backSyn">← zurück zu Satzbau</a></p>';
    h += '<p class="hint">Like Sprachbausteine Teil 1: pick a, b or c. Look at the conjugated verb first. Is it at the end (A), right after the gap (C), in normal order after the subject (B)? Or does a noun come right after the gap (E, a preposition)? If all three options fit the word order, check the meaning. A wrong answer gets flagged, and you try again.</p>';
    D.forEach(function (t, ti) {
      var mail = esc(t.text).replace(/\{(\d+)\}/g, function (m, n) { return '<span class="gap" id="gap-' + n + '">(' + n + ") ______</span>"; }).replace(/\n/g, "<br>");
      h += "<h3>" + esc(t.title) + '</h3><div class="mail">' + mail + "</div>";
      t.gaps.forEach(function (g) {
        var sent = esc(g.s).replace("___", '<span class="blank">___</span>');
        h += '<div class="qq" data-t="' + ti + '" data-n="' + g.n + '"><div class="qt"><b>' + g.n + ".</b> " + sent + '</div><div class="opts">';
        g.o.forEach(function (o, j) { h += '<button class="opt" data-j="' + j + '"><b>' + "abc".charAt(j) + ")</b> " + esc(o) + "</button>"; });
        h += '</div><div class="fb"></div></div>';
      });
      h += '<div class="score" id="dscore-' + ti + '"></div>';
    });
    h += '<p><button id="drillReset">Nochmal von vorn</button></p></article>';
    main.innerHTML = h;
    document.getElementById("backSyn").addEventListener("click", function (ev) { ev.preventDefault(); ev.stopPropagation(); showSyntax(); });
    document.getElementById("drillReset").addEventListener("click", function (ev) { ev.stopPropagation(); showSynDrill(); });
    D.forEach(function (t, ti) {
      var first = {}, tries = {}, done = {};
      t.gaps.forEach(function (g) {
        var box = main.querySelector('.qq[data-t="' + ti + '"][data-n="' + g.n + '"]'), fb = box.querySelector(".fb");
        function finish(mode) {
          done[g.n] = true;
          each(box.querySelectorAll(".opt"), function (b) { if (+b.getAttribute("data-j") === g.a) b.classList.add("yes"); b.classList.add("locked"); });
          var gap = document.getElementById("gap-" + g.n);
          gap.textContent = g.o[g.a]; gap.classList.add("filled");
          var msg = mode === "first" ? "Richtig!" : mode === "second" ? "Richtig, beim zweiten Versuch." : "Die richtige Antwort ist " + "abc".charAt(g.a) + ") " + g.o[g.a] + ".";
          fb.innerHTML = '<div class="' + (mode === "shown" ? "sol" : "ok") + '">' + esc(msg) + "</div><div>" + typeBadge(g.t) + '<span class="why">' + esc(g.why) + "</span></div>";
          if (t.gaps.every(function (x) { return done[x.n]; })) {
            var r = t.gaps.map(function (x) { return first[x.n] ? 1 : 0; });
            state.drill[ti] = { r: r }; save();
            document.getElementById("dscore-" + ti).textContent = "Ergebnis: " + total(r) + " von " + t.gaps.length + " beim ersten Versuch.";
          }
        }
        each(box.querySelectorAll(".opt"), function (btn) {
          btn.addEventListener("click", function (ev) {
            ev.stopPropagation();
            if (done[g.n] || btn.classList.contains("no")) return;
            tries[g.n] = (tries[g.n] || 0) + 1;
            if (+btn.getAttribute("data-j") === g.a) {
              if (first[g.n] === undefined) first[g.n] = true;
              finish(tries[g.n] === 1 ? "first" : "second");
              return;
            }
            first[g.n] = false;
            btn.classList.add("no");
            if (tries[g.n] >= 2) { finish("shown"); return; }
            fb.innerHTML = '<div class="try">Nicht ganz. Where is the conjugated verb: at the end, right after the gap, or after the subject? Or does a noun come right after the gap? If all three fit the word order, check the meaning.</div>';
          });
        });
      });
    });
    window.scrollTo(0, 0);
  }

  function showSyntax(focusKey, focusType) {
    setRoute("#/satzbau");
    current = null; hideCard(); setNav("bSyn");
    var h = '<article class="syn"><h2>Satzbau: Konnektoren und Verbposition</h2>';
    h += '<p class="hint">Every word here changes, or doesn\'t change, where the verb goes. Each one shows its type, meaning and level, plus real sentences from the stories. Tap a link to open the story. <button class="small synT">Satzbau: ' + (state.syn ? "an" : "aus") + "</button> colors these words in the stories, and the verb each one moves gets a box.</p>";
    var dr = DATA.syn.drill.texts.map(function (t, i) { var r = state.drill[i]; return r ? total(r.r) + "/" + t.gaps.length : null; }).filter(Boolean);
    h += '<p><button id="drillGo">Übung: 20 Lücken wie in den Sprachbausteinen</button>' + (dr.length ? ' <span class="hint">Letztes Ergebnis: ' + dr.join(" · ") + "</span>" : "") + "</p>";
    h += "<h3>Die Grundregel</h3><p>In a German statement (Aussagesatz) the conjugated verb is always in <b>position 2</b>. Position 1 can be the subject, a time phrase or a connector: <i>Ich <b>bleibe</b> heute zu Hause.</i> / <i>Heute <b>bleibe</b> ich zu Hause.</i> / <i>Deshalb <b>bleibe</b> ich zu Hause.</i> In a side clause (Nebensatz) the conjugated verb goes to the <b>end</b>: <i>…, weil ich krank <b>bin</b>.</i></p>";
    h += '<h3>Familien: gleiche Bedeutung, andere Wortstellung</h3><p class="rule">A very common Sprachbausteine trap. Pick the column from the word order after the gap.</p><div class="famwrap"><table class="fam"><tr><th>Bedeutung</th><th>A: Verb ans Ende</th><th>B: Position 0</th><th>C: Inversion</th><th>zu + Infinitiv</th><th>E: Präposition</th></tr>';
    DATA.syn.families.forEach(function (f) {
      h += "<tr><td>" + esc(f.m) + '</td><td class="tA">' + esc(f.A) + '</td><td class="tB">' + esc(f.B) + '</td><td class="tC">' + esc(f.C) + '</td><td class="tZ">' + esc(f.Z) + '</td><td class="tE">' + esc(f.E) + "</td></tr>";
    });
    h += "</table></div>";
    GROUPS.forEach(function (g) {
      var items = DATA.syn.items.filter(function (it) { return it.t === g[0]; });
      if (!items.length) return;
      var color = g[0] === "X" ? "--sB" : g[0] === "W" ? "--sW" : "--s" + g[0];
      h += '<details id="g-' + g[0] + '"' + (g[0] === "X" ? "" : " open") + '><summary><span class="dot" style="background:var(' + color + ')"></span>' + esc(g[1]) + " (" + items.length + ")</summary>";
      h += '<p class="rule">' + esc(g[2]) + (g[3] ? " <i>" + esc(g[3]) + "</i>" : "") + "</p><ul>";
      items.forEach(function (it) {
        var ex = examplesFor(it);
        h += '<li id="it-' + it.t + "-" + esc(it.w) + '"><b class="kw">' + esc(it.w) + '</b> <span class="lvl lvl-' + esc(it.lvl) + '">' + esc(it.lvl === "—" ? "nicht auf der Liste" : it.lvl) + "</span> = " + esc(it.en);
        h += ex.total ? '<span class="cnt">' + ex.total + "× in den Geschichten</span>" : "";
        h += (it.note ? '<div class="note">' + esc(it.note) + "</div>" : "") + ex.html + "</li>";
      });
      h += "</ul></details>";
    });
    h += "</article>";
    main.innerHTML = h;
    wireSynToggles();
    document.getElementById("drillGo").addEventListener("click", function (ev) { ev.stopPropagation(); showSynDrill(); });
    each(main.querySelectorAll(".exgo"), function (a) {
      a.addEventListener("click", function (ev) {
        ev.stopPropagation();
        setSyn(true);
        showStory(a.getAttribute("data-n"), "l");
        var pi = +a.getAttribute("data-p");
        setTimeout(function () { flashPara(pi); }, 50);
      });
    });
    window.scrollTo(0, 0);
    if (focusKey) {
      var t = focusType === "Cm" ? "C" : (focusType === "Wd" || focusType === "Wi") ? "W" : focusType;
      var target = document.getElementById("it-" + t + "-" + focusKey);
      if (target) { target.scrollIntoView({ block: "center" }); target.style.background = "var(--flash)"; setTimeout(function () { target.style.background = ""; }, 2500); }
    }
  }
  window.addEventListener("resize", function () { if (openWord && card.style.display === "block") placeCard(openWord); });

  main.addEventListener("click", function (ev) {
    var t = ev.target.closest ? ev.target.closest(".w,.b,.n,.p,.gw") : null;
    if (!t || !main.contains(t)) return;
    var opt = t.closest(".opt");
    if (opt && !opt.classList.contains("locked")) return;
    ev.stopPropagation();
    showCard(t);
  });

  function showIndex() {
    setRoute("#/wortliste");
    current = null; hideCard(); setNav("bIdx");
    var list = Object.keys(DATA.words).map(function (id) { var w = DATA.words[id]; return { id: id, d: w.d, g: w.g, l: w.l, s: w.s || [], ps: w.ps || [], k: w.d.replace(/^(\(sich\)|sich|der|die|das)(\/(der|die|das))?\s+/i, "").replace(/^[-(…\s]+/, "").toLowerCase() }; });
    list.sort(function (a, b) { return a.k.localeCompare(b.k, "de"); });
    main.innerHTML = '<input id="search" type="search" placeholder="Wort suchen (Deutsch oder Englisch) …"><div class="hint" id="cnt"></div><ul class="idx" id="idx"></ul>';
    var q = document.getElementById("search");
    q.value = lastQuery;
    function score(w, t) {
      if (!t) return 0;
      var d = w.d.toLowerCase(), g = w.g.toLowerCase();
      if (w.k === t || w.k.split(/[ ,]/)[0] === t) return 0;
      if (w.k.indexOf(t) === 0) return 1;
      if (new RegExp("(^|[^a-zäöüß])" + t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).test(d + " " + g)) return 2;
      if (d.indexOf(t) >= 0 || g.indexOf(t) >= 0) return 3;
      return -1;
    }
    function draw() {
      var t = q.value.trim().toLowerCase(), h = "", c = 0;
      var shown = list.map(function (w) { return { w: w, s: score(w, t) }; }).filter(function (x) { return x.s >= 0; });
      shown.sort(function (a, b) { return a.s - b.s || a.w.k.localeCompare(b.w.k, "de"); });
      shown.forEach(function (x) {
        var w = x.w;
        c++;
        if (c > 400) return;
        h += '<li><span class="lvl lvl-' + w.l + '">' + lvlName(w.l) + '</span> <span class="d">' + esc(w.d) + '</span> <span class="g">= ' + esc(w.g) + "</span>" + w.s.map(function (n) { return '<a data-n="' + n + '" data-ver="l">' + n + "</a>"; }).join("") + w.ps.filter(function (n) { return DATA.pr[n]; }).map(function (n) { return '<a data-n="' + n + '" data-ver="p">P' + n + "</a>"; }).join("") + "</li>";
      });
      document.getElementById("idx").innerHTML = h;
      document.getElementById("cnt").textContent = c + " Wörter" + (c > 400 ? " (die ersten 400 werden gezeigt)" : "");
      each(document.querySelectorAll("#idx a"), function (a) { a.addEventListener("click", function () { showStory(a.getAttribute("data-n"), a.getAttribute("data-ver")); }); });
    }
    q.addEventListener("input", function () { lastQuery = q.value; draw(); });
    draw();
    window.scrollTo(0, 0);
  }

  document.getElementById("bToc").addEventListener("click", showToc);
  document.getElementById("bIdx").addEventListener("click", showIndex);
  document.getElementById("bSyn").addEventListener("click", function () { showSyntax(); });
  document.getElementById("bHelp").addEventListener("click", showHelp);
  document.getElementById("cardX").addEventListener("click", function (ev) { ev.stopPropagation(); hideCard(); });
  document.addEventListener("click", function (ev) { if (!card.contains(ev.target)) hideCard(); });
  document.addEventListener("keydown", function (ev) {
    if (!current || ev.target.tagName === "INPUT" || ev.target.tagName === "TEXTAREA") return;
    var i = byNum(current);
    if (ev.key === "ArrowRight" && i < DATA.stories.length - 1) showStory(DATA.stories[i + 1].n);
    if (ev.key === "ArrowLeft" && i > 0) showStory(DATA.stories[i - 1].n);
    if (ev.key === "Escape") hideCard();
  });
/*__HEUTE_JS__*/
  setMark(markOf());
  renderRoute();
  booted = true;
  if (!storeOk) storeWarn();
  window.addEventListener("storage", function (e) { if (e.key === KEY || e.key === null) syncFromStorage(); });
  window.addEventListener("focus", syncFromStorage);
  document.addEventListener("visibilitychange", function () { if (!document.hidden) syncFromStorage(); });
})();
</script>
</body>
</html>
"""
page = page.replace("/*__HEUTE_CSS__*/", open(f"{BASE}/heute.css", encoding="utf-8").read()).replace("/*__HEUTE_JS__*/", open(f"{BASE}/heute.js", encoding="utf-8").read())
open(OUT, "w", encoding="utf-8").write(page.replace("__DATA__", payload))
levels = {}
for w in words.values():
    levels[w["l"]] = levels.get(w["l"], 0) + 1
print("wrote", OUT, "| stories:", len(stories), "| tappable list words:", len(words), levels, "| missing glosses:", sum(1 for w in words.values() if not w["g"]), "| quizzes:", len(quiz), "| Prüfung sets:", len(pr), "| Prüfung quizzes:", len(pq), "| Hören tasks:", len(hoeren), "| linked Hören:", len(hlinked), "| mail prompts:", len(mail))
