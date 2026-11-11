import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from quizlib import order, player

MARK = re.compile(r"\[\[([^\[\]|]+)\|([WGXR]\d{3,4})\]\]")
os.makedirs(f"{BASE}/pquiz/blind", exist_ok=True)
for num in sys.argv[1:]:
    num = num.zfill(2)
    raw = open(f"{BASE}/pruefung/set_{num}.md", encoding="utf-8").read()
    open(f"{BASE}/pquiz/blind/text_{num}.md", "w", encoding="utf-8").write(MARK.sub(lambda m: m.group(1), raw))
    d = json.load(open(f"{BASE}/pquiz/pq_{num}.json", encoding="utf-8"))
    out = {"set": num}
    for part in d["parts"]:
        if part["type"] == "abc":
            qs = []
            for k, (it, (pos, perm)) in enumerate(zip(part["items"], player(num, len(part["items"]))), 1):
                o = order(it["right"], it["wrong"], pos, perm)
                qs.append({"k": k, "q": it["q"], "a": o[0], "b": o[1], "c": o[2]})
            out["A"] = {"task": "Teil A: choose a, b or c.", "questions": qs}
        elif part["type"] == "rf":
            out["B"] = {"task": "Teil B: is the statement richtig or falsch?", "questions": [{"k": k, "s": it["s"]} for k, it in enumerate(part["items"], 1)]}
        elif part["kind"] == "headlines":
            out["B"] = {"task": "Teil B: which headline (a to h) fits each news item 1 to 5? Each headline fits at most once, 3 are left over.",
                        "headlines": {o["id"]: o["text"] for o in part["options"]},
                        "questions": [{"k": int(p["id"]), "item": "Text " + p["id"]} for p in part["prompts"]]}
        else:
            out["B"] = {"task": "Teil B: which ad (a, b, c ...) fits each situation? Each ad fits at most once. For exactly one situation no ad fits: answer x.",
                        "questions": [{"k": k, "situation": p["text"]} for k, p in enumerate(part["prompts"], 1)]}
    json.dump(out, open(f"{BASE}/pquiz/blind/blind_{num}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("blind", num)
