import json, re, sys, os
BASE = os.path.dirname(os.path.abspath(__file__))
PRIV = os.environ.get("B1_PRIVATE", os.path.join(BASE, "private"))
W2 = os.path.join(PRIV, "allango-676830", "whisper2")
def norm(s):
    return re.sub(r"[^\wäöüß]+", " ", s.lower().replace("ß", "ss")).split()
def lines(tr):
    out = []
    for ln in open(f"{W2}/track_{tr}.txt", encoding="utf-8"):
        m = re.match(r"\[(\d\d):(\d\d)\] (.*)", ln)
        if m:
            out.append((m.group(1) + ":" + m.group(2), norm(m.group(3))))
    return out
write = "--write" in sys.argv
for n in [a for a in sys.argv[1:] if not a.startswith("--")]:
    p = f"{BASE}/hoeren/u_{n}.json"
    d = json.load(open(p, encoding="utf-8"))
    for i, it in enumerate(d["items"]):
        L = lines(it["tr"])
        ev = norm(it["ev"].replace("…", " "))
        best, at = 0, None
        for j, (t, ws) in enumerate(L):
            pool = ws + (L[j + 1][1] if j + 1 < len(L) else [])
            sc = sum(1 for w in ev if w in pool) / max(1, len(ev))
            first = sum(1 for w in ev[:3] if w in ws) / max(1, min(3, len(ev)))
            sc = sc + 0.01 * first
            if sc > best:
                best, at = sc, t
        flag = "" if best >= 0.6 else "  <-- weak match, kept"
        if at and best >= 0.6 and at != it["at"]:
            print(f"u{n} #{i + 1} tr {it['tr']}: {it['at']} -> {at} ({best:.0%}) {it['ev'][:50]}")
            if write:
                it["at"] = at
        elif flag:
            print(f"u{n} #{i + 1} tr {it['tr']}: {it['at']} best {at} ({best:.0%}){flag} | {it['ev'][:60]}")
    if write:
        json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
