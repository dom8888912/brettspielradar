import importlib
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock


def load_module():
    os.environ.setdefault("EBAY_CLIENT_ID", "dummy")
    os.environ.setdefault("EBAY_CLIENT_SECRET", "dummy")
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    if "scripts.fetch_offers_ebay_enhanced" in sys.modules:
        del sys.modules["scripts.fetch_offers_ebay_enhanced"]
    with patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"access_token": "tok"}
        return importlib.import_module("scripts.fetch_offers_ebay_enhanced")


def test_queries_for_includes_alt_titles_and_synonyms():
    mod = load_module()
    game = {
        "title": "Catan",
        "slug": "catan",
        "alt_titles": ["Die Siedler von Catan"],
        "synonyms": ["Settlers of Catan"],
    }
    queries = mod.queries_for(game)
    assert "Die Siedler von Catan" in queries
    assert "Settlers of Catan" in queries


def test_search_once_adds_category_filter():
    mod = load_module()
    with patch("scripts.fetch_offers_ebay_enhanced.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp
        mod.search_once("catan", category_id="180349")
        _, kwargs = mock_get.call_args
        assert "filter" in kwargs["params"]
        assert "categoryIds:180349" in kwargs["params"]["filter"]
