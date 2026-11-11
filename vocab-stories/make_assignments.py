import json, random
E = json.load(open("/tmp/vs/final_entries.json"))
byid = {e["id"]: e for e in E}
b1 = [e for e in E if e["level"] == "B1"]
gen = sorted([e["id"] for e in b1 if e["theme"] == "GEN"])
random.Random(7).shuffle(gen)
AGENTS = [
 ("A", [("01", "Der Prüfungstag", "Mateo schreibt die telc-B1-Prüfung: Anmeldung, Prüfungsraum, Anweisungen, Antwortbogen, mündliche Prüfung mit Partnerin"), ("11", "Der Deutschkurs", "Mateos Kurs an der Volkshochschule: Lernen, Schule in verschiedenen Ländern, Noten, Hausaufgaben, Studium")], ["PRU", "LER"]),
 ("B", [("02", "Die neue Wohnung", "Lena zieht in Leipzig ein: Lage, Einrichtung, Hausmeister, Mülltrennung, Reparatur"), ("15", "Nachbarn und Hausordnung", "Leben im Haus: Nachbarn, Lärm, Putzen, Probleme in der Wohnung, Handwerker")], ["WOH"]),
 ("C", [("03", "Die Bewerbung", "Mateo sucht eine neue Stelle: Anzeige, Lebenslauf, Vorstellungsgespräch, Vertrag"), ("14", "Ein Tag im Büro", "Lena und ihr Kollege Jonas: Besprechung, Projekt, Stress, Kollegen, Feierabend")], ["ARB"]),
 ("D", [("04", "Auf dem Amt", "Lena meldet sich an, Formulare, Ausweis, Termine, Bürgeramt, Ausländerbehörde für Mateo"), ("17", "Bank, Post und Versicherung", "Konto eröffnen, Überweisung, Einschreiben, Versicherung, Rechnungen")], ["AMT"]),
 ("E", [("05", "Beim Arzt", "Lena ist erkältet: Termin, Wartezimmer, Untersuchung, Rezept, Apotheke"), ("16", "Der Unfall", "Paul hat einen Unfall beim Skifahren: Notruf, Krankenhaus, Operation, Pflege, Gesundheit")], ["GES"]),
 ("F", [("06", "Einkaufen und umtauschen", "Lena kauft Kleidung und ein Gerät: Angebot, Kasse, Quittung, Umtausch, Reklamation"), ("18", "Geld und Online-Shopping", "Sparen, Preise, Bestellung im Internet, Lieferung, Garantie")], ["EIN"]),
 ("G", [("07", "Mit Bahn und Bus", "Mateo fährt zur Arbeit und nach Berlin: Fahrkarte, Verspätung, Umleitung, Stau, Fahrrad"), ("19", "Urlaub an der Ostsee", "Lena und Aylin reisen: Buchung, Hotel, Übernachtung, Ausflug, Rückfahrt")], ["VER"]),
 ("H", [("13", "Im Restaurant", "Lena trifft Freunde im Restaurant: Speisekarte, Bestellung, Kellner, Trinkgeld"), ("20", "Kochen für Freunde", "Mateo kocht für eine Party: Einkaufen, Rezept, Zutaten, Kochen, Gäste")], ["ESS"]),
 ("I", [("10", "Ärger mit dem Internet", "Lenas Internet funktioniert nicht: Anbieter, Hotline, Computer, Handy, Daten"), ("21", "Medien im Alltag", "Zeitung, Radio, Fernsehen, soziale Medien, eine Reportage über Leipzig")], ["MED"]),
 ("J", [("09", "Die Diskussion im Kurs", "Mateos Kurs diskutiert ein Thema (Handys an Schulen): Meinungen, Argumente, Vorschläge, sich einigen"), ("22", "Streit und Versöhnung", "Lena und Aylin streiten und versöhnen sich: Vorwürfe, Entschuldigung, Kompromiss")], ["KOM"]),
 ("K", [("08", "Ein freies Wochenende", "Freizeit, Sport, Hobbys, Verabredungen, Ausflug, Spiel im Stadion"), ("12", "Das Familienfest", "Lenas Familie in Hamburg: Geburtstag der Oma, Verwandte, Erinnerungen, Beziehungen")], ["FRE", "FAM"]),
 ("L", [("23", "Gefühle", "Mateo vor einer wichtigen Entscheidung: Gefühle, Charakter, Freunde geben Rat"), ("24", "Kultur und Feste", "Konzert, Theater, Museum, Weihnachtsmarkt, Karneval, Silvester")], ["GEF", "KUL"]),
 ("M", [("25", "Natur und Wetter", "Wanderung im Gebirge, Wetter, Landschaft, Tiere, Gewitter"), ("26", "Umwelt", "Umweltschutz in Leipzig: Müll, Energie, Klima, ein Projekt mit Kindern im Tierpark")], ["NAT"]),
 ("N", [("27", "Gesellschaft und Politik", "Wahlen, Bürgermeister, Demokratie, Integration, Mateos Einbürgerung"), ("28", "Der Einbruch", "Ein Einbruch im Haus: Polizei, Zeugen, Verdacht, Gericht, Urteil")], ["POL"]),
]
summary = {}
for ai, (agent, stories, themes) in enumerate(AGENTS):
    ids = [e["id"] for e in b1 if e["theme"] in themes]
    g = gen[ai * 35:(ai + 1) * 35]
    data = {"agent": agent, "stories": [{"num": n, "title": t, "focus": f} for n, t, f in stories],
            "theme_words": [{"id": i, "entry": byid[i]["text"], "theme": byid[i]["theme"]} for i in ids],
            "general_words": [{"id": i, "entry": byid[i]["text"]} for i in g]}
    json.dump(data, open(f"/tmp/vs/agent_inputs/agent_{agent}.json", "w"), ensure_ascii=False, indent=1)
    summary[agent] = (len(ids), len(g))
leftover = gen[14 * 35:]
print(summary, "leftover GEN:", len(leftover))
all_assigned = set()
for agent in summary:
    d = json.load(open(f"/tmp/vs/agent_inputs/agent_{agent}.json"))
    all_assigned |= {w["id"] for w in d["theme_words"]} | {w["id"] for w in d["general_words"]}
print("assigned B1:", len(all_assigned), "of", len(b1))
