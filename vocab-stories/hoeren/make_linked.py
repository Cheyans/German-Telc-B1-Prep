import json, re, html, urllib.parse
DW = "https://learngerman.dw.com"
def q(path): return DW + urllib.parse.quote(path, safe="/-")
T1 = "Sie hören fünf kurze Texte, jeden nur einmal. Sind die Aussagen 41 bis 45 richtig oder falsch?"
T2 = "Sie hören ein Gespräch, zweimal. Sind die Aussagen 46 bis 55 richtig oder falsch?"
T3 = "Sie hören fünf kurze Texte, jeden zweimal. Sind die Aussagen 56 bis 60 richtig oder falsch?"
G = ["Sie hören fünf kurze Texte, jeden zweimal. Zu jedem Text lösen Sie zwei Aufgaben: richtig oder falsch, dann a, b oder c (Aufgaben 1 bis 10).",
     "Sie hören einen Text, nur einmal. Wählen Sie bei den Aufgaben 11 bis 15 a, b oder c.",
     "Sie hören ein Gespräch, nur einmal. Sind die Aussagen 16 bis 22 richtig oder falsch?",
     "Sie hören eine Diskussion, zweimal. Wer sagt was? Ordnen Sie die Aussagen 23 bis 30 zu."]
out = []
def add(**k): out.append(k)
dwv = [("Teil 1", "/de/teil-1-die-aufgabe-lesen/l-73044718/e-73045091", "sechs kurze Übungen bis „Teil 1: Teste dich!“"),
       ("Teil 2", "/de/teil-2-die-aufgaben-lesen-1/l-73044718/e-73045833", "fünf kurze Übungen bis „Teil 2: Teste dich!“"),
       ("Teil 3", "/de/teil-3-die-aufgaben-lesen/l-73044718/e-73046407", "fünf kurze Übungen bis „Teil 3: Teste dich! (2)“")]
for i, (p, path, what) in enumerate(dwv, 1):
    add(id=f"DWV{i}", src="dw", set="DW: Deine Deutschprüfung B1 · Vorbereitung", part="Hören " + p, what="Tipps und Übungen", do="Mach die " + what + ". DW zeigt dir die Lösungen.", url=q(path), go="Übung bei DW öffnen", min=15)
def telc(prefix, setname, page, zipurl, pdf, mp3, key, tr, starts, end):
    bounds = starts + [end]
    for i, task in enumerate([T1, T2, T3]):
        add(id=f"{prefix}{i+1}", src="telc", set=setname, part=f"Hörverstehen Teil {i+1}", what=["5 Aussagen", "10 Aussagen", "5 Aussagen"][i],
            task=task, n=[5, 10, 5][i], items=["41 bis 45", "46 bis 55", "56 bis 60"][i], plays=[1, 2, 2][i], page=page, get=zipurl, getlab="ZIP herunterladen",
            pdf={"name": pdf, "q": 16 + i, "key": key, "tr": tr}, audio=dict({"file": mp3, "from": bounds[i], "to": bounds[i + 1]}, **({"note": "Die Datei heißt „_4“, gehört aber zu Übungstest 1."} if mp3.endswith("_4.mp3") else {})), min=[8, 12, 12][i])
telc("TB", "telc Deutsch B1 · Übungstest 1", "https://www.telc.net/sprachpruefungen/deutsch/zertifikat-deutsch-telc-deutsch-b1/", "https://www.telc.net/fileadmin/user_upload/mock_exams/Deutsch/telc_deutsch_b1.zip", "telc_deutsch_b1_zd_uebungstest_1.pdf", "telc_deutsch_b1_zd_uebungstest_4.mp3", 43, 44, ["0:00", "5:40", "15:10"], "24:59")
telc("TS", "telc Deutsch B1 Schule · Übungstest 1", "https://www.telc.net/sprachpruefungen/zertifikatspruefung/deutsch/telc-deutsch-b1-schule/", "https://www.telc.net/fileadmin/user_upload/mock_exams/Deutsch/telc_deutsch_b1_schule.zip", "telc_deutsch_b1-schule_uebungstest_1.pdf", "telc_deutsch_b1-schule_uebungstest_1.mp3", 42, 43, ["0:00", "6:20", "18:40"], "28:16")
telc("TP", "telc Deutsch B1+ Beruf · Übungstest 1", "https://www.telc.net/sprachpruefungen/zertifikatspruefung/deutsch/telc-deutsch-b1-beruf/", "https://www.telc.net/fileadmin/user_upload/mock_exams/Deutsch/telc_deutsch_b1_beruf.zip", "telc_deutsch_b1plus_beruf_uebungstest_1.pdf", "telc_deutsch_b1plus_beruf_modelltest_1.mp3", 42, 43, ["0:00", "6:45", "18:10"], "27:39")
def osd(prefix, setname, zipurl, pdf, mp3s, lens):
    for i, task in enumerate([T1, T2, T3]):
        add(id=f"{prefix}{i+1}", src="osd", set=setname, part=f"Hören Aufgabe {i+1}", what=["5 Aussagen", "10 Aussagen", "5 Aussagen"][i],
            task=task, n=[5, 10, 5][i], items=["41 bis 45", "46 bis 55", "56 bis 60"][i], plays=[1, 2, 2][i], page="https://osd.at/downloads/", get=zipurl, getlab="ZIP herunterladen",
            pdf={"name": pdf, "q": [11, 11, 12][i], "key": 20}, audio={"file": mp3s[i], "from": "0:00", "to": lens[i]}, min=[8, 12, 12][i])
