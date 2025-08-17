\
import os, json, statistics, pathlib, yaml, datetime as dt, xml.etree.ElementTree as ET, re
from urllib.parse import quote_plus
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "games"
DATA = ROOT / "data" / "offers"
HIST_DIR = ROOT / "data" / "history"
TEMPLATES = ROOT / "templates"
PUBLIC = ROOT / "public"
DIST = ROOT / "dist"

EPN_CAMPAIGN_ID = os.getenv("EPN_CAMPAIGN_ID", "").strip()
EPN_REFERENCE_ID = os.getenv("EPN_REFERENCE_ID", "preisradar").strip()

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=select_autoescape(["html"])
)

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_offers(slug):
    p = DATA / f"{slug}.json"
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def price_rating(offers, rules):
    prices = [o["price_eur"] for o in offers if "price_eur" in o]
    if not prices:
        return ("keine Daten", 0.0, "teuer")
    avg = statistics.mean(prices)
    if rules:
        good_threshold = rules.get("good_threshold_eur")
        if good_threshold is None:
            good_threshold = 0
        ok_threshold = rules.get("ok_threshold_eur")
        if ok_threshold is None:
            ok_threshold = 9999
        if avg < good_threshold:
            return ("unter", avg, "unter")
        elif avg <= ok_threshold:
            return ("ok", avg, "ok")
        else:
            return ("teuer", avg, "teuer")
    return ("ok", avg, "ok")

def load_history(slug):
    path = HIST_DIR / f"{slug}.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            x = json.loads(line)
            x["date"] = dt.date.fromisoformat(x["date"])
            rows.append(x)
        except Exception:
            pass
    return rows

def avg_window(rows, days):
    cutoff = dt.date.today() - dt.timedelta(days=days)
    vals = [r["avg"] for r in rows if r.get("avg") and r["date"] >= cutoff]
    if not vals:
        return None
    return round(sum(vals)/len(vals), 2)

def build_epn_search_url(game):
    queries = game.get("search_queries") or game.get("search_terms") or []
    if isinstance(queries, list) and queries:
        q = queries[0]
    else:
        q = game.get("slug") or ""
    url = f"https://www.ebay.de/sch/i.html?_nkw={quote_plus(q)}"
    if EPN_CAMPAIGN_ID:
        url += f"&campid={EPN_CAMPAIGN_ID}&customid={EPN_REFERENCE_ID}-{game.get('slug','')}"
    return url

