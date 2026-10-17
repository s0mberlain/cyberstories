#!/usr/bin/env python3
"""Baut aus dem Ordner geschichten/ die Webapp und die Druck-PDFs (Deutsch und Englisch).

Aufruf aus dem Projektordner:
    python3 werkzeug/bauen.py            prüfen und alles bauen
    python3 werkzeug/bauen.py --pruefen  nur prüfen, nichts bauen
    python3 werkzeug/bauen.py --ohne-pdf nur die Webapp bauen

Ergebnisse landen in ausgabe/.
"""
import base64
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

WERKZEUG = Path(__file__).resolve().parent
PROJEKT = WERKZEUG.parent
GESCHICHTEN = PROJEKT / "geschichten"
BILDER = GESCHICHTEN / "bilder"
AUSGABE = PROJEKT / "ausgabe"
PLATZHALTER = "_platzhalter.svg"

STUFEN = ("leicht", "mittel", "schwer")
# Überschriften in den Geschichten-Dateien und das Feld, das sie füllen.
FELDER = {
    "titel": "titel", "title": "titel",
    "thema": "thema", "topic": "thema",
    "rätsel": "raetsel", "raetsel": "raetsel", "riddle": "raetsel",
    "tipp 1": "tipp1", "hint 1": "tipp1",
    "tipp 2": "tipp2", "hint 2": "tipp2",
    "lösung": "loesung", "loesung": "loesung", "solution": "loesung",
    "merksatz": "merksatz", "key takeaway": "merksatz",
}
PFLICHT = ("titel", "raetsel", "tipp1", "tipp2", "loesung", "merksatz")
SPRACHEN = {"deutsch": "de", "german": "de", "english": "en", "englisch": "en"}


class Fehler(Exception):
    pass


def lies_geschichte(pfad):
    text = pfad.read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        raise Fehler("Der Kopfbereich zwischen den beiden --- Zeilen fehlt.")
    kopf = {}
    for zeile in m.group(1).splitlines():
        zeile = zeile.split("#", 1)[0].strip()
        if zeile:
            if ":" not in zeile:
                raise Fehler(f"Zeile im Kopfbereich ohne Doppelpunkt: „{zeile}“")
            k, v = zeile.split(":", 1)
            kopf[k.strip().lower()] = v.strip()

    try:
        nr = int(kopf.get("nummer", ""))
    except ValueError:
        raise Fehler("„nummer“ fehlt oder ist keine Zahl.")
    stufe = kopf.get("schwierigkeit", "").lower()
    if stufe not in STUFEN:
        raise Fehler(f"„schwierigkeit“ muss leicht, mittel oder schwer sein, nicht „{stufe}“.")
    abteilungen = [a.strip().lower() for a in kopf.get("abteilungen", "").split(",") if a.strip()]

    texte = {}
    for block in re.split(r"(?m)^# ", "\n" + m.group(2))[1:]:
        name, _, rest = block.partition("\n")
        sprache = SPRACHEN.get(name.strip().lower())
        if not sprache:
            raise Fehler(f"Unbekannter Sprachabschnitt „# {name.strip()}“. Erlaubt: # Deutsch, # English.")
        felder = {}
        for teil in re.split(r"(?m)^## ", "\n" + rest)[1:]:
            ueberschrift, _, inhalt = teil.partition("\n")
            feld = FELDER.get(ueberschrift.strip().lower())
            if not feld:
                raise Fehler(f"Unbekannte Überschrift „## {ueberschrift.strip()}“ im Abschnitt {name.strip()}.")
            felder[feld] = inhalt.strip()
        if not any(felder.get(f) for f in PFLICHT):
            continue  # leerer Abschnitt aus der Vorlage zählt als nicht übersetzt
        fehlt = [f for f in PFLICHT if not felder.get(f)]
        if fehlt:
            raise Fehler(f"Im Abschnitt {name.strip()} fehlen: {', '.join(fehlt)}.")
        texte[sprache] = {
            "titel": felder["titel"], "thema": felder.get("thema", ""), "raetsel": felder["raetsel"],
            "tipps": [felder["tipp1"], felder["tipp2"]], "loesung": felder["loesung"], "merksatz": felder["merksatz"],
        }
    if not texte:
        raise Fehler("Weder ein deutscher noch ein englischer Text ist ausgefüllt.")

    bild_name = kopf.get("bild", "") or PLATZHALTER
    bild = BILDER / bild_name
    warnung = None
    if not bild.exists():
        warnung = f"Bild „{bild_name}“ nicht gefunden, nehme Platzhalter."
        bild = BILDER / PLATZHALTER
    svg = bild.read_text(encoding="utf-8")
    inhalt = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S)
    if not inhalt:
        raise Fehler(f"„{bild.name}“ ist keine gültige SVG-Datei.")
    # Die Stile kommen aus App bzw. Druckvorlage, daher den <style>-Block der Einzeldatei entfernen.
    bild_svg = re.sub(r"<style.*?</style>", "", inhalt.group(1), flags=re.S).strip()

    return {"nr": nr, "stufe": stufe, "abteilungen": abteilungen, "bild": bild_svg,
            "de": texte.get("de"), "en": texte.get("en"), "_datei": pfad.name, "_warnung": warnung}


