import json, re, sys, collections
p = "mail/prompts.json"
P = json.load(open(p, encoding="utf-8"))
err = []
ids = set()
kinds = collections.Counter()
regs = collections.Counter()
for i, x in enumerate(P):
    tag = x.get("id", f"#{i}")
    for k in ("id", "kind", "reg", "theme", "from", "mail", "points", "focus"):
        if k not in x:
            err.append(f"{tag}: missing {k}")
    if tag in ids:
        err.append(f"{tag}: duplicate id")
    ids.add(tag)
    kinds[x.get("kind")] += 1
    regs[(x.get("kind"), x.get("reg"))] += 1
    if x.get("kind") not in ("mini", "full"):
        err.append(f"{tag}: kind must be mini or full")
    if x.get("reg") not in ("du", "Sie"):
        err.append(f"{tag}: reg must be du or Sie")
    n = len(x.get("points", []))
    if x.get("kind") == "mini" and n not in (2, 3):
        err.append(f"{tag}: mini needs 2 or 3 points, has {n}")
    if x.get("kind") == "full" and n != 4:
        err.append(f"{tag}: full needs 4 points, has {n}")
    words = len(re.findall(r"\w+", x.get("mail", "")))
    lo, hi = (20, 70) if x.get("kind") == "mini" else (40, 110)
    if not lo <= words <= hi:
        err.append(f"{tag}: incoming mail has {words} words, want {lo}-{hi}")
    blob = json.dumps(x, ensure_ascii=False)
    if "—" in blob or "–" in x.get("mail", ""):
        err.append(f"{tag}: dash found (no em or en dashes in German)")
    for k in ("from", "mail", "points"):
        v = x.get(k, "")
        s = " ".join(v) if isinstance(v, list) else v
        if '"' in s:
            err.append(f"{tag}: straight quote in {k}")
    if not x.get("focus"):
        err.append(f"{tag}: focus is empty")
print("prompts:", len(P), dict(kinds), dict(regs))
print("problems:", len(err))
for e in err:
    print("  ", e)
