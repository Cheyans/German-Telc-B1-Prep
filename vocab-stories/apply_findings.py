import json, os, sys, glob
BASE = os.path.dirname(os.path.abspath(__file__))
args = [a for a in sys.argv[1:] if not a.startswith("--")]
write = "--write" in sys.argv
skip = set()
if os.path.exists(f"{BASE}/review/rejected.json"):
    skip = {(r["file"], r["now"]) for r in json.load(open(f"{BASE}/review/rejected.json", encoding="utf-8"))}
files = args or sorted(glob.glob(f"{BASE}/review/stories_*.json") + glob.glob(f"{BASE}/review/pruefung_*.json") + glob.glob(f"{BASE}/review/hoeren_*.json") + glob.glob(f"{BASE}/review/mail_*.json") + glob.glob(f"{BASE}/review/satzbau_*.json"))
ok = bad = rej = 0
cache = {}
for fp in files:
    for i, f in enumerate(json.load(open(fp, encoding="utf-8"))):
        tag = f"{os.path.basename(fp)}#{i + 1}"
        if (f.get("file"), f.get("now")) in skip:
            rej += 1; continue
        path = f"{BASE}/{f['file']}"
        if f["file"].startswith("review/input_") or not os.path.exists(path):
            print("SKIP", tag, f["file"]); continue
        now, fix = f["now"], f["fix"]
        if path.endswith(".json"):
            if path not in cache:
                cache[path] = json.load(open(path, encoding="utf-8"))
            hits = []
            def walk(o, setter):
                if isinstance(o, str):
                    if now in o:
                        hits.append((o, setter))
                elif isinstance(o, list):
                    for j, v in enumerate(o):
                        walk(v, (lambda lst, j: lambda val: lst.__setitem__(j, val))(o, j))
                elif isinstance(o, dict):
                    for k, v in o.items():
                        walk(v, (lambda dct, k: lambda val: dct.__setitem__(k, val))(o, k))
            walk(cache[path], None)
            n = sum(h[0].count(now) for h in hits)
            if n != 1:
                bad += 1
                print(f"NOMATCH({n}) {tag} {f['file']} | {now[:90]}")
                continue
            hits[0][1](hits[0][0].replace(now, fix))
            ok += 1
            continue
        if path not in cache:
            cache[path] = open(path, encoding="utf-8").read()
        text = cache[path]
        n = text.count(now)
        if n != 1:
            bad += 1
            print(f"NOMATCH({n}) {tag} {f['file']} | {now[:90]}")
            continue
        cache[path] = text.replace(now, fix)
        ok += 1
if write:
    for path, obj in cache.items():
        if path.endswith(".json"):
            json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        else:
            open(path, "w", encoding="utf-8").write(obj)
print(f"applied {ok}, not matched {bad}, rejected {rej}", "(written)" if write else "(dry run)")
