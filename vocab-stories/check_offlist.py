import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))


def main():
    forms = json.load(open(f"{BASE}/offlist/forms.json", encoding="utf-8"))["forms"]
    g = {}
    for k in range(1, 5):
        p = f"{BASE}/offlist/gloss_{k}.json"
        if os.path.exists(p):
            g.update(json.load(open(p, encoding="utf-8")))
    b4 = [x["form"] for x in json.load(open(f"{BASE}/offlist/batch_4.json", encoding="utf-8"))]
    want = set(forms) | set(b4)
    errs = []
    missing = sorted(want - set(g))
    extra = sorted(set(g) - want)
    if missing:
        errs.append(f"{len(missing)} forms without an entry: {', '.join(missing[:12])}")
    if extra:
        errs.append(f"{len(extra)} entries for forms not in the batches: {', '.join(extra[:12])}")
    for f, v in sorted(g.items()):
        d, gl, k = v.get("d", ""), v.get("g", ""), v.get("k", "")
        if not d or not gl:
            errs.append(f"{f}: empty d or g")
        if k not in ("word", "name", "abbr", "interj"):
            errs.append(f"{f}: k must be word, name, abbr or interj")
        if "—" in d + gl:
            errs.append(f"{f}: em dash")
        if f[:1].isupper() and k == "word" and not re.match(r"^(der|die|das|der/die)\s", d) and d[:1].isupper() and " " not in d:
            errs.append(f"{f}: capitalized noun without article: {d}")
        if len(gl.split()) > 9:
            errs.append(f"{f}: gloss longer than 9 words")
    print(f"entries: {len(g)} of {len(want)} | problems: {len(errs)}")
    for e in errs[:40]:
        print("  ", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
