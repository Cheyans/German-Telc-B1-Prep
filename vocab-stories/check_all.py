import glob
import json
import re
from collections import Counter
import os

BASE = os.path.dirname(os.path.abspath(__file__))

MARK = re.compile(r"\[\[([^\[\]|]+)\|([WG]\d{3,4})\]\]")
E = json.load(open(f"{BASE}/final_entries.json"))
byid = {e["id"]: e for e in E}

def norm(s):
    s = s.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return s

texts = {}
used = Counter()
for path in sorted(glob.glob(f"{BASE}/stories/story_*.md")):
    raw = open(path, encoding="utf-8").read()
    for form, i in MARK.findall(raw):
        used[i] += 1
    texts[path] = MARK.sub(lambda m: m.group(1), raw)
full = norm(" ".join(texts.values()))
tokens = set(re.findall(r"[a-z]+", full))
token_list = sorted(tokens)

b1 = [e for e in E if e["level"] == "B1"]
missing_b1 = [e for e in b1 if e["id"] not in used]
unknown = [i for i in used if i not in byid]

def candidates(e):
    lem = re.sub(r"\(.*?\)", " ", e["lemma"])
    lem = re.sub(r"^(der|die|das|sich)(/(der|die|das))?\s+", "", lem.strip())
    cands = set()
    words = [w for w in re.findall(r"[A-Za-zÄÖÜäöüß]+", lem)]
    if len(words) >= 2 and e["pos"] != "verb":
        return {"PHRASE:" + norm(" ".join(words))}
    base = norm(words[0]) if words else ""
    if base:
        if e["pos"] == "verb":
            for suf in ("ieren", "eln", "ern", "en", "n"):
                if base.endswith(suf) and len(base) - len(suf) >= 3:
                    cands.add(base[: len(base) - len(suf)] + ("ier" if suf == "ieren" else ""))
                    break
        cands.add(base)
    for t in re.findall(r"[A-Za-zÄÖÜäöüß]+", re.sub(r"\(.*?\)", " ", e["text"])):
        t = norm(t)
        if t not in ("der", "die", "das", "hat", "ist", "sich", "pl", "nen", "en"):
            cands.add(t)
    return cands

raw_all = norm(" ".join(texts.values()))

def covered(e):
    lem = re.sub(r"\(.*?\)", " ", e["lemma"])
    lem = re.sub(r"^(der|die|das|sich)(/(der|die|das))?\s+", "", lem.strip())
    alts = [a.strip() for a in re.split(r"\s*/\s*", lem) if a.strip()]
    for a in alts:
        a_n = norm(a)
        if "-" in a_n.strip("-") and a_n.strip("-") in raw_all:
            return True
        if a_n.endswith("-") and len(a_n) > 2:
            stem = a_n.rstrip("-")
            if any(tk.startswith(stem) for tk in token_list if tk[:2] == stem[:2]):
                return True
        if " " in a_n and re.sub(r"[^a-z ]", "", a_n).strip() in re.sub(r"[^a-z ]", " ", raw_all):
            return True
    for c in candidates(e):
        if c.startswith("PHRASE:"):
            if c[7:] in full:
                return True
            continue
        if len(c) <= 3:
            if c in tokens:
                return True
        elif any(t.startswith(c) for t in token_list if t[:2] == c[:2]):
            return True
    return False

basics = [e for e in E if e["level"] != "B1"]
missing_basic = [e for e in basics if not covered(e)]
words_total = len(re.findall(r"\w+", " ".join(texts.values())))
print(f"stories: {len(texts)} | words: {words_total}")
print(f"B1 targets: {len(b1)} | used: {len(b1) - len(missing_b1)} | missing: {len(missing_b1)} | unknown IDs: {unknown[:10]}")
print(f"basics: {len(basics)} | probably covered: {len(basics) - len(missing_basic)} | not found: {len(missing_basic)}")
json.dump([e["id"] for e in missing_basic], open(f"{BASE}/missing_basics.json", "w"))
for e in missing_b1[:40]:
    print("  B1 missing:", e["id"], e["text"][:60])
print("basics not found:", ", ".join(e["text"].split(",")[0][:30] for e in missing_basic[:400]))
