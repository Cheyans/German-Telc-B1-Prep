import json
import os
import re
import sys
import unicodedata

BASE = os.path.dirname(os.path.abspath(__file__))
MARK = re.compile(r"\[\[([^\[\]|]+)\|([WGXR]\d{3,4})\]\]")
TRAPS = {"who", "when", "overstate", "flip", "paraphrase", "same-word", "none"}
PART_B = {"news": "Kurznachrichten", "ads": "Anzeigen", "voices": ("Interview", "Meinungen")}


def norm(s):
    s = unicodedata.normalize("NFC", s).replace(" ", " ").replace("­", "")
    s = s.replace("’", "'").replace("‘", "'").replace("´", "'")
    return re.sub(r"\s+", " ", s).strip()


def plain(s):
    return MARK.sub(lambda m: m.group(1), s)


def words(s):
    return len(re.findall(r"[A-Za-zÄÖÜäöüß0-9]+(?:[-'][A-Za-zÄÖÜäöüß0-9]+)*", plain(s)))


def parse_set(raw):
    lines = raw.splitlines()
    head = re.match(r"#\s*(\d{2})\s+\S", lines[0] if lines else "")
    parts, cur, item = {}, None, None
    for ln in lines[1:]:
        m2 = re.match(r"##\s+([AB])\s*·\s*(.+)$", ln)
        m3 = re.match(r"###\s+(.+)$", ln)
        if m2:
            cur = m2.group(1)
            parts[cur] = {"title": m2.group(2).strip(), "text": [], "items": []}
            item = None
        elif m3 and cur:
            item = {"label": m3.group(1).strip(), "text": []}
            parts[cur]["items"].append(item)
        elif cur:
            (item["text"] if item else parts[cur]["text"]).append(ln)
    return head, parts


