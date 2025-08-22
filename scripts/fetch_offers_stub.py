\
import json, pathlib, yaml
ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "games"
DATA = ROOT / "data" / "offers"
def main():
    DATA.mkdir(parents=True, exist_ok=True)
    for yml in CONTENT.glob("*.yaml"):
        game = yaml.safe_load(yml.read_text(encoding="utf-8"))
        slug = game["slug"]; title = game["title"]
        offers = [
            {
                "title": f"{title} – neu OVP",
                "price_eur": 59.90,
                "shipping_eur": 4.90,
                "total_eur": 64.80,
                "condition": "New",
                "shop": "Beispiel-Shop",
                "url": "https://example.com?aff=DEIN_ID",
            }
        ]
        (DATA / f"{slug}.json").write_text(json.dumps(offers, ensure_ascii=False, indent=2), encoding="utf-8")
if __name__ == "__main__":
    main()
