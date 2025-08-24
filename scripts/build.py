import os, json, pathlib, yaml, datetime as dt, xml.etree.ElementTree as ET, re
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
AMAZON_PARTNER_ID = os.getenv("AMAZON_PARTNER_ID", "28310edf-21").strip()

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES)),
    autoescape=select_autoescape(["html"])
)

def simple_md(text):
    """Convert a tiny subset of Markdown to HTML."""
    if not text:
        return ""
    txt = str(text)
    txt = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", txt)
    txt = re.sub(r"\*(.+?)\*", r"<em>\1</em>", txt)
    paras = [p.strip().replace("\n", " ") for p in re.split(r"\n\s*\n", txt) if p.strip()]
    return "".join(f"<p>{p}</p>" for p in paras)

env.filters["md"] = simple_md

def load_yaml(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_offers(slug):
    """Return (offers, fetched_at) for ``slug``."""
    p = DATA / f"{slug}.json"
    if not p.exists():
        return [], None
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        offers = data.get("offers") or []
        ts = data.get("fetched_at")
        if isinstance(ts, str):
            try:
                ts = dt.datetime.fromisoformat(ts.replace("Z", ""))
            except Exception:
                ts = None
        return offers, ts
    return data, None

def append_history(slug, offers):
    """Append today's minimal price to the history file."""
    prices = []
    for o in offers:
        p = o.get("total_eur") or o.get("price_eur")
        if isinstance(p, (int, float)):
            prices.append(p)
    if not prices:
        return
    min_price = round(min(prices), 2)
    HIST_DIR.mkdir(parents=True, exist_ok=True)
    path = HIST_DIR / f"{slug}.jsonl"
    entry = {"date": dt.date.today().isoformat(), "min": min_price}
    lines = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                x = json.loads(line)
                if x.get("date") != entry["date"]:
                    lines.append(x)
            except Exception:
                pass
    lines.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        for x in lines:
            f.write(json.dumps(x) + "\n")

def build_amazon_search_url(game):
    queries = game.get("search_queries") or game.get("search_terms") or []
    if isinstance(queries, list) and queries:
        q = queries[0]
    else:
        q = game.get("title") or game.get("slug") or ""
    return f"https://www.amazon.de/s?k={quote_plus(q)}&tag={AMAZON_PARTNER_ID}"

def load_history(slug):
    path = HIST_DIR / f"{slug}.jsonl"
    if not path.exists():
        return []
    day_values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            x = json.loads(line)
            day = dt.date.fromisoformat(x["date"])
            val = x.get("min")
            if val is None:
                val = x.get("avg")
            if isinstance(val, (int, float)):
                day_values.setdefault(day, []).append(val)
        except Exception:
            pass
    rows = [
        {"date": day, "min": round(min(vals), 2)}
        for day, vals in sorted(day_values.items())
        if vals
    ]
    return rows

def avg_window(rows, days):
    """Return average over the last ``days`` days (inclusive)."""
    cutoff = dt.date.today() - dt.timedelta(days=days - 1)
    vals = []
    for r in rows:
        v = r.get("min")
        if v is None:
            v = r.get("avg")
        if isinstance(v, (int, float)) and r["date"] >= cutoff:
            vals.append(v)
    if not vals:
        return (None, 0)
    return (round(sum(vals)/len(vals), 2), len(vals))

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

def parse_players(p):
    """Return (min_players, max_players) parsed from a players string."""
    if not p:
        return (None, None)
    p = str(p).replace("–", "-")
    m = re.match(r"(\d+)\s*-\s*(\d+)", p)
    if m:
        return int(m.group(1)), int(m.group(2))
    if str(p).isdigit():
        n = int(p)
        return n, n
    return (None, None)

def render_game(yaml_path, site_url):
    game = load_yaml(yaml_path)

    required_fields = ["players", "playtime", "playtime_minutes", "complexity", "weight", "year"]
    missing_fields = [f for f in required_fields if not game.get(f)]

    offers_raw, fetched_at = load_offers(game["slug"])
    offers = sorted(
        offers_raw,
        key=lambda o: o.get("total_eur") or o.get("price_eur") or 1e9,
    )
    append_history(game["slug"], offers)

    fetched_at_display = None
    if fetched_at:
        try:
            ts = dt.datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            fetched_at_display = ts.strftime("%d.%m.%Y %H:%M")
        except Exception:
            fetched_at_display = fetched_at

    # minimaler Preis für Anzeige
    min_price = None
    if offers:
        first = offers[0]
        min_price = first.get("total_eur") or first.get("price_eur")

    # parse player count for template chip
    min_p, max_p = parse_players(game.get("players"))
    if min_p and max_p:
        game["players"] = {"min": min_p, "max": max_p}
    else:
        game["players"] = None

    # Preisverlauf laden und Fenster berechnen
    hist = load_history(game["slug"])
    avg7, avg_days = avg_window(hist, 7)
    avg30, _ = avg_window(hist, 30)

    cutoff = dt.date.today() - dt.timedelta(days=30)
    hist30 = [
        {"date": r["date"].isoformat(), "min": r["min"]}
        for r in hist
        if isinstance(r.get("min"), (int, float)) and r["min"] > 0 and r["date"] >= cutoff
    ]
    hist_days = len(hist30)

    if min_price is not None:
        today = dt.date.today().isoformat()
        if hist30 and hist30[-1]["date"] == today:
            hist30[-1]["min"] = round(min_price, 2)
        else:
            hist30.append({"date": today, "min": round(min_price, 2)})
        hist_days = len(hist30)

    price_trend = None
    if min_price is not None and avg7:
        try:
            ratio = min_price / avg7
            if ratio <= 0.95:
                price_trend = "good"
            elif ratio <= 1.05:
                price_trend = "ok"
            else:
                price_trend = "high"
        except Exception:
            price_trend = None

    # Affiliate-Suchen
    ebay_search_url = build_epn_search_url(game)
    amazon_search_url = build_amazon_search_url(game)

    page_tpl = env.get_template("page.html.jinja")
    page_html = page_tpl.render(
        game=game,
        offers=offers[:3],
        avg30=avg30,
        avg7=avg7,
        avg_days=avg_days,
        hist_days=hist_days,
        min_price=min_price,
        price_trend=price_trend,
        ebay_search_url=ebay_search_url,
        amazon_search_url=amazon_search_url,
        history=hist30,
        history_json=json.dumps(hist30),
        missing_fields=missing_fields,
        last_checked=fetched_at,
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
