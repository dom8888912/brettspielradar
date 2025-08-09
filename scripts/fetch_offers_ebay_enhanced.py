# scripts/fetch_offers_ebay_enhanced.py
# --------------------------------------
# Holt Angebote über die eBay Browse API, wendet spiel-spezifische Filter an
# und speichert max. 8 passende Angebote je Spiel als JSON.
# - Nutzt EPN-Tracking: itemAffiliateWebUrl (wenn Campaign/Reference gesetzt)
# - referenceId = <EPN_REFERENCE_ID>-<slug> für sauberes Reporting pro Spiel
# - Schreibt Preis-Historie (min/avg/n) in data/history/<slug>.jsonl
#
# Voraussetzung:
#   EBAY_CLIENT_ID, EBAY_CLIENT_SECRET (Production)
#   EPN_CAMPAIGN_ID (deine Campaign-ID)
#   EPN_REFERENCE_ID (z. B. "preisradar")
#
# Wenn ENV fehlt oder Approval noch aussteht: Script bricht sauber ab, ohne Daten zu überschreiben.

import os
import json
import time
import pathlib
import requests
import yaml
from dotenv import load_dotenv
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "games"
OFFERS_DIR = ROOT / "data" / "offers"
HIST_DIR = ROOT / "data" / "history"

# Konfiguration
MARKETPLACE = "EBAY_DE"
COUNTRY = "DE"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"

# ENV laden
load_dotenv()
EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
EPN_CAMPAIGN_ID = os.getenv("EPN_CAMPAIGN_ID")  # optional, aber empfohlen
EPN_REFERENCE_ID = os.getenv("EPN_REFERENCE_ID", "preisradar")

SESSION = requests.Session()
SESSION.timeout = 25

def get_token():
    if not (EBAY_CLIENT_ID and EBAY_CLIENT_SECRET):
        raise RuntimeError("Fehlende EBAY_CLIENT_ID/EBAY_CLIENT_SECRET in .env (Production-Keys).")
    auth = requests.auth.HTTPBasicAuth(EBAY_CLIENT_ID, EBAY_CLIENT_SECRET)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials", "scope": SCOPE}
    r = SESSION.post(TOKEN_URL, headers=headers, data=data, auth=auth)
    r.raise_for_status()
    return r.json()["access_token"]

def build_headers(token: str, reference: str):
    # Enduser Context inkl. Affiliate-Daten, falls Campaign-ID bekannt ist
    ctx_parts = [f"contextualLocation=country={COUNTRY}"]
    if EPN_CAMPAIGN_ID:
        ctx_parts.append(f"affiliateCampaignId={EPN_CAMPAIGN_ID}")
        # Referenz pro Spiel (z. B. preisradar-ark-nova), max. ~64 Zeichen ist praktisch
        ref = f"{EPN_REFERENCE_ID}-{reference}".replace(" ", "-")[:64]
        ctx_parts.append(f"affiliateReferenceId={ref}")
    enduserctx = ",".join(ctx_parts)
    return {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE,
        "X-EBAY-C-ENDUSERCTX": enduserctx,
    }

def ebay_search(token: str, query: str, headers: dict, limit: int = 25):
    params = {
        "q": query,
        "limit": str(limit),
        "sort": "price",
        "filter": "priceCurrency:EUR",  # nur EUR
    }
    r = SESSION.get(BROWSE_URL, headers=headers, params=params)
    r.raise_for_status()
    return r.json().get("itemSummaries", []) or []

def normalize_offers(items):
    out = []
    for it in items:
        price_obj = it.get("price") or {}
        currency = price_obj.get("currency")
        value = price_obj.get("value")
        try:
            price = float(value)
        except Exception:
            continue
        if currency and currency.upper() != "EUR":
            continue
        url = it.get("itemAffiliateWebUrl") or it.get("itemWebUrl")
        if not url:
            continue
        title = (it.get("title") or "Angebot").strip()
        condition = (it.get("condition") or "Unknown").strip()
        offer = {
            "title": title[:140],
            "price_eur": round(price, 2),
            "condition": condition,
            "url": url
        }
        out.append(offer)
    return out

