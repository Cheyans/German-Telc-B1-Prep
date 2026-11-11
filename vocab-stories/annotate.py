import glob
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

import spacy

import syntax_roles

BASE = os.path.dirname(os.path.abspath(__file__))
MARK = re.compile(r"\[\[([^\[\]|]+)\|([WGXR]\d{3,4})\]\]")
ARTICLE = re.compile(r"^(der|die|das)(\s*/\s*(der|die|das))?\s+")
GENDER = {"der": "Masc", "die": "Fem", "das": "Neut"}
OBJECT_PREFIX = re.compile(r"^(\(sich etwas\)|\(sich\)|sich etwas|sich|etwas|jemandem|jemanden)\s+")
SKIP_POS = {"PUNCT", "SPACE", "SYM", "X"}
CITY_WORDS = {"Halle"}
COMPOUND_SKIP = {"Fehlalarm", "Buchmesse", "Grundgesetz", "Abonnenten", "Argumente", "Experimente", "Auszubildende", "Hunderttausende",
                 "Hörverstehen", "Leseverstehen", "Schlafengehen", "Versehen", "Torwart", "Tourismusverband", "Tourismusverbands", "Veranstalter",
                 "Verkauf", "Mecklenburg-Vorpommern", "Neuanfang", "Neustart", "Stattdessen", "Biologieunterricht", "Großpösna",
                 "Asiatische", "Begleiter", "Büroauflösung", "Einsatz", "Garmisch-Partenkirchen", "Kompost", "Kroatisch", "Leipzig-Connewitz",
                 "Leipzig-Plagwitz", "Leipzig-Schönefeld", "Mitteldeutschland", "Neu-Delhi", "Organisator", "Paketzusteller", "Zusteller",
                 "Sprachbausteine", "Sprachbausteinen", "Versand", "Waldbrand", "Zugbegleiterin", "www.gruener-osten-leipzig.de", "Graz-Geidorf",
                 "Bezirkshauptmannschaft"}
TITLES = {"Herr", "Herrn", "Frau", "Familie", "Dr.", "Prof."}
SURNAME_WORDS = {"Braun", "Vogel", "Winter", "Koch", "Richter", "Weber", "Wolf", "Fischer", "Bauer", "Lang", "Klein", "Schwarz", "Sommer", "Fuchs", "Hahn", "Jung", "Kaiser", "König", "Krause", "Meier", "Schmidt", "Schulz", "Becker", "Hoffmann", "Krüger", "Neumann", "Lorenz", "Pohl", "Haase", "Engel", "Berger", "Frank", "Graf", "Busch", "Stein", "Licht", "Kurz"}
FUNC_POS = {"PRON", "DET", "ADP", "CCONJ", "SCONJ", "PART", "AUX", "NUM", "INTJ"}
PREPOSITIONS = {"ab", "an", "auf", "aus", "bei", "ein", "mit", "nach", "vor", "zu", "um", "durch", "über", "unter", "hinter", "gegen", "neben"}
JUNK = {"W2818", "W0943"}
NO_SINGLE_KEYS = {"G336"}
DU_FORMS = {"hast": "haben", "bist": "sein", "wirst": "werden", "weißt": "wissen", "kannst": "können", "musst": "müssen", "darfst": "dürfen", "sollst": "sollen", "willst": "wollen", "magst": "mögen", "hattest": "haben", "warst": "sein", "wurdest": "werden"}
LINKS = ("", "s", "n", "en", "e", "es")
PERSONAL = {"ich": "I", "mich": "me", "mir": "(to) me", "du": "you (informal)", "dich": "you (informal)", "dir": "(to) you (informal)",
            "er": "he; it", "ihn": "him; it", "ihm": "(to) him; (to) it", "sie": "she; they; it; (Sie) you (formal)",
            "wir": "we", "uns": "us; (to) us", "ihr": "you (plural, informal); (to) her", "euch": "you; (to) you (plural)",
            "ihnen": "(to) them; (Ihnen) (to) you (formal)"}
DA_WORDS = {"daran": "on it; about it (da-word)", "darauf": "on it; to it; after that (da-word)", "darin": "in it (da-word)",
            "darüber": "about it; over it (da-word)", "davon": "of it; from it; about it (da-word)", "dazu": "to it; for that; in addition (da-word)",
            "davor": "in front of it; before that (da-word)", "dahinter": "behind it (da-word)", "darunter": "under it; among them (da-word)",
            "daneben": "next to it (da-word)", "dadurch": "through it; because of that (da-word)", "daraus": "out of it (da-word)",
            "darum": "that's why; around it (da-word)", "dahin": "there, to that place", "daher": "that's why; from there",
            "dran": "on it (short for daran)", "drauf": "on it (short for darauf)", "drin": "in it (short for darin)",
            "worauf": "on what; for what (wo-word)", "worüber": "about what (wo-word)", "wovon": "of what; about what (wo-word)",
            "wozu": "what for (wo-word)", "woran": "on what; about what (wo-word)", "womit": "with what (wo-word)", "wofür": "for what (wo-word)"}
