import json
import os
import re
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
WORD = re.compile(r"[A-Za-zÄÖÜäöüß]+(?:-[A-Za-zÄÖÜäöüß]+)*")


def text_of(segs):
    return "".join(x if isinstance(x, str) else x[0] for x in segs)


def main():
    ann = json.load(open(f"{BASE}/annotated.json", encoding="utf-8"))
    counts, ctx = Counter(), defaultdict(list)

    def walk(segs):
        full = text_of(segs)
        pos = 0
        for sg in segs:
            if isinstance(sg, str):
                for m in WORD.finditer(sg):
                    f = m.group(0)
                    if len(f) < 2:
                        continue
                    counts[f] += 1
                    if len(ctx[f]) < 2:
                        a = pos + m.start()
                        snippet = full[max(0, a - 70):a + len(f) + 70].replace("\n", " ").strip()
                        if snippet not in ctx[f]:
                            ctx[f].append(snippet)
            pos += len(sg if isinstance(sg, str) else sg[0])

    for paras in ann["stories"].values():
        for p in paras:
            walk(p)
    for st in ann.get("pruefung", {}).values():
        for b in st["blocks"]:
            walk(b["s"])
    for qs in ann["quiz"].values():
        for q in qs:
            walk(q["q"]); walk(q["right"]); [walk(w) for w in q["wrong"]]
    for parts in ann.get("pquiz", {}).values():
        for part in parts:
            for it in part.get("items", []):
                if isinstance(it, dict):
                    walk(it["q"]); walk(it["right"]); [walk(w) for w in it["wrong"]]
                else:
                    walk(it)
            for o in part.get("options", []):
                walk(o)
            for pr in part.get("prompts", []):
                walk(pr)
    forms = sorted(counts, key=lambda f: (f.lower(), f))
    done = {}
    for p in sorted(os.listdir(f"{BASE}/offlist")):
        if p.startswith("gloss_") and p.endswith(".json"):
            done.update(json.load(open(f"{BASE}/offlist/{p}", encoding="utf-8")))
    todo = [f for f in forms if f not in done]
    json.dump({"forms": forms}, open(f"{BASE}/offlist/forms.json", "w", encoding="utf-8"), ensure_ascii=False)
    n = 3
    size = (len(todo) + n - 1) // n if todo else 0
    for k in range(n):
        part = todo[k * size:(k + 1) * size]
        if part:
            json.dump([{"form": f, "count": counts[f], "context": ctx[f]} for f in part],
                      open(f"{BASE}/offlist/batch_{k + 1}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("forms:", len(forms), "| already glossed:", len(forms) - len(todo), "| to gloss:", len(todo), "| batches of", size)


if __name__ == "__main__":
    main()
