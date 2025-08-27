import json, pathlib, yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "games"
DATA = ROOT / "data" / "offers"

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    seller_names = ["demo_shop_a", "demo_shop_b", "demo_shop_c"]
    for yml in CONTENT.glob("*.yaml"):
        game = yaml.safe_load(yml.read_text(encoding="utf-8"))
        slug = game["slug"]; title = game["title"]
        offers = []
        base_price = 50.0
        for i, seller in enumerate(seller_names):
            price = base_price + i * 5
            offers.append({
                "title": f"{title} – neu OVP",
                "price_eur": round(price, 2),
                "shipping_eur": 4.90,
                "total_eur": round(price + 4.90, 2),
                "condition": "New",
                "shop": seller,
                "url": "https://example.com?aff=DEIN_ID",
            })
        (DATA / f"{slug}.json").write_text(
            json.dumps(offers, ensure_ascii=False, indent=2), encoding="utf-8"
        )

if __name__ == "__main__":
    main()