ORDINALS = {"zweit": "second", "dritt": "third", "viert": "fourth", "fünft": "fifth", "sechst": "sixth", "siebt": "seventh", "acht": "eighth",
            "neunt": "ninth", "zehnt": "tenth", "elft": "eleventh", "zwölft": "twelfth", "zwanzigst": "twentieth", "nächst": "next; nearest"}
INTERJECTIONS = {"oh": "oh (surprise)", "na": "well (Na ja: oh well; Na und?: so what?)", "ach": "oh (Ach so: I see)", "au": "ouch",
                 "aha": "I see", "hm": "hmm", "tja": "well (shrug)", "ups": "oops", "pst": "shh", "puh": "phew"}
VERB_FORMS = {"könnte": "können", "könnten": "können", "könntest": "können", "würde": "werden", "würden": "werden", "würdest": "werden",
              "hätte": "haben", "hätten": "haben", "hättest": "haben", "wäre": "sein", "wären": "sein", "wärst": "sein", "müsste": "müssen",
              "müssten": "müssen", "dürfte": "dürfen", "dürften": "dürfen", "möchte": "mögen", "möchten": "mögen", "möchtest": "mögen",
              "siehst": "sehen", "sieht": "sehen", "fährst": "fahren", "liest": "lesen", "nimmst": "nehmen", "gibst": "geben", "hilfst": "helfen",
              "sprichst": "sprechen", "isst": "essen", "läufst": "laufen", "schläfst": "schlafen", "trägst": "tragen", "triffst": "treffen",
              "vergisst": "vergessen", "tut": "tun", "tu": "tun", "seid": "sein", "sei": "sein", "komm": "kommen", "geh": "gehen", "sag": "sagen",
              "schau": "schauen", "hör": "hören", "warte": "warten", "nimm": "nehmen", "gib": "geben", "sieh": "sehen", "hilf": "helfen", "lies": "lesen"}
POSSESSIVE = {"mein": "my", "dein": "your (informal)", "sein": "his; its", "ihr": "her; their; (Ihr) your (formal)", "unser": "our", "euer": "your (plural)"}
CONTENT_POS = {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
ADJ_ENDINGS = ("", "e", "er", "es", "en", "em")
PARTICLES = {"ab", "an", "auf", "aus", "bei", "ein", "fest", "fort", "her", "hin", "los", "mit", "nach", "vor", "weg", "zu", "zurück", "zusammen", "um", "durch", "über", "unter", "wieder", "statt", "teil", "dar", "entgegen", "herein", "heraus", "herunter", "vorbei", "weiter", "hoch", "kennen", "kaputt", "bekannt", "spazieren", "sein", "frei", "voraus", "hinaus", "hinein", "zurecht", "runter", "rauf", "raus", "rein"}
UMLAUT = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "Ä": "A", "Ö": "O", "Ü": "U"})


def nfc(s):
    return unicodedata.normalize("NFC", s)


def clean(s):
    s = nfc(s)
    s = re.sub(r"\s*→.*$", "", s)
    s = re.sub(r"\s*\((?:D|A|CH)(?:\s*,\s*(?:D|A|CH))*\).*$", "", s)
    s = re.sub(r"\s*\((?:D|A|CH)\b.*$", "", s)
    s = re.sub(r"\s+(?:D|A|CH)(?:\s*,\s*(?:D|A|CH))*(?=:|\s|$).*$", "", s)
    s = re.sub(r"\s*\((?:[^()]*[\s.][^()]*)\)", "", s)
    if " " in re.sub(r"\s*\([^()]*\)", "", s).strip():
        s = re.sub(r"\s*\([^()]*\)", "", s)
    return s.strip(" ,;")


def heads_of(e):
    out = []
    first = clean(e["text"]).split(",")[0]
    for src in {clean(e["lemma"]), first}:
        parts = re.split(r"\s+/\s+", src)
        for part in parts:
            m = ARTICLE.match(part)
            art = m.group(0) if m else ""
            rest = part[len(art):]
            if " " not in rest and "/" in rest:
                for alt in rest.split("/"):
                    if alt:
                        out.append((art, alt))
            else:
                out.append((art, rest))
    return out


def expand_optional(word):
    if "(" not in word:
        return [word], []
    full = re.sub(r"[()]", "", word).replace("-", "")
    short = re.sub(r"\([^()]*\)", "", word).strip("-")
    return [full], [short] if short and short != full else []


def noun_plurals(lemma, text):
    m = re.match(r"^\s*(?:der|die|das)\s+[^,]+,\s*([^\s,/]+)", nfc(text))
    if not m:
        return set()
    p = m.group(1)
    if p == "-":
        return {lemma + "n"} if lemma.endswith(("el", "er")) else set()
    if p[0] in "¨“̈":
        suf = p.lstrip("¨“̈").lstrip("-")
        uml = re.sub(r"(au|Au|a|o|u|A|O|U)(?=[^aouäöüAOUÄÖÜ]*$)", lambda x: {"au": "äu", "Au": "Äu", "a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"}[x.group(1)], lemma, count=1)
        return {uml + suf, uml + suf + "n"}
    if p.startswith("-"):
        return {lemma + p[1:], lemma + p[1:] + "n"}
    if p[:1].isupper():
        return {p}
    return set()