def render_game(yaml_path, site_url):
    game = load_yaml(yaml_path)
    offers = load_offers(game["slug"])
    rating_text, avg_price, _ = price_rating(offers, game.get("price_rules"))
    avg_price_eur = round(avg_price, 2) if avg_price else None

    # history
    hist = load_history(game["slug"])
    avg30 = avg_window(hist, 30)
    avg60 = avg_window(hist, 60)
    avg90 = avg_window(hist, 90)

    # delta vs 60-day average
    delta60 = None
    if avg_price_eur is not None and avg60:
        try:
            delta60 = round(((avg_price_eur - avg60) / avg60) * 100, 1)
        except Exception:
            delta60 = None

    # min price for Top-Deal
    prices = [o["price_eur"] for o in offers if "price_eur" in o]
    min_price = min(prices) if prices else None

    search_url = build_epn_search_url(game)
    page_tpl = env.get_template("page.html.jinja")
    page_html = page_tpl.render(
        game=game,
        offers=offers[:8],
        rating_text=rating_text,
        avg_price_eur=avg_price_eur,
        avg30=avg30, avg60=avg60, avg90=avg90,
        delta60=delta60,
        min_price=min_price,
        ebay_search_url=search_url
    )

    layout_tpl = env.get_template("layout.html.jinja")
    out_html = layout_tpl.render(
        title=f"{game['title']}",
        product_name=game["title"],
        meta_description=f"Preisradar, aktuelle Angebote und Deals für {game['title']}.",
        content=page_html,
        disclosure=game.get("disclosure",""),
        site_url=site_url
    )

    out_dir = DIST / "spiel" / game["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(out_html, encoding="utf-8")

def copy_public():
    if not PUBLIC.exists():
        return
    for p in PUBLIC.rglob("*"):
        if p.is_file():
            target = DIST / p.relative_to(PUBLIC)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(p.read_text(encoding="utf-8"), encoding="utf-8")

def build_game_list(site_url):
    raw_games = [load_yaml(p) for p in CONTENT.glob("*.yaml")]
    games = []
    theme_set = set()

    def parse_players(p):
        if not p:
            return (None, None)
        p = str(p).replace("–", "-")
        m = re.match(r"(\d+)\s*-\s*(\d+)", p)
        if m:
            return int(m.group(1)), int(m.group(2))
        if p.isdigit():
            n = int(p)
            return n, n
        return (None, None)

    def parse_age(a):
        if not a:
            return None
        m = re.search(r"\d+", str(a))
        return int(m.group(0)) if m else None

    for g in raw_games:
        title_short = g["title"].split(" –")[0]
        min_p, max_p = parse_players(g.get("players"))
        age = parse_age(g.get("age"))
        themes = g.get("themes") or []
        if isinstance(themes, str):
            themes = [t.strip() for t in themes.split(",") if t.strip()]
        theme_set.update(themes)
        g.update({
            "title_short": title_short,
            "min_players": min_p,
            "max_players": max_p,
            "age": age,
            "themes": themes,
        })
        games.append(g)

    games = sorted(games, key=lambda g: g["title_short"].lower())
    tpl = env.get_template("games.html.jinja")
    inner = tpl.render(games=games, themes=sorted(theme_set))
    layout_tpl = env.get_template("layout.html.jinja")
    out_html = layout_tpl.render(
        title="Alle Brettspiel-Angebote",
        product_name="Brettspiele",
        meta_description="Aktuelle Angebote & Preisvergleich für Brettspiele.",
        content=inner,
        disclosure="",
        site_url=site_url,
        canonical=f"{site_url}/alle-spiele.html",
    )
    DIST.mkdir(exist_ok=True)
    (DIST / "alle-spiele.html").write_text(out_html, encoding="utf-8")


def build_home(site_url):
    tpl = env.get_template("landing.html.jinja")
    inner = tpl.render()
    layout_tpl = env.get_template("layout.html.jinja")
    out_html = layout_tpl.render(
        title="Brettspiel-Angebote & Preisvergleich",
        product_name="Brettspiele",
        meta_description="Brettspielpreisradar erklärt, wie du günstige Brettspiel-Angebote findest.",
        content=inner,
        disclosure="",
        site_url=site_url,
        canonical=f"{site_url}/",
    )
    DIST.mkdir(exist_ok=True)
    (DIST / "index.html").write_text(out_html, encoding="utf-8")

def build_hubs(site_url):
    cfg = ROOT / "content" / "hubs.yaml"
    if not cfg.exists():
        return
    hubs = load_yaml(cfg).get("hubs", [])
    # simple hubs page
    html = ["<h1>Themen-Hubs</h1><div class='grid two'>"]
    for h in hubs:
        html.append("<div class='card'>")
        html.append(f"<h2>{h.get('title','')}</h2>")
        if h.get("description"):
            html.append(f"<p>{h['description']}</p>")
        html.append("<ul>")
        for s in h.get("slugs", []):
            html.append(f"<li><a href='/spiel/{s}/'>{s}</a></li>")
        html.append("</ul></div>")
    html.append("</div>")
    layout_tpl = env.get_template("layout.html.jinja")
    out_html = layout_tpl.render(
        title="Themen-Hubs",
        product_name="Brettspiele",
        meta_description="Themenübersichten zu Brettspielen.",
        content="".join(html),
        disclosure="",
        site_url=site_url
    )
    (DIST / "hubs.html").write_text(out_html, encoding="utf-8")

def build_sitemap(site_url):
    slugs = [p.stem for p in CONTENT.glob("*.yaml")]
    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    def add(loc):
        u = ET.SubElement(urlset, "url")
        ET.SubElement(u, "loc").text = loc
    add(site_url + "/")
    add(site_url + "/alle-spiele.html")
    add(site_url + "/hubs.html")
    for s in slugs:
        add(f"{site_url}/spiel/{s}/")
    ET.ElementTree(urlset).write(DIST/"sitemap.xml", encoding="utf-8", xml_declaration=True)

def clean_dist():
    if DIST.exists():
        for p in DIST.rglob("*"):
            if p.is_file():
                p.unlink()

def main():
    site_url = os.environ.get("SITE_URL","http://localhost:8000")
    clean_dist()
    DIST.mkdir(parents=True, exist_ok=True)
    copy_public()
    for yml in CONTENT.glob("*.yaml"):
        render_game(yml, site_url)
    build_game_list(site_url)
    build_home(site_url)
    build_hubs(site_url)
    build_sitemap(site_url)

if __name__ == "__main__":
    main()
