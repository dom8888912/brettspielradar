import base64
import json
import logging
import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts import label_server


def _auth_header(user="u", password="p"):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_training_index_lists_games(tmp_path, monkeypatch):
    offers_dir = tmp_path / "data" / "offers"
    labels_dir = tmp_path / "data" / "labels"
    logs_dir = tmp_path / "data" / "logs"
    for d in (offers_dir, labels_dir, logs_dir):
        d.mkdir(parents=True)

    (offers_dir / "g1.json").write_text(json.dumps([]), "utf-8")
    (offers_dir / "g2.json").write_text(json.dumps([]), "utf-8")

    monkeypatch.setattr(label_server, "OFFERS_DIR", offers_dir)
    monkeypatch.setattr(label_server, "LABEL_DIR", labels_dir)
    monkeypatch.setattr(label_server, "LOG_DIR", logs_dir)
    monkeypatch.setattr(label_server, "LOG_FILE", logs_dir / "log.txt")
    label_server.app.logger.handlers.clear()
    label_server.app.logger.addHandler(logging.NullHandler())
    monkeypatch.setattr(label_server, "USER", "u")
    monkeypatch.setattr(label_server, "PASSWORD", "p")

    client = label_server.app.test_client()
    resp = client.get("/training", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "/spiel/g1/training" in body
    assert "/spiel/g2/training" in body


def test_label_page_handles_searchresult_dict(tmp_path, monkeypatch):
    offers_dir = tmp_path / "data" / "offers"
    labels_dir = tmp_path / "data" / "labels"
    logs_dir = tmp_path / "data" / "logs"
    for d in (offers_dir, labels_dir, logs_dir):
        d.mkdir(parents=True)

    slug = "game"
    offers_file = offers_dir / f"{slug}.json"
    offers_file.write_text(
        json.dumps({"searchResult": {"item": {"0": {"itemId": "1", "url": "u", "title": "t"}}}}),
        "utf-8",
    )

    monkeypatch.setattr(label_server, "OFFERS_DIR", offers_dir)
    monkeypatch.setattr(label_server, "LABEL_DIR", labels_dir)
    monkeypatch.setattr(label_server, "LOG_DIR", logs_dir)
    monkeypatch.setattr(label_server, "LOG_FILE", logs_dir / "log.txt")
    label_server.app.logger.handlers.clear()
    label_server.app.logger.addHandler(logging.NullHandler())
    monkeypatch.setattr(label_server, "USER", "u")
    monkeypatch.setattr(label_server, "PASSWORD", "p")

    client = label_server.app.test_client()
    resp = client.get(f"/spiel/{slug}/training", headers=_auth_header())
    assert resp.status_code == 200
    assert b"Label offers for" in resp.data

def test_label_page_handles_root_dict(tmp_path, monkeypatch):
    offers_dir = tmp_path / "data" / "offers"
    labels_dir = tmp_path / "data" / "labels"
    logs_dir = tmp_path / "data" / "logs"
    for d in (offers_dir, labels_dir, logs_dir):
        d.mkdir(parents=True)

    slug = "game"
    offers_file = offers_dir / f"{slug}.json"
    offers_file.write_text(
        json.dumps({"0": {"itemId": "1", "url": "u", "title": "t"}}),
        "utf-8",
    )

    monkeypatch.setattr(label_server, "OFFERS_DIR", offers_dir)
    monkeypatch.setattr(label_server, "LABEL_DIR", labels_dir)
    monkeypatch.setattr(label_server, "LOG_DIR", logs_dir)
    monkeypatch.setattr(label_server, "LOG_FILE", logs_dir / "log.txt")
    label_server.app.logger.handlers.clear()
    label_server.app.logger.addHandler(logging.NullHandler())
    monkeypatch.setattr(label_server, "USER", "u")
    monkeypatch.setattr(label_server, "PASSWORD", "p")

    client = label_server.app.test_client()
    resp = client.get(f"/spiel/{slug}/training", headers=_auth_header())
    assert resp.status_code == 200
    assert b"Label offers for" in resp.data


def test_label_page_hides_already_labeled(tmp_path, monkeypatch):
    offers_dir = tmp_path / "data" / "offers"
    labels_dir = tmp_path / "data" / "labels"
    logs_dir = tmp_path / "data" / "logs"
    for d in (offers_dir, labels_dir, logs_dir):
        d.mkdir(parents=True)

    slug = "game"
    offers_file = offers_dir / f"{slug}.json"
    offers_file.write_text(
        json.dumps([
            {"itemId": "1", "url": "u1", "title": "t1"},
            {"itemId": "2", "url": "u2", "title": "t2"},
        ]),
        "utf-8",
    )
    label_file = labels_dir / f"{slug}.json"
    label_file.write_text(json.dumps({"1": True}), "utf-8")

    monkeypatch.setattr(label_server, "OFFERS_DIR", offers_dir)
    monkeypatch.setattr(label_server, "LABEL_DIR", labels_dir)
    monkeypatch.setattr(label_server, "LOG_DIR", logs_dir)
    monkeypatch.setattr(label_server, "LOG_FILE", logs_dir / "log.txt")
    label_server.app.logger.handlers.clear()
    label_server.app.logger.addHandler(logging.NullHandler())
    monkeypatch.setattr(label_server, "USER", "u")
    monkeypatch.setattr(label_server, "PASSWORD", "p")

    client = label_server.app.test_client()
    resp = client.get(f"/spiel/{slug}/training", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "u1" not in body
    assert "u2" in body


def test_label_page_hides_negative_labels(tmp_path, monkeypatch):
    offers_dir = tmp_path / "data" / "offers"
    labels_dir = tmp_path / "data" / "labels"
    logs_dir = tmp_path / "data" / "logs"
    for d in (offers_dir, labels_dir, logs_dir):
        d.mkdir(parents=True)

    slug = "game"
    offers_file = offers_dir / f"{slug}.json"
    offers_file.write_text(
        json.dumps([
            {"itemId": "1", "url": "u1", "title": "t1"},
            {"itemId": "2", "url": "u2", "title": "t2"},
        ]),
        "utf-8",
    )
    label_file = labels_dir / f"{slug}.json"
    label_file.write_text(json.dumps({"1": False}), "utf-8")

    monkeypatch.setattr(label_server, "OFFERS_DIR", offers_dir)
    monkeypatch.setattr(label_server, "LABEL_DIR", labels_dir)
    monkeypatch.setattr(label_server, "LOG_DIR", logs_dir)
    monkeypatch.setattr(label_server, "LOG_FILE", logs_dir / "log.txt")
    label_server.app.logger.handlers.clear()
    label_server.app.logger.addHandler(logging.NullHandler())
    monkeypatch.setattr(label_server, "USER", "u")
    monkeypatch.setattr(label_server, "PASSWORD", "p")

    client = label_server.app.test_client()
    resp = client.get(f"/spiel/{slug}/training", headers=_auth_header())
    assert resp.status_code == 200
    body = resp.data.decode()
    assert "u1" not in body
    assert "u2" in body