def category(e):
    return {"noun": "noun", "verb": "verb"}.get(e["pos"], "other")


class Index:
    def __init__(self, entries):
        self.by_id = {e["id"]: e for e in entries}
        self.keys = defaultdict(list)
        secondary = defaultdict(list)
        self.stems = {}
        self.prefixes = {}
        self.forms = defaultdict(set)
        self.phrases = []
        self.verb_phrase_heads = defaultdict(list)
        self.verb_phrases = defaultdict(list)
        for e in entries:
            e["_genders"] = set()
            if e["id"] in JUNK:
                continue
            if e["id"] in NO_SINGLE_KEYS:
                continue
            for art, word in heads_of(e):
                for a in re.findall(r"der|die|das", art):
                    e["_genders"].add(GENDER[a])
                word = OBJECT_PREFIX.sub("", word.strip())
                if not word:
                    continue
                word = word.rstrip(".") if re.match(r"^[a-zäöü]{1,4}\.$", word) else word
                if " " in word:
                    if "…" not in word and "..." not in word:
                        self.phrases.append((word, e))
                    bits = OBJECT_PREFIX.sub("", word).lower().split()
                    if len(bits) == 2:
                        for last in bits[1].split("/"):
                            for first_alt in bits[0].split("/"):
                                self.verb_phrases[first_alt + " " + last].append(e)
                    if e["pos"] == "verb" or re.search(r"\b(gehen|sein|werden|lassen|geben|sagen|tun|leben|bleiben)$", word):
                        first = OBJECT_PREFIX.sub("", word).split()[0]
                        self.verb_phrase_heads[first.lower()].append(e)
                    continue
                if word.endswith("-"):
                    stem = word.rstrip("-")
                    if stem and stem[0].islower():
                        self.stems[stem.lower()] = e
                    elif len(stem) >= 3:
                        self.prefixes[stem] = e
                    continue
                full, short = expand_optional(word)
                for k in full:
                    self.keys[k.lower()].append(e)
                for k in short:
                    secondary[k.lower()].append(e)
            text = nfc(e["text"])
            for m in re.finditer(r"\(([A-ZÄÖÜ]{2,5})\)", text):
                self.keys[m.group(1).lower()].append(e)
            for m in re.finditer(r"(?:^|[\s/,;])(der|die|das)\s+([A-ZÄÖÜ][\wäöüß]+(?:-[A-ZÄÖÜ]?[\wäöüß]+)?)", text):
                if e["pos"] == "noun" and m.group(2).lower() not in self.keys or e not in self.keys.get(m.group(2).lower(), []):
                    if e["pos"] == "noun":
                        self.keys[m.group(2).lower()].append(e)
                        e["_genders"].add(GENDER[m.group(1)])
            if e["pos"] == "noun":
                for art, word in heads_of(e):
                    for pl in noun_plurals(OBJECT_PREFIX.sub("", word), text):
                        self.forms[pl].add(e["id"])
            if e["pos"] == "other":
                bits = [b.strip() for b in clean(text).split(",")]
                if len(bits) == 3 and bits[2].startswith("am "):
                    for b in (bits[1], bits[2][3:]):
                        st = re.sub(r"(en|e)$", "", b.lower()) if b.endswith("en") else b.lower()
                        if len(st) >= 3:
                            self.stems.setdefault(st, e)
            if e["pos"] == "verb":
                for f in re.split(r",\s*", clean(text)):
                    f = re.sub(r"^(hat|ist|hat/ist|ist/hat)\s+", "", f.strip())
                    if f and " " not in f and f.lower() not in PARTICLES:
                        self.forms[f].add(e["id"])
        for k, es in secondary.items():
            if k not in self.keys:
                self.keys[k].extend(es)
        for e in entries:
            m = re.match(r"^\((\w+)\)\s+(\w+)$", nfc(e["lemma"]).strip())
            if m and e["id"] not in JUNK:
                self.keys[m.group(2).lower()].append(e)
        for k in list(self.keys):
            seen, uniq = set(), []
            for e in self.keys[k]:
                if e["id"] not in seen:
                    seen.add(e["id"])
                    uniq.append(e)
            self.keys[k] = uniq
        self.verb_phrase_heads = {k: v for k, v in self.verb_phrase_heads.items() if k not in self.keys}

    def get(self, key, want):
        es = self.keys.get(key.lower(), [])
        if want == "noun":
            return [e for e in es if category(e) == "noun" or key[:1].isupper() and category(e) != "verb"]
        if want == "verb":
            return [e for e in es if category(e) == "verb"] or [e for e in es if category(e) == "other" and key.islower()]
        return [e for e in es if category(e) == "other" and not e["lemma"][:1].isupper()]


