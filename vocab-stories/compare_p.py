import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from quizlib import player

for num in sys.argv[1:]:
    num = num.zfill(2)
    d = json.load(open(f"{BASE}/pquiz/pq_{num}.json", encoding="utf-8"))
    path = f"{BASE}/pquiz/blind/solve_{num}.json"
    if not os.path.exists(path):
        print(num, "no solver answers yet")
        continue
    s = json.load(open(path, encoding="utf-8"))
    keys = {}
    for part in d["parts"]:
        if part["type"] == "abc":
            keys["A"] = ["abc"[pos] for pos, _ in player(num, len(part["items"]))]
            qa = [it["q"] for it in part["items"]]
        elif part["type"] == "rf":
            keys["B"] = ["richtig" if it["answer"] else "falsch" for it in part["items"]]
            qb = [it["s"] for it in part["items"]]
        else:
            keys["B"] = [p["answer"] for p in part["prompts"]]
            qb = [p.get("text") or "Text " + p["id"] for p in part["prompts"]]
    bad = total = 0
    for sec, qs in (("A", qa), ("B", qb)):
        picks = {a.get("k"): a for a in s.get(sec, [])}
        for k, key in enumerate(keys[sec], 1):
            total += 1
            a = picks.get(k, {})
            pick = str(a.get("pick", "")).strip().lower()
            issue = (a.get("issue") or "").strip()
            flags = []
            if pick != key:
                flags.append(f"key {key}, solver {pick or '-'}")
            if a.get("guessable"):
                flags.append("guessable without the text")
            if a.get("sure") == "low":
                flags.append("solver unsure")
            if issue:
                flags.append("issue: " + issue)
            if flags:
                bad += 1
                print(f"{num} {sec}{k}: " + " | ".join(flags) + f" | {qs[k-1][:70]}")
    for g in s.get("german", []):
        print(f"{num} German: {g}")
    print(f"{num}: {total - bad}/{total} clean, {len(s.get('german', []))} German notes")
