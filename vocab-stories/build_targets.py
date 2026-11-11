import json, re, sys
sys.path.insert(0, "/tmp/vs")
from groups import GROUPS
sys.path.insert(0, "/tmp/vocab")
M = json.load(open("/tmp/vocab/master_alpha.json"))
src = open("/tmp/vocab/build_master.py").read()
ns = {}
exec(src.split("a1 = parse_a1()")[0], ns)
a1 = {ns["norm_lemma"](t).lower() for t in ns["parse_a1"]()}
a2 = {ns["norm_lemma"](t).lower() for t in ns["parse_a2"]()}
alpha_lemmas = {m["lemma"].lower() for m in M}
entries = []
for m in M:
    if m["region"] in ("A", "CH", "A,CH"):
        continue
    entries.append({"id": m["id"], "text": m["text"], "lemma": m["lemma"], "pos": m["pos"], "level": m["level"], "sub": m["sub"], "parent": m["parent"], "src": "alpha"})
gi = 0
for g, items in GROUPS.items():
    for it in items:
        gi += 1
        lem = ns["norm_lemma"](re.sub(r"\(.*?\)", "", it)).strip()
        key = lem.lower()
        if key in alpha_lemmas:
            continue
        level = "A1" if key in a1 else ("A2" if key in a2 else "B1")
        if g in ("Zahlen", "Farben", "Monate", "Wochentage", "Tageszeiten", "Jahreszeiten", "Uhrzeit"):
            level = "A1" if level == "B1" else level
        pos = "noun" if re.match(r"^(der|die|das)\b", it) else ("verb" if re.match(r"^[a-zäöü]+(en|ern|eln)$", lem) and g == "Anglizismen" else "other")
        entries.append({"id": f"G{gi:03d}", "text": it, "lemma": lem, "pos": pos, "level": level, "sub": False, "parent": None, "src": "group:" + g})
json.dump(entries, open("/tmp/vs/entries.json", "w"), ensure_ascii=False, indent=0)
from collections import Counter
print("entries:", len(entries), Counter(e["level"] for e in entries))
print("by src:", Counter(e["src"].split(":")[0] for e in entries))
print("group B1-new:", [e["text"] for e in entries if e["src"] != "alpha" and e["level"] == "B1"][:200])