def lies_alle():
    karten, fehler = [], []
    for pfad in sorted(GESCHICHTEN.glob("*.md")):
        if pfad.name.startswith("_"):
            continue
        try:
            karten.append(lies_geschichte(pfad))
        except Fehler as e:
            fehler.append(f"{pfad.name}: {e}")
    nummern = {}
    for k in karten:
        nummern.setdefault(k["nr"], []).append(k["_datei"])
    for nr, dateien in nummern.items():
        if len(dateien) > 1:
            fehler.append(f"Nummer {nr} ist mehrfach vergeben: {', '.join(dateien)}")
    karten.sort(key=lambda k: k["nr"])
    return karten, fehler


# ---------- Schriften ----------

SCHRIFTEN = WERKZEUG / "schriften"


def schriften_css():
    """Inter und JetBrains Mono als eingebettete @font-face-Regeln, damit keine externe Verbindung nötig ist."""
    regeln = []
    for datei in sorted(SCHRIFTEN.glob("*.woff2")):
        m = re.match(r"(inter|jetbrains-mono)-latin-(\d+)-normal\.woff2", datei.name)
        if not m:
            continue
        familie = "Inter" if m.group(1) == "inter" else "JetBrains Mono"
        daten = base64.b64encode(datei.read_bytes()).decode()
        regeln.append(f'@font-face{{font-family:"{familie}";font-style:normal;font-weight:{m.group(2)};'
                      f'font-display:swap;src:url(data:font/woff2;base64,{daten}) format("woff2")}}')
    return "\n".join(regeln) + "\n"


# ---------- Webapp ----------

def baue_app(karten):
    vorlage = (WERKZEUG / "app_vorlage.html").read_text(encoding="utf-8")
    daten = [{k: v for k, v in c.items() if not k.startswith("_")} for c in karten]
    js = json.dumps(daten, ensure_ascii=False).replace("</", "<\\/")
    seite = vorlage.replace("/*DATA*/[]", js, 1).replace("/*SCHRIFTEN*/", schriften_css(), 1)
    # Variante für den claude.ai-Link (ohne eigenes Grundgerüst)
    (WERKZEUG / ".artefakt.html").write_text(seite, encoding="utf-8")
    kopf, rest = seite.split("</style>", 1)
    einzel = ('<!doctype html>\n<html lang="de">\n<head>\n<meta charset="utf-8">\n'
              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
              + kopf + "</style>\n</head>\n<body>\n" + rest + "\n</body>\n</html>\n")
    ziel = AUSGABE / "Cyberstories_Spiel.html"
    ziel.write_text(einzel, encoding="utf-8")
    return ziel