class Matcher:
    def __init__(self, index, author_forms):
        self.ix = index
        self.author_forms = author_forms
        self.names = set()

    def nouns(self, tok):
        ix = self.ix
        lemma, text = tok.lemma_, tok.text
        plural_only = [e for e in (ix.get(text, "noun") or []) if "(Pl" in e["text"]]
        cands = plural_only or ix.get(lemma, "noun") or ix.get(text, "noun")
        if not cands and text in ix.forms:
            cands = [ix.by_id[i] for i in ix.forms[text] if category(ix.by_id[i]) == "noun"]
        for base_word in (lemma, text):
            if not cands and base_word.endswith("in") and len(base_word) > 4:
                base = base_word[:-2]
                cands = ix.get(base, "noun") or ix.get(base.translate(UMLAUT), "noun")
            if not cands and base_word.endswith("innen") and len(base_word) > 7:
                base = base_word[:-5]
                cands = ix.get(base, "noun") or ix.get(base.translate(UMLAUT), "noun")
        if not cands:
            cands = [e for e in ix.keys.get(lemma.lower(), []) if category(e) == "verb"]
        if not cands:
            for n in range(len(text) - 3, 2, -1):
                if text[:n] in ix.prefixes:
                    cands = [ix.prefixes[text[:n]]]
                    break
        g = tok.morph.get("Gender")
        if len(cands) > 1 and g:
            narrowed = [e for e in cands if not e["_genders"] or g[0] in e["_genders"]]
            cands = narrowed or cands
        return cands

    def others(self, tok):
        ix = self.ix
        lemma, text = tok.lemma_, tok.text
        low = text.lower()
        if low == "was":
            was = ix.get("was", "other")
            if was:
                return was
        if low == "früher" and "W0893" in ix.by_id:
            return [ix.by_id["W0893"]]
        if tok.pos_ in ("ADJ", "DET", "PRON"):
            for end in ("en", "em", "er", "es", "e"):
                st = low[: -len(end)]
                if low.endswith(end) and len(st) >= 3 and st in ix.stems and ix.stems[st]["text"].split(",")[0].strip().endswith("-"):
                    return [ix.stems[st]]
        cands = ix.get(lemma, "other") or ix.get(low, "other") or ix.get(low.rstrip("."), "other")
        if not cands:
            for w in (low, lemma.lower()):
                for end in ADJ_ENDINGS:
                    if end and w.endswith(end) and len(w) - len(end) >= 3:
                        stem = w[: len(w) - len(end)]
                        cands = ix.get(stem, "other") or ([ix.stems[stem]] if stem in ix.stems else [])
                        if cands:
                            break
                    elif not end and w in ix.stems:
                        cands = [ix.stems[w]]
                        break
                if cands:
                    break
        if not cands and low in ix.verb_phrase_heads:
            cands = ix.verb_phrase_heads[low]
        return cands

    def adj_stem(self, w):
        ix = self.ix
        for end in ("e", "er", "es", "en", "em"):
            if w.endswith(end) and len(w) - len(end) >= 3:
                stem = w[: len(w) - len(end)]
                if stem in ix.stems:
                    return [ix.stems[stem]]
                c = ix.get(stem, "other")
                if c:
                    return c
        return []

    def compound(self, text):
        ix = self.ix
        if text in COMPOUND_SKIP:
            return []
        if "-" in text:
            parts = [p for p in text.split("-") if p]
            ids = []
            for part in parts:
                c = ix.get(part, "noun") or ix.get(part, "other") or ix.get(part.lower(), "other")
                if not c and part[:1].isupper():
                    c = self.compound(part)
                    c = [ix.by_id[i] for i in c] if c else []
                ids.extend(e["id"] for e in c[:1])
            return ids
        if not text[:1].isupper() or len(text) < 7:
            return []
        for cut in range(3, len(text) - 2):
            head = text[cut:]
            tail = [e for e in ix.get(head[:1].upper() + head[1:], "noun") if category(e) == "noun"] or [ix.by_id[i] for i in ix.forms.get(head[:1].upper() + head[1:], ()) if category(ix.by_id[i]) == "noun"]
            if not tail or len(head) < 3:
                continue
            first = text[:cut]
            for link in LINKS:
                if link and not first.endswith(link):
                    continue
                stem = first[: len(first) - len(link)] if link else first
                if len(stem) < 3:
                    continue
                f = ix.get(stem, "noun") or ix.get(stem.lower() + "n", "verb") or ix.get(stem.lower() + "en", "verb") or ix.get(stem.lower(), "other")
                if f:
                    return [f[0]["id"], tail[0]["id"]]
            return [tail[0]["id"]]
        return []

    def verbs(self, tok):
        ix = self.ix
        cands = ix.get(tok.lemma_, "verb")
        if not cands and tok.text in ix.forms:
            cands = [ix.by_id[i] for i in ix.forms[tok.text]]
        if not cands and tok.text.lower() in ix.verb_phrase_heads:
            cands = ix.verb_phrase_heads[tok.text.lower()]
        if not cands and tok.lemma_.lower() in ix.verb_phrase_heads:
            cands = ix.verb_phrase_heads[tok.lemma_.lower()]
        if not cands:
            cands = ix.get(tok.text.lower(), "other")
        if not cands and tok.text.lower() in DU_FORMS:
            cands = ix.get(DU_FORMS[tok.text.lower()], "verb")
        if not cands and tok.text.lower() in VERB_FORMS:
            cands = ix.get(VERB_FORMS[tok.text.lower()], "verb")
        if not cands and tok.text.lower().endswith("st") and len(tok.text) > 4:
            cands = ix.get(tok.text.lower()[:-2] + "en", "verb") or ix.get(tok.text.lower()[:-3] + "en", "verb")
        if not cands:
            cands = self.adj_stem(tok.text.lower())
        return cands

    def separable(self, doc):
        sep = {}
        self.sep_notes = {}
        for tok in doc:
            if tok.dep_ == "svp" and tok.head.pos_ in ("VERB", "AUX"):
                verb = tok.head
                cands = [e for e in self.ix.keys.get(tok.text.lower() + verb.lemma_.lower(), []) if category(e) == "verb"]
                if not cands:
                    cands = self.ix.verb_phrases.get(tok.text.lower() + " " + verb.lemma_.lower(), [])
                if cands:
                    ids = [e["id"] for e in cands]
                    sep[tok.i] = ids
                    sep[verb.i] = ids
                elif tok.text.lower() not in PREPOSITIONS and self.ix.get(tok.text.lower(), "other"):
                    sep[tok.i] = [e["id"] for e in self.ix.get(tok.text.lower(), "other")]
                else:
                    if re.fullmatch(r"[A-Za-zÄÖÜäöüß]+", tok.text):
                        self.sep_notes[tok.i] = f"separable verb part: {tok.text.lower()}{verb.lemma_.lower()} (not on the list as one word)"
        return sep

    def grammar(self, tok):
        low, tag = tok.text.lower(), tok.tag_
        if low in DA_WORDS:
            return DA_WORDS[low]
        if low in INTERJECTIONS and tok.pos_ in ("INTJ", "PART", "ADV", "X", "PROPN", "NOUN"):
            return INTERJECTIONS[low]
        if tok.pos_ == "ADV" and low == "morgen":
            return "tomorrow (heute, morgen, übermorgen)"
        for end in ("e", "er", "es", "en", "em"):
            if low.endswith(end) and low[: -len(end)] in ORDINALS:
                return ORDINALS[low[: -len(end)]] + " (ordinal number)"
        if tag == "ART" and low in ("der", "die", "das", "den", "dem", "des"):
            return "the (article: der, die, das)"
        if tag == "PRF":
            return "oneself: myself, yourself, himself, herself, themselves (reflexive)"
        formal = tok.text[:1].isupper() and not tok.is_sent_start
        if tag == "PPER" and low in ("sie", "ihnen"):
            if formal:
                return "you (formal)" if low == "sie" else "(to) you (formal)"
            if not tok.text[:1].isupper():
                return "she; they; it" if low == "sie" else "(to) them"
        if tag == "PPER" and low in PERSONAL:
            return PERSONAL[low]
        if tag in ("PPOSAT", "PPOSS") and low.startswith("ihr"):
            if formal:
                return "your (formal) (possessive)"
            if not tok.text[:1].isupper():
                return "her; their (possessive)"
        if tag in ("PPOSAT", "PPOSS"):
            for stem, g in POSSESSIVE.items():
                if low.startswith(stem if stem != "euer" else "eu"):
                    return g + " (possessive)"
        if tag in ("PRELS", "PRELAT"):
            return "who, which, that (relative pronoun)"
        if tag == "PDS" and low in ("der", "die", "das", "den", "dem", "denen", "dessen", "deren"):
            return "that, this one; who, which (pronoun)"
        return None

    def match(self, tok, sep):
        if tok.i in sep:
            return sep[tok.i], ""
        if tok.i in getattr(self, "sep_notes", {}):
            return self.sep_notes[tok.i], "g"
        if not re.search(r"[A-Za-zÄÖÜäöüß]", tok.text) or tok.dep_ == "svp":
            return None, None
        low0 = tok.text.lower()
        if tok.text in CITY_WORDS and tok.i > 0 and tok.doc[tok.i - 1].text.lower() in ("in", "aus", "nach", "von", "bei", "bis"):
            return None, "p"
        prev = tok.doc[tok.i - 1] if tok.i > 0 else None
        if prev is not None and tok.text[:1].isupper() and (prev.text in TITLES or (tok.text in SURNAME_WORDS and prev.pos_ == "PROPN" and prev.text[:1].isupper())):
            return None, "p"
        if tok.text in COMPOUND_SKIP:
            return None, None
        nxt = tok.doc[tok.i + 1] if tok.i + 1 < len(tok.doc) else None
        if tok.text in ("Liebe", "Lieber", "Liebes") and nxt is not None and nxt.text[:1].isupper() and (nxt.pos_ == "PROPN" or nxt.text in TITLES or nxt.text in ("Grüße", "Gruß", "Kolleginnen", "Kollegen", "Nachbarinnen", "Nachbarn", "Freunde", "Eltern")) and "W1475" in self.ix.by_id:
            return ["W1475"], ""
        if tok.text == "Seen" and "W2091" in self.ix.by_id:
            return ["W2091"], ""
        if tok.text == "Steuer" and prev is not None and prev.text.lower() in ("am", "ans", "hinterm"):
            return None, None
        if low0 == "lieber" and tok.pos_ == "ADV":
            return "rather, preferably (gern, lieber, am liebsten)", "g"
        if low0 == "liebsten" and tok.i > 0 and tok.doc[tok.i - 1].text.lower() == "am":
            return "most of all, best (gern, lieber, am liebsten)", "g"
        if tok.pos_ in ("NOUN", "PROPN"):
            cands = self.nouns(tok)
        elif tok.pos_ in ("VERB", "AUX"):
            cands = self.verbs(tok)
        else:
            cands = self.others(tok)
        if tok.pos_ in SKIP_POS:
            return None, None
        if not cands and tok.text.lower() in DU_FORMS:
            cands = self.ix.get(DU_FORMS[tok.text.lower()], "verb")
        if not cands and tok.text.lower() in VERB_FORMS:
            cands = self.ix.get(VERB_FORMS[tok.text.lower()], "verb")
        if not cands and tok.pos_ in ("NOUN", "PROPN") and tok.is_sent_start:
            cands = self.verbs(tok) or self.others(tok)
        if not cands and tok.pos_ not in ("NOUN", "PROPN"):
            cands = self.adj_stem(tok.text.lower())
        if not cands and len(tok.text) > 3 and tok.text in self.author_forms and tok.text.lower() not in PARTICLES and tok.tag_ != "PRF":
            cands = [self.ix.by_id[i] for i in sorted(self.author_forms[tok.text])]
            if tok.pos_ in FUNC_POS:
                cands = [e for e in cands if category(e) != "verb"]
        if not cands:
            g = self.grammar(tok)
            if g:
                return g, "g"
        if not cands and tok.text.isupper() and len(tok.text) <= 5:
            cands = self.ix.keys.get(tok.text.lower(), [])
        if not cands:
            if tok.pos_ == "PROPN" and "-" not in tok.text:
                return None, "p"
            parts = self.compound(tok.text)
            if parts:
                return parts, "c"
            return None, None
        return [e["id"] for e in cands], ""


