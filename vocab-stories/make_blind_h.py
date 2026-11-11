import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))
H = f"{BASE}/hoeren"
PRIV = os.environ.get("B1_PRIVATE", os.path.join(BASE, "private"))
TT = os.path.join(PRIV, "allango-676865", "transcripts")
TU = os.path.join(PRIV, "allango-676830", "official")
def blind_t(nn):
    d = json.load(open(f"{H}/h_{nn}.json", encoding="utf-8"))
    out = {"file": f"h_{nn}", "transcript": f"{TT}/track_{nn}.txt",
           "tasks": [{"part": t["part"], "from": t["from"], "to": t["to"], "intro": t["intro"],
                      "items": [{"k": i + 1, "t": it.get("t"), "s": it["s"]} for i, it in enumerate(t["items"])]} for t in d["tasks"]]}
    json.dump(out, open(f"{H}/blind/hb_{nn}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
def blind_u(n):
    d = json.load(open(f"{H}/u_{n}.json", encoding="utf-8"))
    out = {"file": f"u_{n}", "transcripts": {tr: f"{TU}/track_{tr}.txt" for tr in d["tracks"]}, "intro": d["intro"],
           "items": [{"k": i + 1, "tr": it["tr"], "s": it["s"]} for i, it in enumerate(d["items"])]}
    json.dump(out, open(f"{H}/blind/hb_u{n}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for a in sys.argv[1:]:
    (blind_u(a[1:]) if a.startswith("u") else blind_t(a))
    print("blind", a)
