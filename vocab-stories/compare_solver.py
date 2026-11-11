import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from quizlib import layout

for num in sys.argv[1:]:
    num = num.zfill(2)
    d = json.load(open(f"{BASE}/quiz/quiz_{num}.json", encoding="utf-8"))
    path = f"{BASE}/quiz/blind/solve_{num}.json"
    if not os.path.exists(path):
        print(num, "no solver answers yet")
        continue
    s = json.load(open(path, encoding="utf-8"))
    picks = {a["k"]: a for a in s["answers"]}
    bad = 0
    for k, (pos, perm) in enumerate(layout(num, len(d["questions"])), 1):
        key = "abc"[pos]
        a = picks.get(k, {})
        agree = a.get("pick") == key
        issue = (a.get("issue") or "").strip()
        if not agree or issue:
            bad += 1
            print(f"{num} Q{k}: key {key}, solver {a.get('pick')} | issue: {issue or '-'} | {d['questions'][k-1]['q'][:70]}")
    print(f"{num}: {len(d['questions']) - bad}/{len(d['questions'])} clean")