def phrase_regex(phrase):
    words = phrase.replace(".", ". ").split()
    parts = []
    for w in words:
        if w.endswith("."):
            parts.append(re.escape(w[:-1]) + r"\.")
        elif len(w) > 4 and w.endswith("e") and w[0].isupper():
            parts.append(re.escape(w) + r"[nrsm]?")
        else:
            parts.append(re.escape(w))
    return re.compile(r"(?<![\wäöüß])" + r"\s*".join(parts) + r"(?![\wäöüß])", re.I)


def parse_paragraph(block):
    spans, out, last = [], "", 0
    for m in MARK.finditer(block):
        out += block[last:m.start()]
        start = len(out)
        out += m.group(1)
        spans.append((start, len(out), m.group(2)))
        last = m.end()
    out += block[last:]
    return out, spans


def annotate_text(nlp, matcher, phrases, text, spans, stats, ctx=None):
    marks = [(s, e, [i], True) for s, e, i in spans]
    taken = [(s, e) for s, e, _ in spans]
    for rx, entry in phrases:
        for m in rx.finditer(text):
            s, e = m.start(), m.end()
            if not any(a < e and s < b for a, b in taken):
                marks.append((s, e, [entry["id"]], False))
                taken.append((s, e))
    doc = nlp(text)
    sep = matcher.separable(doc)
    role_spans = {}
    if ctx is not None:
        for i, r in syntax_roles.roles(doc).items():
            t, key, vi = r[0], r[1], r[2]
            vis = [x for x in ([vi] + list(r[3:4])) if x is not None]
            stats["link"] += 1
            link = stats["link"]
            tok = doc[i]
            role_spans[(tok.idx, tok.idx + len(tok.text))] = f"k{t}:{link}:{key}"
            for x in vis:
                vt = doc[x]
                role_spans.setdefault((vt.idx, vt.idx + len(vt.text)), f"v{t}:{link}")
            stats["syn_counts"][f"{t}|{key}"] += 1
            pool = stats["syn_ex"][f"{t}|{key}"]
            if len(pool) < 40:
                sent = tok.sent
                base = sent.start_char
                pool.append({"n": ctx[0], "p": ctx[1], "t": sent.text, "w": len(sent),
                             "k": [tok.idx - base, tok.idx - base + len(tok.text)],
                             "v": [[doc[x].idx - base, doc[x].idx - base + len(doc[x].text)] for x in vis]})
    for tok in doc:
        s, e = tok.idx, tok.idx + len(tok.text)
        if any(a < e and s < b for a, b in taken):
            continue
        ids, kind = matcher.match(tok, sep)
        if kind == "g":
            marks.append((s, e, ids, "g"))
            taken.append((s, e))
            continue
        if kind == "p":
            marks.append((s, e, [], "p"))
            taken.append((s, e))
            continue
        if not ids:
            if tok.pos_ in CONTENT_POS and re.search(r"[a-zäöüß]", tok.text):
                stats["unmatched"][tok.lemma_] += 1
            continue
        marks.append((s, e, ids, kind or False))
        taken.append((s, e))
        if kind == "c":
            stats["compound"] += 1
            stats["covered_c"].update(ids)
            continue
        lvl = "b1" if any(matcher.ix.by_id[i]["level"] == "B1" for i in ids) else "basic"
        stats["auto_" + lvl] += 1
        if len(ids) > 1:
            stats["multi"][",".join(ids)] += 1
    for (s, e), role in role_spans.items():
        if not any(a < e and s < b for a, b in taken):
            marks.append((s, e, [], "r"))
            taken.append((s, e))
    marks.sort(key=lambda m: m[0])
    segs, last = [], 0
    for s, e, ids, author in marks:
        if s < last:
            continue
        if s > last:
            segs.append(text[last:s])
        role = role_spans.get((s, e), "")
        if author == "g":
            segs.append([text[s:e], "", "g", ids] + ([role] if role else []))
            last = e
            continue
        if author == "r":
            segs.append([text[s:e], "", "r", "", role])
            last = e
            continue
        flag = "a" if author is True else (author if author else "")
        seg = [text[s:e], ",".join(ids)] + ([flag] if flag else [])
        if role:
            seg = seg + [""] * (4 - len(seg)) + [role]
        segs.append(seg)
        if flag != "c":
            stats["covered"].update(ids)
        last = e
    if last < len(text):
        segs.append(text[last:])
    return segs


