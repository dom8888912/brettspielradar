"""Small Flask server to label eBay offers as relevant or not.

This tool is meant for manual training.  It exposes a single page per game
where the top offers of the last fetch are shown.  Each offer can be labelled
"relevant" or "nicht relevant" and the result is stored in
``data/labels/<slug>.json``.  The page is protected via HTTP basic
authentication; credentials are read from the environment variables
``TRAINING_USER`` and ``TRAINING_PASS`` which should be stored as GitHub
secrets for deployments.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import subprocess
from functools import wraps

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

USER = os.getenv("TRAINING_USER", "")
PASSWORD = os.getenv("TRAINING_PASS", "")


def check_auth(username: str, password: str) -> bool:
    return username == USER and password == PASSWORD


def authenticate():
    return (
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'},
    )


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)

    return decorated


@app.route("/__version__")
def version():
    """Expose the currently running git commit hash."""
    resp = jsonify({"commit": REVISION})
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.route("/spiel/<slug>/training", methods=["GET"])
@requires_auth
def label_page(slug: str):
    offers_file = OFFERS_DIR / f"{slug}.json"
    if not offers_file.exists():
        abort(404)
    try:
        data = json.loads(offers_file.read_text("utf-8"))
        app.logger.info("loaded %s with root type %s", offers_file, type(data).__name__)
        # ``fetch_offers_ebay_enhanced.py`` stores either a plain list of offers
        # or a dictionary with an ``offers`` key.  Older files might still use the
        # eBay API's ``searchResult.item`` structure.  Instead of slicing the raw
        # JSON (which would raise ``KeyError: slice(None, 100, None)`` when the
        # root object is a dictionary) we normalise the structure here and always
        # operate on a list.
        if isinstance(data, dict):
            # Prefer the plain ``offers`` list if present
            offers = data.get("offers")
            if offers is None:
                # Fall back to the eBay API format: {"searchResult": {"item": [...]}}
                offers = data.get("searchResult", {}).get("item")
            if offers is None:
                # Some legacy dumps were a plain dict keyed by numbers
                offers = data
        else:
            offers = data
        # eBay's ``searchResult.item`` or legacy dumps may still be dictionaries
        # keyed by numbers.  Convert them to a list before slicing.
        if isinstance(offers, dict):
            offers = list(offers.values())
        if not isinstance(offers, list):
            offers = []
        offers = offers[:100]
    except Exception:  # pragma: no cover - logging full stack for debugging
        app.logger.exception("failed to load offers for %s", slug)
        abort(500)
    label_file = LABEL_DIR / f"{slug}.json"
    labels: dict[str, bool] = {}
    if label_file.exists():
        labels = json.loads(label_file.read_text("utf-8"))

    def _oid(o: dict) -> str:
        return str(o.get("itemId") or o.get("id") or o.get("url"))

    offers = [o for o in offers if _oid(o) not in labels]
    html = """
<!doctype html>
<title>Label offers – {{ slug }}</title>
<meta name="robots" content="noindex, nofollow">
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
    const div=document.createElement('div');
    const img = o.image_url ? `<img src="${o.image_url}" alt="" style="max-width:150px"><br>` : '';
    const desc = o.description ? `<p>${o.description}</p>` : '';
    div.innerHTML = `${img}<p><a href="${o.url}" target="_blank">${o.title||id}</a> – ${o.total_eur||o.price_eur||''} €</p>${desc}`;
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
@requires_auth
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

