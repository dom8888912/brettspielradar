"""Small Flask server to label eBay offers as relevant or not.

This tool is meant for manual training.  It exposes a single page per game
where the top offers of the last fetch are shown.  Each offer can be labelled
"relevant" or "nicht relevant" and the result is stored in
``data/labels/<slug>.json``.
"""

from __future__ import annotations

import json
import logging
import pathlib
import subprocess

from flask import (
    Flask,
    abort,
    jsonify,
    render_template_string,
    request,
    make_response,
)


ROOT = pathlib.Path(__file__).resolve().parents[1]
OFFERS_DIR = ROOT / "data" / "offers"
LABEL_DIR = ROOT / "data" / "labels"
LOG_DIR = ROOT / "data" / "logs"
for d in (LABEL_DIR, LOG_DIR):
    d.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "label_server.log"

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s")
)
app = Flask(__name__)
app.logger.setLevel(logging.INFO)
app.logger.addHandler(file_handler)


def _git_rev() -> str:
    """Return the current git commit hash for troubleshooting."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            check=True,
            text=True,
        )
        return out.stdout.strip()
    except Exception:  # pragma: no cover - best effort only
        return "unknown"


REVISION = _git_rev()
app.logger.info("running commit %s", REVISION)

@app.route("/__version__")
def version():
    """Expose the currently running git commit hash."""
    resp = jsonify({"commit": REVISION})
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


def _load_offers(slug: str) -> list[dict]:
    """Return normalised offers for *slug*."""
    offers_file = OFFERS_DIR / f"{slug}.json"
    if not offers_file.exists():
        return []
    data = json.loads(offers_file.read_text("utf-8"))
    if isinstance(data, dict):
        offers = data.get("offers")
        if offers is None:
            offers = data.get("searchResult", {}).get("item")
        if offers is None:
            offers = data
    else:
        offers = data
    if isinstance(offers, dict):
        offers = list(offers.values())
    if not isinstance(offers, list):
        offers = []
    return offers[:100]


def _offer_id(o: dict) -> str:
    return str(o.get("itemId") or o.get("id") or o.get("url"))


@app.route("/training", methods=["GET"])
def training_index():
    games = []
    for path in sorted(OFFERS_DIR.glob("*.json")):
        slug = path.stem
        offers = _load_offers(slug)
        label_file = LABEL_DIR / f"{slug}.json"
        labels = {}
        if label_file.exists():
            labels = json.loads(label_file.read_text("utf-8"))
        unlabeled = [o for o in offers if _offer_id(o) not in labels]
        games.append({"slug": slug, "count": len(unlabeled)})
    html = """
<!doctype html>
<title>Training Übersicht</title>
<meta name="robots" content="noindex, nofollow">
<style>
body{font-family:sans-serif;}
ul{list-style:none;padding:0;}
li{margin:5px 0;}
</style>
<h1>Training Übersicht</h1>
<ul>
{% for g in games %}
  <li><a href="/spiel/{{ g.slug }}/training">{{ g.slug }}</a> ({{ g.count }})</li>
{% endfor %}
</ul>
"""
    response = make_response(render_template_string(html, games=games))
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.route("/spiel/<slug>/training", methods=["GET"])
def label_page(slug: str):
    offers = _load_offers(slug)
    if not offers:
        abort(404)
    label_file = LABEL_DIR / f"{slug}.json"
    labels: dict[str, bool] = {}
    if label_file.exists():
        labels = json.loads(label_file.read_text("utf-8"))
    offers = [o for o in offers if _offer_id(o) not in labels]
    html = """
<!doctype html>
<title>Label offers – {{ slug }}</title>
<meta name="robots" content="noindex, nofollow">
<style>
body{font-family:sans-serif;}
.offer{border:1px solid #ccc;padding:10px;margin-bottom:10px;}
.offer img{max-width:150px;display:block;margin-bottom:5px;}
.offer button{margin-right:5px;}
</style>
<p><a href="/training">&larr; zurück zur Übersicht</a></p>
<h1>Label offers for {{ slug }}</h1>
<div id="offers"></div>
<script>
const offers = {{ offers | tojson }};
const labels = {{ labels | tojson }};
function sendLabel(id, val){
  fetch('', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({id:id, label:val})});
}
function render(){
  const container=document.getElementById('offers');
  container.innerHTML='';
  offers.forEach(o=>{
    const id=o.itemId || o.id || o.url;
    if (labels[id] !== undefined){
      return; // bereits gelabelt – ausblenden
    }
    const div=document.createElement('div');
    div.className='offer';
    const img = o.image_url ? `<img src="${o.image_url}" alt="">` : '';
    div.innerHTML = `${img}<p><a href="${o.url}" target="_blank">${o.title||id}</a> – ${o.total_eur||o.price_eur||''} €</p>`;
    const descText = o.description || o.subtitle;
    if (descText){
      const p=document.createElement('p');
      p.textContent=descText;
      div.appendChild(p);
    }
    const rel=document.createElement('button');
    rel.textContent='relevant';
    rel.onclick=()=>{labels[id]=true; sendLabel(id,true); render();};
    const nrel=document.createElement('button');
    nrel.textContent='nicht relevant';
    nrel.onclick=()=>{labels[id]=false; sendLabel(id,false); render();};
    div.appendChild(rel); div.appendChild(nrel);
    container.appendChild(div);
  });
}
render();
</script>
"""
    response = make_response(
        render_template_string(html, slug=slug, offers=offers, labels=labels)
    )
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.route("/spiel/<slug>/training", methods=["POST"])
def save_label(slug: str):
    try:
        data = request.get_json(force=True) or {}
        item_id = str(data.get("id"))
        label = bool(data.get("label"))
        label_file = LABEL_DIR / f"{slug}.json"
        labels = {}
        if label_file.exists():
            labels = json.loads(label_file.read_text("utf-8"))
        labels[item_id] = label
        label_file.write_text(
            json.dumps(labels, ensure_ascii=False, indent=2), "utf-8"
        )
        resp = jsonify({"status": "ok"})
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        return resp
    except Exception:  # pragma: no cover - debugging write errors
        app.logger.exception("failed to save label for %s", slug)
        abort(500)


if __name__ == "__main__":
    app.run(port=8000, debug=True)

