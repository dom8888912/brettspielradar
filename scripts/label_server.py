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
import os
import pathlib
from functools import wraps

from flask import Flask, abort, jsonify, render_template_string, request, make_response


ROOT = pathlib.Path(__file__).resolve().parents[1]
OFFERS_DIR = ROOT / "data" / "offers"
LABEL_DIR = ROOT / "data" / "labels"
LABEL_DIR.mkdir(parents=True, exist_ok=True)

USER = os.getenv("TRAINING_USER", "")
PASSWORD = os.getenv("TRAINING_PASS", "")

app = Flask(__name__)


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


@app.route("/spiel/<slug>/training", methods=["GET"])
@requires_auth
def label_page(slug: str):
    offers_file = OFFERS_DIR / f"{slug}.json"
    if not offers_file.exists():
        abort(404)
    data = json.loads(offers_file.read_text("utf-8"))
    if isinstance(data, dict):
        offers = data.get("offers", [])
    else:
        offers = data
    offers = offers[:100]
    label_file = LABEL_DIR / f"{slug}.json"
    labels = {}
    if label_file.exists():
        labels = json.loads(label_file.read_text("utf-8"))

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
    div.innerHTML = `<p><a href="${o.url}" target="_blank">${o.title||id}</a>` +
      ` – ${o.total_eur||o.price_eur||''} € – <strong>${labels[id]}</strong></p>`;
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
    data = request.get_json(force=True) or {}
    item_id = str(data.get("id"))
    label = bool(data.get("label"))
    label_file = LABEL_DIR / f"{slug}.json"
    labels = {}
    if label_file.exists():
        labels = json.loads(label_file.read_text("utf-8"))
    labels[item_id] = label
    label_file.write_text(json.dumps(labels, ensure_ascii=False, indent=2), "utf-8")
    resp = jsonify({"status": "ok"})
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


if __name__ == "__main__":
    app.run(port=8000, debug=True)

