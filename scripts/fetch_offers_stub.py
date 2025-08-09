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
            {"title": f"{title} – wie neu", "price_eur": 47.90, "condition": "Used", "url": "https://example.com?aff=DEIN_ID"},
            {"title": f"{title} – neu OVP", "price_eur": 59.90, "condition": "New", "url": "https://example.com?aff=DEIN_ID"}
        ]
        (DATA / f"{slug}.json").write_text(json.dumps(offers, ensure_ascii=False, indent=2), encoding="utf-8")
if __name__ == "__main__":
    main()
