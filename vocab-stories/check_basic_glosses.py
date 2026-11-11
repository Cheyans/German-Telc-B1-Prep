import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

part = sys.argv[1]
inp = json.load(open(f"{BASE}/glosses/basics_input_{part}.json", encoding="utf-8"))
path = f"{BASE}/glosses/basics_{part}.json"
errors, warns = [], []
if not os.path.exists(path):
    print(f"ERRORS (1):\n  missing {path}")
    sys.exit()
try:
    out = json.load(open(path, encoding="utf-8"))
except Exception as e:
    print(f"ERRORS (1):\n  invalid JSON: {e}")
    sys.exit()
ids = [w["id"] for w in inp]
for w in inp:
    g = out.get(w["id"])
    if not g or not str(g).strip():
        errors.append(f"{w['id']}: missing gloss ({w['entry'][:40]})")
        continue
    if len(g) > 60:
        errors.append(f"{w['id']}: gloss longer than 60 characters")
    if "—" in g or '"' in g:
        errors.append(f"{w['id']}: no em dashes or straight double quotes")
    if w["pos"] == "verb" and not re.match(r"^(\(\w+\) )?to ", g):
        warns.append(f"{w['id']}: verb gloss should start with 'to': {g}")
    if w["pos"] == "noun" and re.match(r"^(the|a|an) ", g):
        warns.append(f"{w['id']}: noun gloss without article: {g}")
for k in out:
    if k not in ids:
        errors.append(f"{k}: not in your input")
print(f"ERRORS ({len(errors)}):")
for e in errors[:60]:
    print("  " + e)
print(f"WARNINGS ({len(warns)}):")
for w in warns[:60]:
    print("  " + w)
