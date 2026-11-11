import json, re, sys, unicodedata
import os

BASE = os.path.dirname(os.path.abspath(__file__))

agent = sys.argv[1]
inp = json.load(open(f"{BASE}/agent_inputs/agent_{agent}.json"))
entries = {e["id"]: e for e in json.load(open(f"{BASE}/final_entries.json"))}
assigned = [w["id"] for w in inp["theme_words"]] + [w["id"] for w in inp["general_words"]]
aset = set(assigned)
MARK = re.compile(r"\[\[([^\[\]|]+)\|([WG]\d{3,4})\]\]")
PARTICLES = {"ab", "an", "auf", "aus", "bei", "ein", "fest", "fort", "her", "hin", "los", "mit", "nach", "vor", "weg", "zu", "zurück", "zusammen", "um", "durch", "über", "unter", "wieder", "statt", "teil", "dar", "entgegen", "herein", "heraus", "herunter", "hinterher", "vorbei", "weiter", "runter", "rauf", "raus", "kennen", "kaputt", "bekannt", "stehen", "spazieren", "sein", "lassen", "gehen", "werden", "geben", "sagen", "voraus", "hoch"}

def norm(s):
    s = s.lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss")
    return re.sub(r"[^a-z]", "", s)

def forms_of(e):
    t = re.sub(r"\(.*?\)", " ", e["text"])
    toks = re.findall(r"[A-Za-zÄÖÜäöüß]+", t + " " + e["lemma"])
    return {norm(x) for x in toks if len(x) >= 2}

def plausible(form, e):
    f = norm(form)
    if not f:
        return False
    fs = forms_of(e)
    if f in fs or f in PARTICLES:
        return True
    lem = norm(re.sub(r"^(der|die|das|sich)\s+", "", e["lemma"]))
    for cand in fs | {lem}:
        if len(cand) >= 3 and (f.startswith(cand[:4]) or cand.startswith(f[:4])):
            return True
        if len(cand) >= 4 and cand[:3] in f:
            return True
    return False

errors, warnings, used = [], [], {}
for st in inp["stories"]:
    path = f"{BASE}/stories/story_{st['num']}.md"
    try:
        txt = open(path).read()
    except FileNotFoundError:
        errors.append(f"missing file {path}")
        continue
    lines = txt.strip().splitlines()
    if not lines or not lines[0].startswith(f"# {st['num']} "):
        errors.append(f"{path}: first line must be '# {st['num']} <Titel>'")
    body = "\n".join(lines[1:])
    if "—" in body:
        errors.append(f"{path}: contains an em dash (—)")
    if '"' in body:
        errors.append(f"{path}: contains straight double quotes; use „…“")
    leftover = MARK.sub("", body)
    if "[[" in leftover or "]]" in leftover or re.search(r"\|[WG]\d", leftover):
        errors.append(f"{path}: malformed markup near: {leftover[max(0, leftover.find('[[') - 20):leftover.find('[[') + 40]!r}")
    marks = MARK.findall(body)
    words = len(re.findall(r"\w+", MARK.sub(lambda m: m.group(1), body)))
    print(f"story {st['num']}: {words} words, {len(marks)} marked words, {len(set(i for _, i in marks))} distinct IDs")
    for form, i in marks:
        used.setdefault(i, []).append((st["num"], form))
        if i not in aset:
            errors.append(f"story {st['num']}: [[{form}|{i}]] uses an ID that is not assigned to you")
        elif not plausible(form, entries[i]):
            warnings.append(f"story {st['num']}: check [[{form}|{i}]] (entry: {entries[i]['text'][:60]})")
missing = [i for i in assigned if i not in used]
for i in missing:
    errors.append(f"not used yet: {i} = {entries[i]['text'][:70]}")
gpath = f"{BASE}/glosses/agent_{agent}.json"
try:
    gl = json.load(open(gpath))
    for i in assigned:
        g = gl.get(i, "")
        if not isinstance(g, str) or not g.strip():
            errors.append(f"gloss missing for {i} ({entries[i]['text'][:40]})")
        elif len(g) > 70:
            warnings.append(f"gloss for {i} is long ({len(g)} chars)")
    extra = set(gl) - aset
    if extra:
        errors.append(f"gloss file has IDs not assigned to you: {sorted(extra)[:10]}")
except FileNotFoundError:
    errors.append(f"missing gloss file {gpath}")
except json.JSONDecodeError as ex:
    errors.append(f"gloss file is not valid JSON: {ex}")
print(f"\nassigned {len(assigned)} | used {len(set(used) & aset)} | missing {len(missing)}")
print(f"ERRORS ({len(errors)}):"); [print("  -", x) for x in errors[:80]]
print(f"WARNINGS ({len(warnings)}):"); [print("  -", x) for x in warnings[:60]]
sys.exit(1 if errors else 0)
