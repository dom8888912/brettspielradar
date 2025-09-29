# Preisradar – Improved (Stand: 20250809-082352)

**Was neu ist**


- Längere Inhalte je Spiel: optionale Sektionen (How-to in 60s, Gebraucht-Checkliste, Editionen, Erweiterungen, Pros/Cons).
- FAQ: erste 2 Punkte standardmäßig geöffnet.
- Automatischer Preiskommentar (Delta vs. Ø60 Tage).
- „Top-Deal“-Badge, wenn Minimumpreis deutlich unter Ø60 oder unter Schwelle liegt.
- Build-Script rechnet `delta60` und `min_price`.
- Fetcher (Stub + eBay Enhanced) unverändert kompatibel.

**Test (Stub)**
```bat
py -m venv .venv
.\.venv\Scripts\activate
py -m pip install -r requirements.txt
py scripts\fetch_offers_stub.py
py scripts\build.py
py -m http.server -d dist 8000
```

**Mit eBay**
1) `.env` anlegen mit `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EPN_CAMPAIGN_ID` (und optional `EPN_REFERENCE_ID`).
2) Dann:
```bat
py scripts\fetch_offers_ebay_enhanced.py
py scripts\build.py
```

In `config/filters.yaml` kannst du den Marktplatz und die Währung anpassen
(`marketplace_id`, `price_currency`). Standard ist `EBAY_DE` mit `EUR` und
`item_location_countries: [DE]` für Angebote aus Deutschland. Über
`default_ebay_category_id` legst du fest, welche eBay-Kategorie für die Suche
verwendet wird (z. B. `180349` für Brettspiele). Pro Spiel lässt
sich in `content/games/<slug>.yaml` über `search_terms` festlegen, welche
Schlüsselwörter an die eBay‑API übergeben werden. Ein optionales
`price_filter: {min: 20}` setzt einen Mindestpreis.

**Amazon Affiliate**

Setze optional die Umgebungsvariable `AMAZON_PARTNER_ID` (Standard `28310edf-21`), um einen "Preis bei Amazon prüfen"-Button mit Affiliate-Link auf jeder Spieleseite auszugeben.

**YAML Felder (neu & optional)**
- `how_to_play_60s` (Text), `used_checklist` (Liste), `editions` (note/recommended/avoid), `expansions` (Liste mit name/verdict), `pros`/`cons` (Listen).

## Manuelles Prüfen der eBay-Angebote

Um irrelevante Treffer aus den eBay-Suchergebnissen zu filtern, werden nur
Angebote berücksichtigt, die du manuell als „relevant“ markierst. Das klappt so:

1. **Angebote labeln**

   - Lege die Umgebungsvariablen `TRAINING_USER` und `TRAINING_PASS` an
     (z. B. als GitHub Secret).
   - Starte den kleinen Server:
     ```bash
     python scripts/label_server.py
     ```
   - Rufe im Browser `http://localhost:8000/training` auf und wähle ein Spiel.
     Auf der jeweiligen Spielseite kannst du die angezeigten Angebote als
     „relevant“ oder „nicht relevant“ markieren. Die Seite zeigt bis zu 100
     unlabeled Treffer inklusive Bild und Kurzbeschreibung; bereits
     bewertete Angebote werden ausgeblendet.

   Die Bewertungen werden in `data/labels/<slug>.json` gespeichert. Fehler beim
   Einlesen der Angebote landen samt Stacktrace in `data/logs/label_server.log`.
   Unter `http://localhost:8000/__version__` gibt der Server den aktuell
   ausgeführten Git-Commit zurück – hilfreich zum Überprüfen eines
   Neustarts oder Deployments.

2. **Build aktualisieren**

   Beim nächsten Durchlauf von `python scripts/build.py` fließen ausschließlich
   jene Angebote in Preisindikator und Anzeige ein, die du manuell als
   relevant markiert hast. Unbewertete oder abgelehnte Treffer werden ignoriert.