def parse_set(raw):
    lines = raw.splitlines()
    m = re.match(r"#\s*(\d+)\s+(.*)", lines[0])
    num, title = m.group(1).zfill(2), MARK.sub(lambda x: x.group(1), m.group(2)).strip()
    blocks, buf, part, label = [], [], None, ""

    def flush():
        if buf:
            blocks.append({"k": "p", "part": part, "label": label, "raw": " ".join(buf)})
            buf.clear()

    for ln in lines[1:]:
        s = ln.strip().replace("**", "")
        m2 = re.match(r"##\s+([AB])\s*·\s*(.+)$", s)
        m3 = re.match(r"###\s+(.+)$", s)
        if m2:
            flush()
            bits = [b.strip() for b in m2.group(2).split("·")]
            part, label = m2.group(1), bits[0]
            blocks.append({"k": "h2", "part": part, "label": label, "raw": " · ".join(bits[1:])})
        elif m3:
            flush()
            blocks.append({"k": "h3", "part": part, "label": label, "raw": m3.group(1).strip()})
        elif not s:
            flush()
        elif label == "Interview" and buf and SPEAKER.match(s):
            flush()
            buf.append(s)
        else:
            buf.append(s)
    flush()
    return num, title, blocks


SPEAKER = re.compile(r"^([A-ZÄÖÜ][^:\[\]]{1,40}?):\s+(.*)$")