osd("OE", "ÖSD Zertifikat Deutsch Österreich B1 · Modellsatz", "https://osd.at/wp-content/uploads/2026/08/ZDOe-B1_Modellsatz.zip", "ZDÖ B1 Modellsatz HP.pdf", ["B1_ZDO_MS_A1.mp3", "B1_ZDO_MS_A2.mp3", "B1_ZDO_MS_A3_290817.mp3"], ["5:07", "8:53", "8:27"])
osd("OJ", "ÖSD Zertifikat Deutsch Österreich B1 · Modellsatz Jugendliche", "https://osd.at/wp-content/uploads/2026/08/ZDOe-B1_Jugendliche_Modellsatz.zip", "ZDÖ B1 J Modellsatz HP.pdf", ["B1_ZDO_J_MS_A1_180917.mp3", "B1_ZDO_J_MS_A2_180917.mp3", "B1_ZDO_J_MS_A3_180917.mp3"], ["5:02", "10:13", "8:35"])
dwt = [("Teil 1: persönliche Berichte", "/de/teil-1-persönliche-berichte/l-73033929/e-73034091", "Mach die Übung. DW zeigt dir danach die Lösungen."),
       ("Teil 2: ein Gespräch", "/de/teil-2-ein-gespräch/l-73033929/e-73034182", "Mach die Übung. DW zeigt dir danach die Lösungen."),
       ("Teil 3: Informationstexte", "/de/teil-3-informationstexte-1/l-73033929/e-73034302", "Mach beide Übungen, Informationstexte (1) und (2). DW zeigt dir danach die Lösungen.")]
for i, (p, path, do) in enumerate(dwt, 1):
    add(id=f"DWT{i}", src="dw", set="DW: Deine Deutschprüfung B1 · Test", part="Hören " + p, what="wie in der Prüfung", do=do, url=q(path), go="Test bei DW öffnen", min=12)
GO = "https://www.goethe.de/pro/relaunch/prf/materialien/B1/"
gsets = [("G1E", "Goethe-Zertifikat B1 · Prüfungstraining 1 (Erwachsene)", "b1_modellsatz_erwachsene.pdf", "https://goethemp4s.akamaized.net/resources/files/mp468/pruefungstraining_1_hoeren_b1_erwachsene.mp4", ["0:00", "10:40", "15:09", "20:18", "32:10"], [34, 35, 36, 37]),
         ("G2E", "Goethe-Zertifikat B1 · Prüfungstraining 2 (Erwachsene)", "B1_Uebungssatz_Erwachsene.pdf", "https://goethemp4s.akamaized.net/resources/files/mp468/pruefungstraining_2_hoeren_b1_erwachsene.mp4", ["0:00", "11:18", "16:25", "21:10", "33:59"], [35, 36, 37, 38]),
         ("G1J", "Goethe-Zertifikat B1 · Prüfungstraining 1 (Jugendliche)", "b1_modellsatz_jugend.pdf", "https://goethemp4s.akamaized.net/resources/files/mp468/pruefungstraining_1_hoeren_b1_jugendliche.mp4", ["0:00", "10:09", "15:02", "19:37", "31:27"], [34, 35, 36, 37]),
         ("G2J", "Goethe-Zertifikat B1 · Prüfungstraining 2 (Jugendliche)", "B1_Uebungssatz_Jugendliche.pdf", "https://goethemp4s.akamaized.net/resources/files/mp310/pruefungstraining_2_hoeren_b1_jugendliche.mp3", ["0:00", "11:53", "17:04", "22:12", "34:29"], [35, 36, 37, 38])]
for pre, setname, pdf, audio, b, trs in gsets:
    for i in range(4):
        add(id=f"{pre}{i+1}", src="goethe", set=setname, part=f"Hören Teil {i+1}", what=["10 Aufgaben", "5 Aufgaben", "7 Aussagen", "8 Aussagen"][i],
            task=G[i], n=[10, 5, 7, 8][i], items=["1 bis 10", "11 bis 15", "16 bis 22", "23 bis 30"][i], plays=[2, 1, 1, 2][i], page="https://www.goethe.de/de/spr/prf/ueb/pb1.html",
            pdf={"name": pdf, "url": GO + pdf, "q": 18 + i, "key": 33, "tr": trs[i]}, audio={"url": audio, "from": b[i], "to": b[i + 1]}, min=[14, 8, 8, 16][i])
rows = [(r["href"], r["parts"]) for r in json.load(open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "nicos_weg_b1.json"), encoding="utf-8"))]
for k, (href, parts) in enumerate(rows, 1):
    title = parts[0] if parts else "Lektion"
    topic = " · ".join(parts[1:3]) if len(parts) > 1 else ""
    final = "abschlusstest" in href
    add(id=f"NW{k:02d}", src="nicos", set="DW: Nicos Weg B1", part=("Abschlusstest" if final else f"Lektion {k} von {len(rows) - 1}: {title}"), what=topic,
        do=("Mach den Test. Er prüft den ganzen B1-Kurs." if final else "Schau das Video und mach die Übungen dazu. DW zeigt dir die Lösungen."), url=q(href), go="Lektion bei DW öffnen", min=20 if final else 15)
json.dump(out, open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "linked.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out), "tasks |", ", ".join(f"{s}: {sum(1 for x in out if x['src'] == s)}" for s in ["dw", "telc", "osd", "goethe", "nicos"]))
print("nicos sample:", [ (x["part"], x["what"]) for x in out if x["src"] == "nicos"][:2], out[-1]["part"])
