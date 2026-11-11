import io, sys
import pymupdf
from PIL import Image

OUT = sys.argv[1]
pages = [
    ("01", "Teil 1 · Teilnehmer/in A und B", "Einander kennenlernen"),
    ("02", "Modelltest 2 · Teil 2 · Teilnehmer/in A", "Ausgehen und Leute treffen"),
    ("03", "Modelltest 2 · Teil 2 · Teilnehmer/in B", "Ausgehen und Leute treffen"),
    ("04", "Modelltest 2 · Teil 3 · Teilnehmer/in A und B", "Gemeinsam etwas planen: Gesundheit"),
    ("05", "Modelltest 3 · Teil 2 · Teilnehmer/in A", "Verhalten in der Öffentlichkeit"),
    ("06", "Modelltest 3 · Teil 2 · Teilnehmer/in B", "Verhalten in der Öffentlichkeit"),
    ("07", "Modelltest 3 · Teil 3 · Teilnehmer/in A und B", "Gemeinsam etwas planen: Veranstaltung"),
    ("08", "Modelltest 4 · Teil 2 · Teilnehmer/in A", "Filme sehen"),
    ("09", "Modelltest 4 · Teil 2 · Teilnehmer/in B", "Filme sehen"),
    ("10", "Modelltest 4 · Teil 3 · Teilnehmer/in A und B", "Gemeinsam etwas planen: Abschiedsfeier"),
]
rows = [
    ("2", "2", "Teil 1 · A und B", "Einander kennenlernen"),
    ("3", "2", "Teil 2 · A", "Ausgehen und Leute treffen (Galina Konrad)"),
    ("4", "2", "Teil 2 · B", "Ausgehen und Leute treffen (Arno Betancourt)"),
    ("5", "2", "Teil 3 · A und B", "Gemeinsam etwas planen: mehr für die Gesundheit tun"),
    ("6", "3", "Teil 2 · A", "Verhalten in der Öffentlichkeit (Mariam Kohl)"),
    ("7", "3", "Teil 2 · B", "Verhalten in der Öffentlichkeit (Florian Frei)"),
    ("8", "3", "Teil 3 · A und B", "Gemeinsam etwas planen: eine Veranstaltung besuchen"),
    ("9", "4", "Teil 2 · A", "Filme sehen (Djamal Demouni)"),
    ("10", "4", "Teil 2 · B", "Filme sehen (Tabea Allmeyer)"),
    ("11", "4", "Teil 3 · A und B", "Gemeinsam etwas planen: Abschiedsfeier für eine Nachbarin"),
]
total = len(pages)
W, H = pymupdf.paper_size("a4")
css = """
* { font-family: sans-serif; color: #222; }
h1 { font-size: 24px; margin: 0 0 4px 0; }
h2 { font-size: 15px; font-weight: normal; color: #555; margin: 0 0 22px 0; }
table { border-collapse: collapse; width: 100%; font-size: 11.5px; }
th { text-align: left; background: #e9eef3; padding: 6px 8px; border-bottom: 1px solid #b8c4d0; }
td { padding: 6px 8px; border-bottom: 1px solid #dde3e9; }
p.note { font-size: 11.5px; color: #333; margin-top: 18px; line-height: 1.45; }
.lab { font-size: 10.5px; font-weight: bold; color: #333; }
.top { font-size: 10.5px; color: #555; text-align: right; }
.pn { font-size: 8.5px; color: #777; text-align: right; }
"""
doc = pymupdf.open()
for n, (pid, label, topic) in enumerate(pages, start=1):
    im = Image.open(f"/tmp/sprechen-work/out/{pid}_full.png").convert("RGB")
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=84, optimize=True)
    page = doc.new_page(width=W, height=H)
    box = pymupdf.Rect(28, 44, W - 28, H - 30)
    iw, ih = im.size
    s = min(box.width / iw, box.height / ih)
    dw, dh = iw * s, ih * s
    r = pymupdf.Rect(box.x0 + (box.width - dw) / 2, box.y0, box.x0 + (box.width - dw) / 2 + dw, box.y0 + dh)
    page.insert_image(r, stream=buf.getvalue())
    page.insert_htmlbox(pymupdf.Rect(28, 18, W * 0.62, 40), f"<div class='lab'>{label}</div>", css=css)
    page.insert_htmlbox(pymupdf.Rect(W * 0.55, 18, W - 28, 40), f"<div class='top'>{topic}</div>", css=css)
    page.insert_htmlbox(pymupdf.Rect(28, H - 24, W - 28, H - 8), f"<div class='pn'>Seite {n} von {total}</div>", css=css)
doc.set_metadata({"title": "Mündliche Prüfung telc Deutsch B1: Übungsmaterial", "author": "Cheyan Setayesh"})
doc.save(OUT, garbage=4, deflate=True)
print("saved", OUT, doc.page_count, "pages")
