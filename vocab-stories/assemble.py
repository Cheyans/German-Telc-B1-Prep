import json, re
from collections import Counter, defaultdict
E = json.load(open("/tmp/vs/entries.json"))
DROP = {"W0561", "W1338", "W1626", "W2155", "W2787", "W1947", "W2479", "W2880", "W2121", "W0388", "W0465", "W1118", "W1823", "W2393", "W2865"}
FIX = {"W1092": "Haupt- / die Hauptstadt, ¨-e", "W1691": "Not- / die Notaufnahme, -n", "W1383": "Kriminal- / die Kriminalpolizei", "W1963": "rück- / die Rückfahrt, -en", "W2156": "Sonder- / das Sonderangebot, -e"}
theme = {}
for k in range(1, 5):
    for line in open(f"/tmp/vs/themes_{k}.txt"):
        code, ids = line.split(":", 1)
        for i in ids.split():
            theme["W" + i] = code.strip()
G_B1 = set("""Abo Akku Azubi bzw. ca. d. h. EG OG UG Kfz Pkw Lkw vgl. WG
Bikini bloggen Blog Camp campen Castingshow Chat chatten checken Chip City Comic E-Bike E-Book faxen Fax Festival Fitness global googeln Hit Homepage Jazz jobben Ketchup Killer Link live Mailbox mailen Manager Mobilbox Mountainbike Plattform Poster Puzzle Sandwich Show Snack Software Song Spot Steak surfen Swimmingpool Terminal Tour Trend twittern User
Antwortbogen ankreuzen Aussage Durchsage Einleitung Folie Hilfsmittel Kommentar Moderator Modul Präsentation Rückmeldung Struktur Textaufbau übertragen
Krippe Kindertagesstätte Grundschule Realschule Gesamtschule Berufsschule Sonderschule Gymnasium Fachhochschule Hochschule Volkshochschule Mittelschule
Chemie Geografie Mathematik Philosophie Physik Biologie befriedigend ausreichend mangelhaft ungenügend
nördlich östlich südlich westlich Europäer europäisch Österreicher österreichisch Schweizer schweizerisch Grieche griechisch Türke türkisch Ukrainer ukrainisch
Bund Bundeskanzler Bundestag Bundespräsident Bürgermeister Demokratie demokratisch EU Gemeinde konservativ liberal Minister Parlament Partei Regierung Staat staatlich Bundesland Bundesrepublik
Affe Bär Biene Elefant Ente Fliege Giraffe Hase Insekt Krokodil Löwe Mücke Pinguin Schaf Schildkröte Schlange
Quadratmeter Grad Prozent Gramm Pfund Pfingsten Silvester Nationalfeiertag Neujahr
stündlich wöchentlich monatlich jährlich Jahrzehnt Jahrhundert Jahrtausend tagsüber werktags wochentags Sonnabend sonnabends Mitternacht""".split())
GTHEME = {"Abkürzungen": None, "Anglizismen": None, "Anweisungssprache": "PRU", "Bildungseinrichtungen": "LER", "Schulfächer": "LER", "Schulnoten": "LER",
          "Farben": "GEN", "Himmelsrichtungen": "VER", "Länder": "POL", "Politik": "POL", "Tiere": "NAT", "Maße": None, "Zahlen": "GEN",
          "Feiertage": "KUL", "Jahreszeiten": "GEN", "Monate": "GEN", "Tageszeiten": "GEN", "Uhrzeit": "GEN", "Wochentage": "GEN", "Zeitangaben": "GEN"}
SPECIAL = {"Abo": "MED", "Akku": "MED", "Azubi": "ARB", "EG": "WOH", "OG": "WOH", "UG": "WOH", "ICE": "VER", "Kfz": "VER", "Lkw": "VER", "Pkw": "VER", "PC": "MED", "SMS": "MED", "TV": "MED", "WC": "WOH", "WG": "WOH", "DVD": "MED",
           "Bikini": "FRE", "Camp": "FRE", "campen": "FRE", "Castingshow": "MED", "Comic": "FRE", "Festival": "KUL", "fit": "FRE", "Fitness": "FRE", "Hit": "KUL", "Jazz": "KUL", "Mountainbike": "FRE", "Puzzle": "FRE", "Show": "MED", "Song": "KUL", "Swimmingpool": "FRE", "Tour": "VER", "E-Bike": "VER", "Poster": "KUL", "Killer": "MED",
           "Cola": "ESS", "Hamburger": "ESS", "Ketchup": "ESS", "Sandwich": "ESS", "Snack": "ESS", "Steak": "ESS", "Job": "ARB", "jobben": "ARB", "Manager": "ARB", "Team": "ARB", "Terminal": "VER", "Spot": "MED",
           "Quadratmeter": "WOH", "Grad": "NAT", "über Null / unter Null": "NAT", "plus / minus": "NAT", "Prozent": "POL", "Gramm": "ESS", "Pfund": "ESS", "Kilo(gramm)": "ESS", "Liter": "ESS", "Meter": "VER", "Zentimeter": "VER", "Kilometer": "VER", "Kilometer pro Stunde": "VER", "Euro": "EIN", "Cent": "EIN"}
out = []
for e in E:
    if e["id"] in DROP:
        continue
    e = dict(e)
    if e["id"] in FIX:
        e["text"] = FIX[e["id"]]
        e["lemma"] = FIX[e["id"]].split("/")[1].split(",")[0].strip()
        e["lemma"] = re.sub(r"^(der|die|das)\s+", "", e["lemma"])
    if e["src"].startswith("group:"):
        g = e["src"].split(":")[1]
        key = e["lemma"].split(" (")[0].split(",")[0].strip()
        key = re.sub(r"^(der|die|das)(/(der|die|das))?\s+", "", key)
        first = key.split(" ")[0] if g not in ("Maße",) else key
        e["level"] = "B1" if (first in G_B1 or key in G_B1) else "A2"
        e["theme"] = SPECIAL.get(first) or SPECIAL.get(key) or GTHEME.get(g) or ("MED" if g == "Anglizismen" else "GEN")
    else:
        e["theme"] = theme.get(e["id"], "GEN") if e["level"] == "B1" else None
    out.append(e)
json.dump(out, open("/tmp/vs/final_entries.json", "w"), ensure_ascii=False, indent=0)
b1 = [e for e in out if e["level"] == "B1"]
print("total entries:", len(out), "| B1 targets:", len(b1), "| basics:", len(out) - len(b1))
print(Counter(e["theme"] for e in b1).most_common())
