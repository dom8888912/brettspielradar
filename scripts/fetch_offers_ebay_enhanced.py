#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch eBay offers for each game and save to data/offers/<slug>.json

- Application Access Token (client_credentials) with base scope
- Marketplace via header (X-EBAY-C-MARKETPLACE-ID=EBAY_DE)
- Optional EPN affiliate via X-EBAY-C-ENDUSERCTX
- Supports per-game YAML `search_terms` (DE+EN), tries multiple queries
- Excludes accessory items and private sellers, keeps only new-condition listings
- Robust price detection (price / priceRange.min / currentBidPrice), EUR only
"""

import os, json, time
from pathlib import Path
from typing import List, Dict, Any
import requests, yaml

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "games"
DATA_DIR = ROOT / "data" / "offers"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_env_file(path: Path):
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Load local .env if present (does not override already set env)
load_env_file(ROOT / ".env")

CID  = os.getenv("EBAY_CLIENT_ID", "").strip()
CSEC = os.getenv("EBAY_CLIENT_SECRET", "").strip()
EPN_CAMPAIGN_ID = os.getenv("EPN_CAMPAIGN_ID", "").strip()      # optional for affiliate
EPN_REFERENCE_ID = os.getenv("EPN_REFERENCE_ID", "preisradar").strip()  # optional base

if not CID or not CSEC:
    print("❌ EBAY_CLIENT_ID / EBAY_CLIENT_SECRET fehlen – breche ab.")
    raise SystemExit(1)

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

def get_token(client_id: str, client_secret: str) -> str:
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }
    resp = requests.post(TOKEN_URL, data=data, auth=(client_id, client_secret), timeout=25)
    if resp.status_code != 200:
        print("❌ OAuth-Fehler:", resp.status_code, resp.text[:400])
        raise SystemExit(1)
    tok = resp.json().get("access_token")
    if not tok:
        print("❌ Kein access_token in OAuth-Antwort")
        raise SystemExit(1)
    print("✔ OAuth ok")
    return tok

TOKEN = get_token(CID, CSEC)

def build_headers() -> Dict[str, str]:
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept-Language": "de-DE",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE",
    }
    if EPN_CAMPAIGN_ID:
        h["X-EBAY-C-ENDUSERCTX"] = f"affiliateCampaignId={EPN_CAMPAIGN_ID},affiliateReferenceId={EPN_REFERENCE_ID}"
    return h

HEADERS = build_headers()

# accessory detection – accessories are skipped entirely
EXCLUDE_TERMS = [
  "erweiterung", "expansion", "insert", "organizer", "sleeve", "sleeves",
  "einsatz", "ersatzteil", "ersatzteile", "promo", "upgrade", "coins", "münzen",
  "spielmatte", "playmat", "inlay", "aufbewahrung", "storage", "standee", "minis"
]
def looks_like_accessory(title: str) -> bool:
    t = (title or "").lower()
    return any(term in t for term in EXCLUDE_TERMS)

def search_once(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    filters = [
        "priceCurrency:EUR",
        "conditionIds:{1000}",  # nur Neuware
        "sellerAccountTypes:{BUSINESS}",
    ]
    params = {
        "q": query,
        "limit": str(limit),
        "sort": "price",
        "fieldgroups": "EXTENDED",
        "filter": ",".join(filters),
    }
    r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=25)
    if r.status_code != 200:
        print(f"  ⚠ Suche '{query}' fehlgeschlagen:", r.status_code, r.text[:300])
        return []
    items = r.json().get("itemSummaries") or []
    return items

def pick_price_eur(item) -> float | None:
    # 1) Fixpreis
    price = item.get("price")
    if isinstance(price, dict) and price.get("currency") == "EUR":
        try:
            return float(price.get("value"))
        except (TypeError, ValueError):
            pass
    # 2) Preisrange (min)
    pr = item.get("priceRange")
    if isinstance(pr, dict):
        minp = pr.get("min")
        if isinstance(minp, dict) and minp.get("currency") == "EUR":
            try:
                return float(minp.get("value"))
            except (TypeError, ValueError):
                pass
    # 3) Auktionen
    bid = item.get("currentBidPrice")
    if isinstance(bid, dict) and bid.get("currency") == "EUR":
        try:
            return float(bid.get("value"))
        except (TypeError, ValueError):
            pass
    return None

def pick_shipping_eur(item) -> float:
    """Extract shipping cost in EUR from an item summary."""
    opts = item.get("shippingOptions") or []
    for opt in opts:
        cost = opt.get("shippingCost")
        if isinstance(cost, dict) and cost.get("currency") == "EUR":
            try:
                return float(cost.get("value"))
            except (TypeError, ValueError):
                pass
    return 0.0

def build_url(item, slug: str) -> str:
    url = item.get("itemAffiliateWebUrl") or item.get("itemWebUrl") or ""
    if EPN_CAMPAIGN_ID and url and "campid=" not in url:
        sep = "&" if "?" in url else "?"
        url += f"{sep}campid={EPN_CAMPAIGN_ID}&customid={EPN_REFERENCE_ID}-{slug}"
    return url

def queries_for(game: Dict[str, Any]) -> List[str]:
    title = (game.get("title") or "").strip()
    slug  = (game.get("slug") or "").strip()
    q = []
    terms = game.get("search_terms")
    if isinstance(terms, list):
        q.extend([s for s in terms if isinstance(s, str) and s.strip()])
    if title:
        q += [f"{title} Brettspiel", f"{title} Spiel"]
    if slug:
        q.append(f"{slug.replace('-', ' ')} Brettspiel")
    seen, out = set(), []
    for s in q:
        s2 = s.strip()
        if s2 and s2.lower() not in seen:
            seen.add(s2.lower())
            out.append(s2)
    return out[:6]

def fetch_for_game(game: Dict[str, Any], max_keep: int = 1) -> List[Dict[str, Any]]:
    slug = game.get("slug")
    if not slug:
        return []
    offers = []
    seen = set()
    for q in queries_for(game):
        items = search_once(q, limit=50)
        for it in items:
            iid = it.get("itemId")
            if not iid or iid in seen:
                continue

            price = pick_price_eur(it)
            if price is None:
                continue
            shipping = pick_shipping_eur(it)
            total = price + shipping if price is not None else None

            url = build_url(it, slug)
            if not url:
                continue

            title = (it.get("title") or "").strip()
            if looks_like_accessory(title):
                continue

            # Zusätzliche Sicherungs-Filter (sollten vom API-Filter bereits greiffen)
            cond_id = str(it.get("conditionId") or "")
            cond_txt = (it.get("condition") or "").lower()
            if cond_id and cond_id not in {"1000", "1500", "1750"} and "neu" not in cond_txt and "new" not in cond_txt:
                continue
            seller = it.get("seller") or {}
            acc_type = (seller.get("accountType") or seller.get("sellerAccountType") or "").upper()
            if acc_type != "BUSINESS":
                continue
            shop = seller.get("username") or "eBay"

            img = (it.get("image") or {}).get("imageUrl")

            offers.append({
                "id": iid,
                "title": title[:140],
                "price_eur": round(price, 2),
                "shipping_eur": round(shipping, 2),
                "total_eur": round(total, 2) if total is not None else None,
                "condition": it.get("condition"),
                "url": url,
                "image_url": img,
                "shop": shop,
            })
            seen.add(iid)
            if len(offers) >= max_keep:
                break
        if len(offers) >= max_keep:
            break
    offers.sort(key=lambda x: (x.get("total_eur") if x.get("total_eur") is not None else 1e9))
    return offers

def load_games() -> List[Dict[str, Any]]:
    games = []
    for yml in sorted(CONTENT_DIR.glob("*.yaml")):
        with yml.open("r", encoding="utf-8") as f:
            g = yaml.safe_load(f) or {}
            if isinstance(g, dict) and g.get("slug"):
                games.append(g)
    return games

def main():
    games = load_games()
    if not games:
        print("⚠ Keine Spiele gefunden unter", CONTENT_DIR)
    if not EPN_CAMPAIGN_ID:
        print("⚠ EPN_CAMPAIGN_ID fehlt – Affiliate-Tracking wird (noch) nicht angehängt.")
    updated = 0
    for g in games:
        slug = g["slug"]
        offers = fetch_for_game(g, max_keep=1)
        outp = DATA_DIR / f"{slug}.json"
        outp.parent.mkdir(parents=True, exist_ok=True)
        with outp.open("w", encoding="utf-8") as f:
            json.dump(offers, f, ensure_ascii=False, indent=2)
        print(f"✔ {slug}: {len(offers)} Angebote gespeichert.")
        updated += 1
        time.sleep(0.2)  # freundlich zur API
    print(f"Fertig. {updated} Spiele aktualisiert.")

if __name__ == "__main__":
    main()
