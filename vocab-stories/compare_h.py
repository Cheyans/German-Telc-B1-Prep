import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
H = f"{BASE}/hoeren"
def keys(a):
    if a.startswith("u"):
        d = json.load(open(f"{H}/u_{a[1:]}.json", encoding="utf-8"))
        return [("", i + 1, it) for i, it in enumerate(d["items"])]
    d = json.load(open(f"{H}/h_{a}.json", encoding="utf-8"))
    return [(str(t["part"]), i + 1, it) for t in d["tasks"] for i, it in enumerate(t["items"])]
tot = bad = flags = 0
for a in sys.argv[1:]:
    sp = f"{H}/solve/hs_{a}.json"
    if not os.path.exists(sp):
        print(a, "no solver file"); continue
    S = json.load(open(sp, encoding="utf-8"))
    ans = {(str(x.get("part", "")), int(x["k"])): x for x in S["answers"]}
    for part, k, it in keys(a):
        tot += 1
        x = ans.get((part, k))
        if not x:
            print(f"{a} part {part or '-'} #{k}: no answer"); bad += 1; continue
        mine = x.get("a")
        f = [z for z in ("unsure", "ambiguous", "guessable") if x.get(z)]
        if mine != it["a"]:
            bad += 1
            print(f"MISMATCH {a} part {part or '-'} #{k}: key {it['a']} solver {mine} | {it['s']} | solver: {x.get('at', '')} {x.get('ev', '')} | {x.get('note', '')}")
        elif f:
            flags += 1
            print(f"flag {a} part {part or '-'} #{k} {f}: {it['s']} | {x.get('note', '')}")
print(f"items {tot}, mismatches {bad}, flagged {flags}")
