import json, os, re, sys

BASE = os.path.dirname(os.path.abspath(__file__))
L = json.load(open(os.path.join(BASE, "hoeren", "linked.json"), encoding="utf-8"))
errs = []


def err(t, msg):
    errs.append(f"{t.get('id', '?')}: {msg}")


def secs(x):
    m = re.fullmatch(r"(\d{1,2}):(\d\d)", x or "")
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


ids = [t.get("id") for t in L]
for d in sorted({i for i in ids if ids.count(i) > 1}):
    errs.append(f"{d}: duplicate id")
for t in L:
    for k in ("id", "src", "set", "part", "min"):
        if not t.get(k):
            err(t, f"missing {k}")
    if t.get("src") not in ("dw", "telc", "osd", "goethe", "nicos"):
        err(t, f"unknown src {t.get('src')}")
    for k in ("url", "get", "page"):
        if t.get(k) and not t[k].startswith("https://"):
            err(t, f"{k} is not https")
    text = " ".join(str(t.get(k, "")) for k in ("set", "part", "what", "task", "do", "items"))
    if re.search(r"[–—]|\"", text):
        err(t, "dash or straight quote in German text")
    if t.get("url"):
        if t.get("pdf") or t.get("audio"):
            err(t, "online task with pdf or audio")
        continue
    p, a = t.get("pdf"), t.get("audio")
    if not p or not a:
        err(t, "needs url, or pdf and audio")
        continue
    if not all(isinstance(p.get(k), int) and p[k] > 0 for k in ("q", "key")):
        err(t, "pdf.q and pdf.key must be page numbers")
    if p.get("url") and not p["url"].startswith("https://"):
        err(t, "pdf.url is not https")
    f, to = secs(a.get("from")), secs(a.get("to"))
    if f is None or to is None or f >= to:
        err(t, f"bad audio window {a.get('from')} to {a.get('to')}")
    if not (a.get("file") or (a.get("url") or "").startswith("https://")):
        err(t, "audio needs a file name or an https url")
    if t.get("plays") not in (1, 2):
        err(t, "plays must be 1 or 2")
    m = re.fullmatch(r"(\d+) bis (\d+)", t.get("items", ""))
    if not m or int(m.group(2)) - int(m.group(1)) + 1 != t.get("n"):
        err(t, f"items {t.get('items')!r} do not match n={t.get('n')}")
by_set = {}
for t in L:
    if t.get("audio") and t["audio"].get("from"):
        by_set.setdefault((t["set"], t["audio"].get("file") or t["audio"].get("url")), []).append(t)
for (s, _), ts in by_set.items():
    for x, y in zip(ts, ts[1:]):
        if x["audio"]["file" if "file" in x["audio"] else "url"] == y["audio"]["file" if "file" in y["audio"] else "url"] and x["audio"]["to"] != y["audio"]["from"]:
            errs.append(f"{y['id']}: starts at {y['audio']['from']}, but {x['id']} ends at {x['audio']['to']}")
print(f"{len(L)} linked tasks, {len(errs)} problems")
for e in errs:
    print("  " + e)
sys.exit(1 if errs else 0)
