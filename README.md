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

**Amazon Affiliate**

Setze optional die Umgebungsvariable `AMAZON_PARTNER_ID` (Standard `28310edf-21`), um einen "Preis bei Amazon prüfen"-Button mit Affiliate-Link auf jeder Spieleseite auszugeben.

**YAML Felder (neu & optional)**
- `how_to_play_60s` (Text), `used_checklist` (Liste), `editions` (note/recommended/avoid), `expansions` (Liste mit name/verdict), `pros`/`cons` (Listen).