def pruefung_pass(nlp, index, phrases, story_forms, stats, out):
    extras = json.load(open(f"{BASE}/extras.json", encoding="utf-8"))
    for x in extras:
        index.by_id.setdefault(x["id"], {"id": x["id"], "level": "X" if x["kind"] == "extra" else "AT", "pos": x["pos"], "text": x["word"], "lemma": x["word"]})
    set_paths = sorted(glob.glob(f"{BASE}/pruefung/set_*.md"))
    raws = {p: nfc(open(p, encoding="utf-8").read().strip()) for p in set_paths}
    forms = defaultdict(set, {k: set(v) for k, v in story_forms.items()})
    for raw in raws.values():
        for form, i in MARK.findall(raw):
            if " " not in form and i[0] != "R":
                forms[form].add(i)
    matcher = Matcher(index, forms)
    pstats = {"auto_b1": 0, "auto_basic": 0, "compound": 0, "unmatched": Counter(), "multi": Counter(), "covered": set(), "covered_c": set(),
              "link": stats["link"], "syn_counts": Counter(), "syn_ex": defaultdict(list)}
    out["pruefung"], out["pquiz"] = {}, {}
    for p in set_paths:
        num, title, blocks = parse_set(raws[p])
        done = []
        for k, b in enumerate(blocks):
            raw = b.pop("raw")
            if b["k"] == "p" and b["label"] == "Interview":
                m = SPEAKER.match(raw)
                if m:
                    b["sp"], raw = m.group(1).strip(), m.group(2)
            text, spans = parse_paragraph(raw)
            b["s"] = annotate_text(nlp, matcher, phrases, text, spans, pstats, ctx=("P" + num, k) if b["k"] == "p" else None)
            done.append(b)
        out["pruefung"][num] = {"t": title, "blocks": done}
    cover = set(pstats["covered"])

    def ann(t):
        return annotate_text(nlp, matcher, phrases, nfc(t), [], pstats) if t else []

    for qp in sorted(glob.glob(f"{BASE}/pquiz/pq_*.json")):
        try:
            d = json.load(open(qp, encoding="utf-8"))
            num = d["set"]
            parts = []
            for part in d["parts"]:
                if part["type"] == "abc":
                    parts.append({"items": [{"q": ann(it["q"]), "right": ann(it["right"]), "wrong": [ann(w) for w in it["wrong"]]} for it in part["items"]]})
                elif part["type"] == "rf":
                    parts.append({"items": [ann(it["s"]) for it in part["items"]]})
                else:
                    parts.append({"options": [ann(o["text"]) for o in part.get("options", [])], "prompts": [ann(x.get("text", "")) for x in part["prompts"]]})
        except Exception as e:
            print("skipping", os.path.basename(qp), e)
            continue
        out["pquiz"][num] = parts
    stats["link"] = pstats["link"]
    return cover


