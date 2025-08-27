"""Train a tiny text classifier to filter irrelevant eBay offers.

The script expects labelled offers in ``data/labels`` generated via
``scripts/label_server.py`` and the corresponding raw offers in
``data/offers``.  A simple ``TfidfVectorizer`` + ``LogisticRegression``
pipeline is used.  The resulting model is saved to
``data/relevance_model.pkl`` and automatically used during ``build.py`` to
filter offers.
"""

from __future__ import annotations

import json
import pathlib

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


ROOT = pathlib.Path(__file__).resolve().parents[1]
OFFERS_DIR = ROOT / "data" / "offers"
LABEL_DIR = ROOT / "data" / "labels"
MODEL_PATH = ROOT / "data" / "relevance_model.pkl"


def load_dataset():
    texts, labels = [], []
    for label_file in LABEL_DIR.glob("*.json"):
        slug = label_file.stem
        offers_file = OFFERS_DIR / f"{slug}.json"
        if not offers_file.exists():
            continue
        offers = json.loads(offers_file.read_text("utf-8"))
        label_map = json.loads(label_file.read_text("utf-8"))
        for offer in offers:
            item_id = str(offer.get("itemId") or offer.get("id") or offer.get("url") or "")
            if not item_id or item_id not in label_map:
                continue
            text = " ".join(
                str(offer.get(k, ""))
                for k in ["title", "subtitle", "condition", "shop", "description"]
            )
            texts.append(text)
            labels.append(1 if label_map[item_id] else 0)
    return texts, labels


def main():
    texts, y = load_dataset()
    if not texts:
        print("No labelled data found")
        return
    vec = TfidfVectorizer(max_features=5000)
    X = vec.fit_transform(texts)
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vec, "model": model}, MODEL_PATH)
    print(f"Saved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()

