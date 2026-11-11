import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from quizlib import layout, order

for num in sys.argv[1:]:
    num = num.zfill(2)
    d = json.load(open(f"{BASE}/quiz/quiz_{num}.json", encoding="utf-8"))
    qs = []
    for k, (q, (pos, perm)) in enumerate(zip(d["questions"], layout(num, len(d["questions"])))):
        opts = order(q["right"], q["wrong"], pos, perm)
        qs.append({"k": k + 1, "q": q["q"], "a": opts[0], "b": opts[1], "c": opts[2]})
    os.makedirs(f"{BASE}/quiz/blind", exist_ok=True)
    json.dump({"story": num, "questions": qs}, open(f"{BASE}/quiz/blind/blind_{num}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("blind", num)