def check(num):
    errors, warns = [], []
    ip = f"{BASE}/pruefung_inputs/set_{num}.json"
    sp = f"{BASE}/pruefung/set_{num}.md"
    qp = f"{BASE}/pquiz/pq_{num}.json"
    if not os.path.exists(ip):
        return [f"no input file {ip}"], warns
    inp = json.load(open(ip, encoding="utf-8"))
    if not os.path.exists(sp):
        return [f"missing {sp}"], warns
    raw = unicodedata.normalize("NFC", open(sp, encoding="utf-8").read())
    head, parts = parse_set(raw)
    if not head or head.group(1) != num:
        errors.append(f"first line must be '# {num} <Titel>'")
    if "—" in raw:
        errors.append("em dash (—) in the set")
    if '"' in raw:
        errors.append('straight double quote (") in the set, use „…“')
    if raw.count("[[") != raw.count("]]") or raw.count("[[") != len(MARK.findall(raw)):
        errors.append("broken [[form|ID]] markup somewhere")
    allowed = {t["id"] for t in inp["targets"]} | {t["id"] for t in inp["missed"]} | {x["id"] for x in inp["extras"]}
    used = {i for _, i in MARK.findall(raw)}
    for grp in ("targets", "missed", "extras"):
        miss = [t["id"] for t in inp[grp] if t["id"] not in used]
        if miss:
            errors.append(f"{grp} not used ({len(miss)}): {', '.join(miss)}")
    stray = sorted(used - allowed)
    if stray:
        errors.append(f"marked IDs not in your input file: {', '.join(stray)}")
    if "A" not in parts or "B" not in parts:
        errors.append("need '## A · Artikel · …' and '## B · …' sections")
        return errors, warns
    if not parts["A"]["title"].startswith("Artikel"):
        errors.append("Part A heading must be '## A · Artikel · <Überschrift>'")
    want = PART_B[inp["part_b"]]
    btitle = parts["B"]["title"]
    if not (btitle.startswith(want) if isinstance(want, str) else btitle.startswith(want)):
        errors.append(f"Part B heading must start with {want} (part_b = {inp['part_b']})")
    a_words = words("\n".join(parts["A"]["text"]))
    b_text = "\n".join(parts["B"]["text"] + [l for it in parts["B"]["items"] for l in [it["label"]] + it["text"]])
    b_words = words(b_text)
    if not 380 <= a_words <= 550:
        errors.append(f"Part A has {a_words} words (need 380–550)")
    if not 800 <= a_words + b_words <= 1250:
        errors.append(f"whole set has {a_words + b_words} words (need 800–1250)")
    items = parts["B"]["items"]
    if inp["part_b"] == "news":
        if [it["label"] for it in items] != ["1", "2", "3", "4", "5"]:
            errors.append("Kurznachrichten need items ### 1 … ### 5")
    if inp["part_b"] == "ads":
        letters = [re.match(r"([a-h])\)", it["label"]).group(1) if re.match(r"([a-h])\)", it["label"]) else "?" for it in items]
        if not 6 <= len(letters) <= 8 or letters != list("abcdefgh"[: len(letters)]):
            errors.append("Anzeigen need 6–8 items '### a) Titel', '### b) …' in order")
    text_norm = norm(plain(raw))
    if not os.path.exists(qp):
        errors.append(f"missing {qp}")
        return errors, warns
    try:
        q = json.load(open(qp, encoding="utf-8"))
    except Exception as e:
        return errors + [f"quiz is not valid JSON: {e}"], warns
    if q.get("set") != num:
        errors.append(f'quiz "set" must be "{num}"')
    qparts = q.get("parts", [])
    if len(qparts) != 2 or qparts[0].get("part") != "A" or qparts[1].get("part") != "B":
        errors.append("quiz needs exactly 2 parts: A then B")
        return errors, warns

    def ev_ok(tag, ev):
        e = norm(ev)
        if len(e) < 12:
            errors.append(f"{tag}: evidence too short")
        elif e not in text_norm:
            parts_ok = all(p.strip() in text_norm for p in re.split(r"(?<=[.!?…])\s+", e) if len(p.strip()) > 8)
            if not parts_ok:
                errors.append(f"{tag}: evidence not found word for word in the set")

    def style(tag, *ts):
        for t in ts:
            if not isinstance(t, str):
                continue
            if "—" in t:
                errors.append(f"{tag}: em dash")
            if '"' in t:
                errors.append(f"{tag}: straight double quote")
            if "[[" in t:
                errors.append(f"{tag}: markup left in the text")

    pa = qparts[0]
    if pa.get("type") != "abc" or len(pa.get("items", [])) != 5:
        errors.append("Part A quiz must be type abc with 5 items")
    else:
        traps = 0
        longest_right = 0
        for k, it in enumerate(pa["items"], 1):
            tag = f"A{k}"
            for f in ("q", "right", "wrong", "evidence", "why", "trap"):
                if f not in it:
                    errors.append(f"{tag}: missing {f}")
            if not isinstance(it.get("wrong"), list) or len(it.get("wrong", [])) != 2:
                errors.append(f"{tag}: wrong must be 2 options")
                continue
            if it.get("trap") not in TRAPS:
                errors.append(f"{tag}: trap must be one of {sorted(TRAPS)}")
            traps += it.get("trap") != "none"
            opts = [it["right"]] + it["wrong"]
            if len({norm(o).lower() for o in opts}) < 3:
                errors.append(f"{tag}: options must differ")
            if len(it["q"].split()) > 18:
                warns.append(f"{tag}: question longer than 18 words")
            for o in opts:
                if len(o.split()) > 14:
                    warns.append(f"{tag}: option longer than 14 words: {o[:40]}…")
            if len(it["right"]) >= max(len(w) for w in it["wrong"]):
                longest_right += 1
            style(tag, it["q"], *opts, it.get("why", ""))
            ev_ok(tag, it.get("evidence", ""))
        if traps < 3:
            errors.append(f"Part A: only {traps} of 5 items use a trap (need ≥ 3)")
        if longest_right >= 4:
            warns.append(f"Part A: the right option is the longest in {longest_right} of 5 items")
    pb = qparts[1]
    if inp["part_b"] in ("news", "ads"):
        kind = "headlines" if inp["part_b"] == "news" else "ads"
        if pb.get("type") != "match" or pb.get("kind") != kind:
            errors.append(f"Part B quiz must be type match, kind {kind}")
        else:
            prompts = pb.get("prompts", [])
            if len(prompts) != 5:
                errors.append("Part B needs 5 prompts")
            ans = [p.get("answer") for p in prompts]
            if kind == "headlines":
                opts = pb.get("options", [])
                ids = [o.get("id") for o in opts]
                if ids != list("abcdefgh"):
                    errors.append("headlines need 8 options with ids a–h")
                if [p.get("id") for p in prompts] != ["1", "2", "3", "4", "5"]:
                    errors.append("headline prompts need ids 1–5 (the news items)")
                if len(set(ans)) != 5 or not set(ans) <= set(ids):
                    errors.append("each news item needs a different headline from a–h")
                for o in opts:
                    style("headline", o.get("text", ""))
            else:
                letters = [re.match(r"([a-h])\)", it["label"]).group(1) for it in items if re.match(r"([a-h])\)", it["label"])]
                if ans.count("x") != 1:
                    errors.append("ads: exactly one situation must have answer x")
                real = [a for a in ans if a != "x"]
                if len(set(real)) != len(real) or not set(real) <= set(letters):
                    errors.append("ads: answers must be different ad letters from the set (or x)")
                for p in prompts:
                    if not p.get("text"):
                        errors.append(f"ads prompt {p.get('id')}: missing situation text")
            for p in prompts:
                tag = f"B{p.get('id')}"
                style(tag, p.get("text", ""), p.get("why", ""))
                ev_ok(tag, p.get("evidence", ""))
                if not p.get("why"):
                    errors.append(f"{tag}: missing why")
    else:
        its = pb.get("items", [])
        if pb.get("type") != "rf" or len(its) != 5:
            errors.append("Part B quiz must be type rf with 5 items")
        else:
            false_n = sum(1 for it in its if it.get("answer") is False)
            if not 2 <= false_n <= 3:
                errors.append(f"rf: {false_n} false statements (need 2–3)")
            traps = sum(1 for it in its if it.get("trap") not in (None, "none"))
            if traps < 3:
                errors.append(f"rf: only {traps} items use a trap (need ≥ 3)")
            for k, it in enumerate(its, 1):
                tag = f"RF{k}"
                if not isinstance(it.get("answer"), bool):
                    errors.append(f"{tag}: answer must be true or false")
                if it.get("trap") not in TRAPS:
                    errors.append(f"{tag}: trap must be one of {sorted(TRAPS)}")
                if len(it.get("s", "").split()) > 16:
                    warns.append(f"{tag}: statement longer than 16 words")
                style(tag, it.get("s", ""), it.get("why", ""))
                ev_ok(tag, it.get("evidence", ""))
    return errors, warns


def main():
    args = sys.argv[1:]
    if args == ["all"]:
        args = sorted(re.search(r"set_(\d+)", p).group(1) for p in os.listdir(f"{BASE}/pruefung_inputs") if p.startswith("set_"))
    bad = 0
    for num in args:
        num = num.zfill(2)
        errors, warns = check(num)
        print(f"set {num}: {len(errors)} errors, {len(warns)} warnings")
        for e in errors:
            print("  ERROR", e)
        for w in warns:
            print("  warn ", w)
        bad += bool(errors)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
