import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import annotate as A
import spacy

plan = json.load(open(f"{BASE}/basics/insert_plan_2026-10-21.json", encoding="utf-8"))
entries = [dict(e) for e in json.load(open(f"{BASE}/final_entries.json", encoding="utf-8"))]
index = A.Index(entries)
phrases = sorted(((A.phrase_regex(p), e) for p, e in index.phrases if e["pos"] != "verb"), key=lambda x: -len(x[0].pattern))
matcher = A.Matcher(index, defaultdict(set))
nlp = spacy.load("de_core_news_md")
for num in sys.argv[1:]:
    num = num.zfill(2)
    raw = A.nfc(open(f"{BASE}/stories/story_{num}.md", encoding="utf-8").read().strip())
    errors = []
    if "—" in raw:
        errors.append("em dash in the story")
    body = "\n".join(raw.splitlines()[1:])
    if '"' in body:
        errors.append("straight double quote in the story")
    stats = {"auto_b1": 0, "auto_basic": 0, "compound": 0, "unmatched": Counter(), "multi": Counter(), "covered": set(), "covered_c": set()}
    for block in re.split(r"\n\s*\n", body.strip()):
        block = " ".join(l.strip() for l in block.splitlines() if l.strip())
        if block:
            text, spans = A.parse_paragraph(block)
            A.annotate_text(nlp, matcher, phrases, text, spans, stats)
    for w in plan.get(num, []):
        if w["id"] not in stats["covered"]:
            errors.append(f"{w['id']} {w['entry'][:40]} is not found in the story yet")
    print(f"story {num}: ERRORS ({len(errors)}):")
    for e in errors:
        print("  " + e)