def main():
    entries = [dict(e) for e in json.load(open(f"{BASE}/final_entries.json", encoding="utf-8"))]
    index = Index(entries)
    phrases = sorted(((phrase_regex(p), e) for p, e in index.phrases if e["pos"] != "verb"), key=lambda x: -len(x[0].pattern))
    author_forms = defaultdict(set)
    story_paths = sorted(glob.glob(f"{BASE}/stories/story_*.md"))
    raws = {p: nfc(open(p, encoding="utf-8").read().strip()) for p in story_paths}
    for raw in raws.values():
        for form, i in MARK.findall(raw):
            if " " not in form:
                author_forms[form].add(i)
    nlp = spacy.load("de_core_news_md")
    matcher = Matcher(index, author_forms)
    stats = {"auto_b1": 0, "auto_basic": 0, "compound": 0, "unmatched": Counter(), "multi": Counter(), "covered": set(), "covered_c": set(),
             "link": 0, "syn_counts": Counter(), "syn_ex": defaultdict(list)}
    out = {"stories": {}, "quiz": {}, "titles": {}}
    for p in story_paths:
        lines = raws[p].splitlines()
        num = re.match(r"#\s*(\d+)", lines[0]).group(1).zfill(2)
        paras = []
        for block in re.split(r"\n\s*\n", "\n".join(lines[1:]).strip()):
            block = " ".join(l.strip() for l in block.splitlines() if l.strip())
            if block:
                text, spans = parse_paragraph(block)
                paras.append(annotate_text(nlp, matcher, phrases, text, spans, stats, ctx=(num, len(paras))))
        out["stories"][num] = paras
        out["titles"][num] = re.match(r"#\s*\d+\s+(.*)", lines[0]).group(1).strip()
    story_cover = set(stats["covered"])
    for qp in sorted(glob.glob(f"{BASE}/quiz/quiz_*.json")):
        try:
            d = json.load(open(qp, encoding="utf-8"))
            num = d["story"]
        except Exception as e:
            print("skipping", os.path.basename(qp), e)
            continue
        qs = []
        for q in d.get("questions", []):
            try:
                qs.append({
                    "q": annotate_text(nlp, matcher, phrases, nfc(q["q"]), [], stats),
                    "right": annotate_text(nlp, matcher, phrases, nfc(q["right"]), [], stats),
                    "wrong": [annotate_text(nlp, matcher, phrases, nfc(w), [], stats) for w in q["wrong"]],
                })
            except Exception as e:
                print("skipping a question in", num, e)
        out["quiz"][num] = qs
    examples = {}
    for key, pool in stats["syn_ex"].items():
        good = [x for x in pool if 5 <= x["w"] <= 24 and (x["v"] or key[0] in "BDE" or key.startswith("Cm"))] or pool
        good.sort(key=lambda x: (x["n"], x["w"]))
        picked, seen = [], set()
        for x in good:
            if x["n"] in seen:
                continue
            seen.add(x["n"])
            picked.append({k: v for k, v in x.items() if k != "w"})
            if len(picked) == 3:
                break
        examples[key] = picked
    out["syntax"] = {"counts": dict(stats["syn_counts"]), "examples": examples}
    pr_cover = pruefung_pass(nlp, index, phrases, author_forms, stats, out)
    json.dump(out, open(f"{BASE}/annotated.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    never = [e for e in entries if e["id"] not in story_cover]
    print("auto marks: B1", stats["auto_b1"], "| basics", stats["auto_basic"], "| compounds", stats["compound"], "| multi-ID tokens", sum(stats["multi"].values()))
    print("entries never tappable in the stories:", len(never), "| B1:", sum(1 for e in never if e["level"] == "B1"))
    if out["pruefung"]:
        b1 = [e for e in entries if e["level"] == "B1"]
        print("Prüfung sets:", len(out["pruefung"]), "| B1 entries tappable there:", sum(1 for e in b1 if e["id"] in pr_cover), "of", len(b1))
    if "-v" in sys.argv:
        print("top unmatched content lemmas:", ", ".join(f"{k}:{v}" for k, v in stats["unmatched"].most_common(80)))
        print("multi:", stats["multi"].most_common(25))
        print("never:", "; ".join(f"{e['id']} {e['level']} {e['text'][:28]}" for e in never[:200]))


if __name__ == "__main__":
    main()
