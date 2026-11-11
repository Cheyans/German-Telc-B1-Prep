import json, re, glob, collections

BASE = "."
fe = {e["id"]: e for e in json.load(open(f"{BASE}/final_entries.json", encoding="utf-8"))}
gloss = {}
for f in glob.glob(f"{BASE}/glosses/*.json"):
    if "input" in f:
        continue
    d = json.load(open(f, encoding="utf-8"))
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, str):
                gloss.setdefault(k, v)

MARK = re.compile(r"\[\[([^|\]]+)\|([A-Z]\d+)\]\]")
stories = {}
for p in sorted(glob.glob(f"{BASE}/stories/story_*.md")):
    raw = open(p, encoding="utf-8").read()
    num = re.match(r"#\s*(\d+)\s*(.*)", raw.splitlines()[0])
    stories[num.group(1).zfill(2)] = {"title": num.group(2).strip(), "raw": raw, "ids": sorted(set(i for _, i in MARK.findall(raw)))}

missed = json.load(open(f"{BASE}/missed_ids.json"))["ids"]
extras = json.load(open(f"{BASE}/extras.json", encoding="utf-8"))
extra_sets = {x["id"]: x["sets"] for x in extras}

def part_b(n):
    return {1: "news", 2: "ads", 0: "voices"}[int(n) % 3]

load = collections.Counter()
missed_sets = {}
nums = sorted(stories)
for i, mid in enumerate(missed):
    have = [n for n in nums if mid in stories[n]["ids"]]
    cand = sorted((n for n in nums if n not in have), key=lambda n: (load[n], (int(n) * 7 + i * 3) % 28))
    pick = cand[:3]
    for n in pick:
        load[n] += 1
    missed_sets[mid] = pick

def entry(i):
    e = fe.get(i)
    return {"id": i, "entry": e["text"] if e else i, "level": e["level"] if e else "?", "gloss": gloss.get(i, "")}

for n in nums:
    s = stories[n]
    body = "\n".join(s["raw"].splitlines()[1:]).strip()
    cast = re.sub(r"\[\[([^|\]]+)\|[A-Z]\d+\]\]", r"\1", body)[:700]
    out = {
        "set": n,
        "title": s["title"],
        "part_b": part_b(n),
        "targets": [entry(i) for i in s["ids"]],
        "missed": [entry(m) for m in missed if n in missed_sets[m]],
        "extras": [{"id": x["id"], "word": x["word"], "gloss": x["gloss"], "kind": x["kind"], "de": x.get("de", "")} for x in extras if n in x["sets"]],
        "story_opening": cast,
    }
    json.dump(out, open(f"{BASE}/pruefung_inputs/set_{n}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

cnt = collections.Counter()
for n in nums:
    d = json.load(open(f"{BASE}/pruefung_inputs/set_{n}.json", encoding="utf-8"))
    for m in d["missed"]:
        cnt[m["id"]] += 1
assert all(cnt[m] == 3 for m in missed), "missed coverage"
ex = collections.Counter()
for n in nums:
    for x in json.load(open(f"{BASE}/pruefung_inputs/set_{n}.json", encoding="utf-8"))["extras"]:
        ex[x["id"]] += 1
assert all(ex[x["id"]] >= 2 for x in extras), "extras coverage"
print("sets:", len(nums), "| missed per set:", dict(sorted(load.items())), "| extras per set:", {n: len([x for x in extras if n in x['sets']]) for n in nums})
