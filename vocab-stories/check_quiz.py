import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
MARK = re.compile(r"\[\[([^\[\]|]+)\|([WG]\d{3,4})\]\]")
FIELDS = ("q", "right", "wrong", "evidence", "why")


def norm(s):
    s = unicodedata.normalize("NFC", s).replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def story_paras(num):
    raw = open(f"{BASE}/stories/story_{num}.md", encoding="utf-8").read()
    body = "\n".join(raw.splitlines()[1:])
    paras = [norm(MARK.sub(lambda m: m.group(1), p)) for p in re.split(r"\n\s*\n", body) if p.strip()]
    return paras, {i for _, i in MARK.findall(raw)}


def check(num):
    errors, warns = [], []
    path = f"{BASE}/quiz/quiz_{num}.json"
    if not os.path.exists(path):
        return [f"missing {path}"], warns
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"invalid JSON: {e}"], warns
    paras, ids = story_paras(num)
    qs = d.get("questions", [])
    if d.get("story") != num:
        errors.append(f'"story" must be "{num}"')
    if len(qs) != 5:
        errors.append(f"need 5 questions, found {len(qs)}")
    last = -1
    for k, q in enumerate(qs, 1):
        tag = f"Q{k}"
        missing = [f for f in FIELDS if f not in q]
        if missing:
            errors.append(f"{tag}: missing {', '.join(missing)}")
            continue
        if not isinstance(q["wrong"], list) or len(q["wrong"]) != 2:
            errors.append(f"{tag}: wrong must be a list of 2 options")
            continue
        opts = [q["right"]] + q["wrong"]
        for t in [q["q"]] + opts + [q["evidence"], q["why"]]:
            if "—" in t:
                errors.append(f"{tag}: em dash")
            if '"' in t:
                errors.append(f"{tag}: straight double quote, use „…“")
            if "[[" in t or "]]" in t:
                errors.append(f"{tag}: markup left in the text")
        if len({norm(o).lower() for o in opts}) < 3:
            errors.append(f"{tag}: the three options must differ")
        if len(q["q"]) > 150:
            errors.append(f"{tag}: question longer than 150 characters")
        for o in opts:
            if len(o) > 100:
                errors.append(f"{tag}: option longer than 100 characters: {o[:40]}")
        if len(q["why"]) > 260:
            errors.append(f"{tag}: why longer than 260 characters")
        ev = norm(q["evidence"])
        pos = next((i for i, p in enumerate(paras) if ev and ev in p), -1)
        if pos < 0:
            errors.append(f"{tag}: evidence not found word for word in one paragraph: {ev[:70]}")
        else:
            if pos < last:
                warns.append(f"{tag}: evidence comes before the previous question's, keep story order")
            last = max(last, pos)
        for w in q.get("words", []):
            if w not in ids:
                errors.append(f"{tag}: {w} is not marked in this story")
        lr, lw = len(q["right"]), max(len(x) for x in q["wrong"])
        if lr > 1.6 * lw and lr - lw > 15:
            warns.append(f"{tag}: the right answer is much longer than the wrong ones")
        if len(norm(q["right"])) > 12 and norm(q["right"]).rstrip(".").lower() in ev.lower():
            warns.append(f"{tag}: the right answer copies the text word for word, paraphrase it")
    return errors, warns


if __name__ == "__main__":
    for num in sys.argv[1:]:
        errors, warns = check(num.zfill(2))
        print(f"story {num}: ERRORS ({len(errors)}):")
        for e in errors:
            print("  " + e)
        print(f"story {num}: WARNINGS ({len(warns)}):")
        for w in warns:
            print("  " + w)
