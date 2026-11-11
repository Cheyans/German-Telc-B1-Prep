
B_WORDS = {"aber", "denn", "sondern", "doch", "oder", "und", "sowie", "bzw."}
C_WORDS = {"deshalb", "deswegen", "darum", "daher", "also", "trotzdem", "dennoch", "dann", "danach", "anschließend", "vorher", "davor",
           "zuerst", "zunächst", "schließlich", "zuletzt", "außerdem", "zusätzlich", "sonst", "stattdessen", "allerdings", "jedoch",
           "dagegen", "inzwischen", "seitdem", "dadurch", "dabei", "damit", "übrigens", "nämlich", "folglich", "somit", "hingegen", "zudem"}
E_WORDS = {"trotz", "wegen", "während", "statt", "anstatt", "aufgrund", "innerhalb", "außerhalb", "dank", "seit", "bis"}
W_WORDS = {"warum", "wieso", "weshalb", "wann", "wo", "wie", "was", "wer", "welche", "welcher", "welches", "welchen", "welchem", "wohin", "woher"}
FIN = ("VVFIN", "VAFIN", "VMFIN")
CLAUSE_START_PUNCT = {",", ";", ":", "„", "“", "(", "–", "-", "!", "?", "."}

def finite_of(tok):
    t = tok
    for _ in range(3):
        if t.tag_ in FIN:
            return t
        if t.head is t:
            break
        if t.head.tag_.startswith("V"):
            t = t.head
        else:
            break
    for c in tok.children:
        if c.tag_ in FIN:
            return c
    return None

END_OK = {",", ".", "!", "?", ":", ";", "“", "”", ")", "und", "oder", "aber", "–"}

def verb_final(v):
    nxt = v.doc[v.i + 1] if v.i + 1 < len(v.doc) else None
    return nxt is None or nxt.text in END_OK

def last_verb_in_clause(tok):
    best = None
    for t in tok.doc[tok.i + 1:]:
        if t.text in {",", ".", "!", "?", ";", ":", "“", "”"}:
            break
        if t.tag_.startswith("V"):
            best = t
    return best

def clause_initial(tok):
    if tok.is_sent_start:
        return True
    prev = tok.doc[tok.i - 1]
    if prev.text in CLAUSE_START_PUNCT:
        return True
    if prev.tag_ == "KON" and (prev.is_sent_start or tok.doc[prev.i - 1].text in CLAUSE_START_PUNCT):
        return True
    return False

def roles(doc):
    out = {}
    for tok in doc:
        low = tok.text.lower()
        prev = doc[tok.i - 1].text.lower() if tok.i > 0 else ""
        if tok.tag_ == "KOUS":
            key = low
            if low == "ob" and prev == "als":
                key = "als ob"
            elif low == "dass" and prev in ("ohne", "statt", "anstatt", "so"):
                key = {"ohne": "ohne dass", "statt": "statt dass", "anstatt": "statt dass", "so": "sodass"}[prev]
            v = finite_of(tok.head)
            if v is None or v.i <= tok.i:
                v = last_verb_in_clause(tok)
            if v is not None and v.i > tok.i and not verb_final(v):
                continue
            out[tok.i] = ("A", key, v.i if v is not None and v.i > tok.i else None)
        elif tok.tag_ == "KOUI":
            key = {"um": "um … zu", "ohne": "ohne … zu", "statt": "statt … zu", "anstatt": "statt … zu"}.get(low)
            inf = tok.head
            zu = next((c for c in inf.children if c.tag_ == "PTKZU"), None)
            if key and inf.i > tok.i and (inf.tag_ == "VVIZU" or (zu is not None and inf.tag_ in ("VVINF", "VAINF", "VMINF"))):
                out[tok.i] = ("Z", key, inf.i, zu.i if zu is not None else None)
        elif tok.tag_ == "KON" and low in B_WORDS:
            out[tok.i] = ("B", "bzw." if low == "bzw." else low, None)
        elif low in C_WORDS and tok.tag_ in ("ADV", "PROAV", "PAV", "ADJD"):
            if low == "nämlich":
                out[tok.i] = ("Cm", low, None)
            elif low == "also" and tok.i + 1 < len(doc) and doc[tok.i + 1].text == ",":
                continue
            elif clause_initial(tok):
                v = tok.head if tok.head.tag_ in FIN and tok.head.i > tok.i else None
                if v is None:
                    nxt = next((t for t in doc[tok.i + 1: tok.i + 4] if t.tag_ in FIN), None)
                    v = nxt
                out[tok.i] = ("C", low, v.i if v is not None else None)
            else:
                out[tok.i] = ("Cm", low, None)
        elif tok.tag_ == "APPR" and low in E_WORDS:
            out[tok.i] = ("E", "statt" if low == "anstatt" else low, None)
        elif tok.tag_ == "PRELS":
            v = finite_of(tok.head)
            if tok.i > 0 and doc[tok.i - 1].text in (",", "(") and v is not None and v.i > tok.i + 1 and verb_final(v):
                out[tok.i] = ("R", "der, die, das", v.i)
        elif tok.tag_ in ("PWAV", "PWS", "PWAT") and low.startswith("w") and (low in W_WORDS or low.startswith("wo")):
            key = "welch-" if low.startswith("welch") else low
            sent_text = tok.sent.text.rstrip("“” ")
            question = sent_text.endswith("?")
            prev_t = doc[tok.i - 1] if tok.i > 0 else None
            starts = tok.is_sent_start or (prev_t is not None and prev_t.text in ("„", "“", "(")) or (prev_t is not None and prev_t.tag_ == "KON" and (prev_t.is_sent_start or doc[prev_t.i - 1].text in ("„", "“")))
            if starts and question:
                v = next((t for t in doc[tok.i + 1: tok.i + 4] if t.tag_ in FIN), None)
                if v is not None:
                    out[tok.i] = ("Wd", key, v.i)
            elif prev_t is not None and prev_t.text == "," and not (low == "was" and any(t.text.lower() in ("alles", "etwas", "nichts", "vieles") for t in doc[max(0, tok.i - 5):tok.i - 1])):
                v = finite_of(tok.head)
                if v is None or v.i <= tok.i:
                    v = last_verb_in_clause(tok)
                if v is not None and v.i > tok.i + 1 and verb_final(v):
                    out[tok.i] = ("Wi", key, v.i)
        elif low in ("je",) and tok.tag_ == "ADV" and tok.i + 1 < len(doc) and doc[tok.i + 1].tag_ in ("ADJD", "ADV") :
            v = next((t for t in doc[tok.i + 1:] if t.tag_ in FIN or t.text == ","), None)
            out[tok.i] = ("D", "je … desto", v.i if v is not None and v.tag_ in FIN else None)
        elif low in ("desto", "umso") and tok.tag_ == "ADV":
            v = next((t for t in doc[tok.i + 1: tok.i + 5] if t.tag_ in FIN), None)
            out[tok.i] = ("D", "je … desto", v.i if v is not None else None)
        elif low in ("entweder", "sowohl", "weder", "zwar") and not (low == "zwar" and prev == "und"):
            out[tok.i] = ("D", {"entweder": "entweder … oder", "sowohl": "sowohl … als auch", "weder": "weder … noch", "zwar": "zwar … aber"}[low], None)
    return out