# ---------- Druck ----------

DRUCK_TEXTE = {
    "de": dict(raetsel="RÄTSEL", frage="Fragen nur mit Ja oder Nein", loesung="LÖSUNG", tipps="Tipps",
               loesung_lbl="Lösung", merksatz="Merksatz", nur_sl="NUR FÜR DIE SPIELLEITUNG",
               stufen={"leicht": "leicht", "mittel": "mittel", "schwer": "schwer"}),
    "en": dict(raetsel="RIDDLE", frage="Yes-or-no questions only", loesung="SOLUTION", tipps="Hints",
               loesung_lbl="Solution", merksatz="Key takeaway", nur_sl="FOR THE GAME MASTER ONLY",
               stufen={"leicht": "easy", "mittel": "medium", "schwer": "hard"}),
}
X0, Y0, B, H = 10, 10.5, 95, 138
VORNE = [(0, 0), (1, 0), (0, 1), (1, 1)]
HINTEN = [(1, 0), (0, 0), (1, 1), (0, 1)]  # gespiegelt für Duplex über die lange Kante


def md(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return "".join(f"<p>{p.strip()}</p>" for p in s.split("\n\n"))


def vorderseite(c, t, d):
    return f'''<div class="card front" data-nr="{c["nr"]}">
  <div class="bar"><span class="brand">CYBER<span class="red">STORIES</span></span><span class="no">#{c["nr"]:02d}</span></div>
  <div class="art"><div class="grid"></div><svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">{c["bild"]}</svg></div>
  <h1>{html.escape(t["titel"])}</h1>
  <div class="rule"></div>
  <div class="txt fit">{md(t["raetsel"])}</div>
  <div class="foot"><span>{d["raetsel"]}</span><span>{d["frage"]}</span></div>
</div>'''


def rueckseite(c, t, d):
    n = STUFEN.index(c["stufe"]) + 1
    sterne = f'<span class="stars">{"■" * n}<span class="off">{"■" * (3 - n)}</span></span> <span class="lvl">{d["stufen"][c["stufe"]]}</span>'
    tipps = "".join(f"<li>{html.escape(x)}</li>" for x in t["tipps"])
    return f'''<div class="card back" data-nr="{c["nr"]}">
  <div class="bar"><span class="brand">{d["loesung"]}</span><span class="no">#{c["nr"]:02d}</span></div>
  <div class="fit">
    <div class="head"><h2>{html.escape(t["titel"])}</h2>{sterne}</div>
    <div class="lbl">{d["tipps"]}</div><ol class="tips">{tipps}</ol>
    <div class="lbl">{d["loesung_lbl"]}</div><div class="txt">{md(t["loesung"])}</div>
    <div class="merk"><div class="lbl red">{d["merksatz"]}</div>{md(t["merksatz"])}</div>
  </div>
  <div class="foot"><span>{d["nur_sl"]}</span><span>CYBERSTORIES</span></div>
</div>'''


def schnittmarken():
    out, l = [], 6
    for x in (X0, X0 + B, X0 + 2 * B):
        out.append(f'<div class="crop" style="left:{x-0.1}mm;top:{Y0-l-1}mm;width:.2mm;height:{l}mm"></div>')
        out.append(f'<div class="crop" style="left:{x-0.1}mm;top:{Y0+2*H+1}mm;width:.2mm;height:{l}mm"></div>')
    for y in (Y0, Y0 + H, Y0 + 2 * H):
        out.append(f'<div class="crop" style="top:{y-0.1}mm;left:{X0-l-1}mm;height:.2mm;width:{l}mm"></div>')
        out.append(f'<div class="crop" style="top:{y-0.1}mm;left:{X0+2*B+1}mm;height:.2mm;width:{l}mm"></div>')
    return "".join(out)


def blatt(gruppe, fn, pos, lang):
    d = DRUCK_TEXTE[lang]
    slots = "".join(f'<div class="slot" style="left:{X0+pos[i][0]*B}mm;top:{Y0+pos[i][1]*H}mm">{fn(c, c[lang], d)}</div>'
                    for i, c in enumerate(gruppe))
    return f'<div class="sheet">{schnittmarken()}{slots}</div>'


FIT_JS = """
document.fonts.ready.then(() => {
  for (const el of document.querySelectorAll('.fit')) {
    let fs = parseFloat(getComputedStyle(el).fontSize);
    while (el.scrollHeight > el.clientHeight + 1 && fs > 6) { fs -= 0.2; el.style.fontSize = fs + 'px'; }
    if (el.scrollHeight > el.clientHeight + 1) el.dataset.overflow = '1';
  }
  document.body.dataset.ready = '1';
});
"""


def baue_druck_html(karten, lang):
    karten = [c for c in karten if c[lang]]
    seiten = []
    for i in range(0, len(karten), 4):
        g = karten[i:i + 4]
        seiten.append(blatt(g, vorderseite, VORNE, lang))
        seiten.append(blatt(g, rueckseite, HINTEN, lang))
    css = (WERKZEUG / "druck_stil.css").read_text(encoding="utf-8")
    ziel = WERKZEUG / f".druck_{lang}.html"
    ziel.write_text(
        f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>Cyberstories</title>'
        f'<style>{schriften_css()}{css}</style></head><body>{"".join(seiten)}<script>{FIT_JS}</script></body></html>',
        encoding="utf-8")
    return ziel, len(karten)


def baue_pdf(quelle, ziel):
    node = shutil.which("node")
    if not node:
        print("  Node.js nicht gefunden, PDF übersprungen.")
        return False
    env = dict(os.environ)
    npm = shutil.which("npm")
    if npm:  # global installiertes Playwright ebenfalls finden
        wurzel = subprocess.run([npm, "root", "-g"], text=True, capture_output=True).stdout.strip()
        env["NODE_PATH"] = os.pathsep.join(x for x in (env.get("NODE_PATH"), wurzel) if x)
    r = subprocess.run([node, str(WERKZEUG / "pdf.js"), str(quelle), str(ziel)], text=True, capture_output=True, env=env)
    if r.stdout.strip():
        print(r.stdout.rstrip())
    if r.returncode != 0:
        print("  PDF konnte nicht erzeugt werden (braucht Node.js mit Playwright):", r.stderr.strip().splitlines()[-1:] or "")
        return False
    return True


def main():
    nur_pruefen = "--pruefen" in sys.argv
    ohne_pdf = "--ohne-pdf" in sys.argv
    karten, fehler = lies_alle()
    print(f"{len(karten)} Geschichten gelesen.")
    for c in karten:
        if c["_warnung"]:
            print(f"  Hinweis {c['_datei']}: {c['_warnung']}")
        if not c["en"]:
            print(f"  Hinweis {c['_datei']}: noch keine englische Fassung.")
        if not c["de"]:
            print(f"  Hinweis {c['_datei']}: noch keine deutsche Fassung.")
    if fehler:
        print("\nFEHLER, bitte korrigieren:")
        for f in fehler:
            print("  " + f)
        sys.exit(1)
    if nur_pruefen:
        print("Alles in Ordnung.")
        return
    AUSGABE.mkdir(exist_ok=True)
    print("Webapp:", baue_app(karten).relative_to(PROJEKT))
    if ohne_pdf:
        return
    for lang, name in (("de", "Cyberstories_Karten_DE.pdf"), ("en", "Cyberstories_Cards_EN.pdf")):
        quelle, n = baue_druck_html(karten, lang)
        ziel = AUSGABE / name
        if baue_pdf(quelle, ziel):
            print(f"Druck {lang.upper()}: {ziel.relative_to(PROJEKT)} ({n} Karten)")


if __name__ == "__main__":
    main()