def apply_filters(game: dict, offers: list):
    inc = [k.lower() for k in (game.get("include_keywords") or [])]
    exc = [k.lower() for k in (game.get("exclude_keywords") or [])]
    cond_whitelist = [c.lower() for c in (game.get("condition_whitelist") or [])]
    pf = game.get("price_filter") or {}

    def ok(o):
        t = o["title"].lower()
        if exc and any(k in t for k in exc):
            return False
        if inc and not any(k in t for k in inc):
            return False
        if pf.get("min") and o["price_eur"] < float(pf["min"]):
            return False
        if pf.get("max") and o["price_eur"] > float(pf["max"]):
            return False
        if cond_whitelist and o.get("condition", "").lower() not in cond_whitelist:
            return False
        return True

    filtered = [o for o in offers if ok(o)]
    # Dedupe: (title_lower, price) Kombination
    seen = set()
    uniq = []
    for o in filtered:
        key = (o["title"].lower(), o["price_eur"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(o)
    # nach Preis sortieren (günstig zuerst)
    uniq.sort(key=lambda x: x["price_eur"])
    return uniq

def append_history(slug: str, offers: list):
    if not offers:
        return
    HIST_DIR.mkdir(parents=True, exist_ok=True)
    prices = [o["price_eur"] for o in offers]
    row = {
        "date": date.today().isoformat(),
        "min": min(prices),
        "avg": round(sum(prices) / len(prices), 2),
        "n": len(prices),
    }
    path = HIST_DIR / f"{slug}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def merged_offers_for_game(token: str, game: dict):
    slug = game["slug"]
    headers = build_headers(token, slug)
    queries = game.get("search_queries") or [f"{game['title']} Brettspiel deutsch"]
    merged = []
    for q in queries:
        try:
            items = ebay_search(token, q, headers=headers, limit=25)
            offers = normalize_offers(items)
            merged.extend(offers)
            time.sleep(0.25)  # etwas Pause zwischen Requests
        except requests.HTTPError as e:
            print(f"[WARN] HTTP {e.response.status_code} bei Query '{q}' für {slug}")
        except Exception as e:
            print(f"[WARN] Fehler bei Query '{q}' für {slug}: {e}")
    return apply_filters(game, merged)

def main():
    OFFERS_DIR.mkdir(parents=True, exist_ok=True)

    # Wenn keine Dev-Creds konfiguriert sind, freundlich aussteigen
    if not (EBAY_CLIENT_ID and EBAY_CLIENT_SECRET):
        print("ℹ Keine EBAY_CLIENT_* in .env gefunden – überspringe eBay-Fetch. (Später erneut ausführen.)")
        return

    try:
        token = get_token()
    except Exception as e:
        print(f"✖ Konnte kein Token holen: {e}")
        return

    # Warnung, falls keine Campaign-ID gesetzt (dann evtl. keine Affiliate-URLs)
    if not EPN_CAMPAIGN_ID:
        print("⚠ EPN_CAMPAIGN_ID fehlt – Affiliate-Tracking-URLs (itemAffiliateWebUrl) sind u.U. nicht verfügbar.")

    yml_paths = list(CONTENT_DIR.glob("*.yaml"))
    if not yml_paths:
        print("ℹ Keine Spiele-YAMLs gefunden.")
        return

    for yml in yml_paths:
        try:
            game = yaml.safe_load(yml.read_text(encoding="utf-8"))
            slug = game["slug"]
            offers = merged_offers_for_game(token, game)
            # speichern (max. 8 Angebote)
            with open(OFFERS_DIR / f"{slug}.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(offers[:8], ensure_ascii=False, indent=2))
            append_history(slug, offers)
            print(f"✔ {slug}: {len(offers[:8])} Angebote gespeichert.")
        except Exception as e:
            print(f"✖ Fehler bei {yml.name}: {e}")

if __name__ == "__main__":
    main()
