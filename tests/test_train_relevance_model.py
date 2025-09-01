import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import train_relevance_model


def test_load_dataset_skips_non_dict(tmp_path, monkeypatch):
    offers_dir = tmp_path / "data" / "offers"
    labels_dir = tmp_path / "data" / "labels"
    offers_dir.mkdir(parents=True)
    labels_dir.mkdir(parents=True)

    slug = "game"
    (offers_dir / f"{slug}.json").write_text(
        json.dumps(["oops", {"itemId": "1", "title": "foo"}]), "utf-8"
    )
    (labels_dir / f"{slug}.json").write_text(json.dumps({"1": True}), "utf-8")

    monkeypatch.setattr(train_relevance_model, "OFFERS_DIR", offers_dir)
    monkeypatch.setattr(train_relevance_model, "LABEL_DIR", labels_dir)

    texts, labels = train_relevance_model.load_dataset()
    assert len(texts) == 1
    assert labels == [1]
