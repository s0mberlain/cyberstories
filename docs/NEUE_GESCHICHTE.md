# Neue Geschichte anlegen

Jede Karte ist eine eigene Datei im Ordner `geschichten/`. Eine neue Datei erscheint nach dem Bauen automatisch in der Webapp und im Druck-PDF.

## In vier Schritten

1. **Vorlage kopieren:** `geschichten/_vorlage.md` kopieren und umbenennen, zum Beispiel in `041-der-falsche-paketbote.md`. Die Nummer vorne sorgt für die Sortierung im Ordner.
2. **Kopfbereich ausfüllen:** Nummer (fortlaufend, nicht doppelt), Schwierigkeit (`leicht`, `mittel` oder `schwer`), optional Abteilungen und Bild.
3. **Texte schreiben:** Unter `# Deutsch` und `# English` jeweils Titel, Thema, Rätsel, zwei Tipps, Lösung und Merksatz. Fehlt die englische Fassung noch, den Abschnitt einfach leer lassen: Die Karte erscheint dann in der englischen App auf Deutsch mit dem Hinweis „Only available in German“ und fehlt im englischen Druck-PDF.
4. **Bauen:** Im Hauptordner des Projekts `python3 werkzeug/bauen.py` ausführen. Der Befehl prüft zuerst alle Geschichten und nennt Fehler mit Dateiname, zum Beispiel ein fehlendes Feld oder eine doppelte Nummer. Danach entstehen in `ausgabe/`:
   - `Cyberstories_Spiel.html`, die Webapp als einzelne Datei
   - `Cyberstories_Karten_DE.pdf` und `Cyberstories_Cards_EN.pdf`, die Druckbögen

Nur prüfen ohne zu bauen: `python3 werkzeug/bauen.py --pruefen`. Nur die Webapp bauen: `python3 werkzeug/bauen.py --ohne-pdf`.

## Bilder

Bilder liegen als SVG-Dateien in `geschichten/bilder/`, Format 120 × 120 (`viewBox="0 0 120 120"`). Damit sie zum Stil passen, nutzen sie diese Klassen:

| Klasse | Wirkung |
|---|---|
| `k` | schwarze Linie |
| `r` | rote Linie |
| `kf` | schwarz gefüllt |
| `rf` | rot gefüllt |
| `w` | weiß gefüllt (zum Abdecken) |

Am einfachsten eine vorhandene Datei kopieren und anpassen. Ohne eigenes Bild nimmt die Karte das Platzhalter-Bild (Schild mit Fragezeichen).

## Gut zu wissen

- **Hervorhebungen:** `*kursiv*` und `**fett**` funktionieren in allen Texten. Ein Absatz entsteht durch eine Leerzeile.
- **Abteilungen:** Eine neue Abteilung (zum Beispiel `logistik`) erscheint automatisch als Filter in der App.
- **Voraussetzungen:** Python 3 für die Webapp. Für die PDFs zusätzlich Node.js mit Playwright: im Hauptordner `npm install` und danach `npx playwright install chromium`.
- **Einfachste Variante:** Die Geschichte in den Projekt-Chat schreiben, Claude legt die Datei an, übersetzt und baut neu.
