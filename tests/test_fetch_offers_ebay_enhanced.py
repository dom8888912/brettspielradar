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


def test_queries_for_uses_explicit_search_terms_only():
    mod = load_module()
    game = {
        "title": "Catan",
        "slug": "catan",
        "search_terms": ["Catan Brettspiel", "Siedler von Catan"],
        "alt_titles": ["ignored"],
    }
    queries = mod.queries_for(game)
    assert queries == ["Catan Brettspiel", "Siedler von Catan"]


def test_search_once_adds_filters():
    mod = load_module()
    # ensure location filter can be injected
    mod.FILTER_CFG["item_location_countries"] = ["DE"]
    with patch("scripts.fetch_offers_ebay_enhanced.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {}
        mock_get.return_value = mock_resp
        mod.search_once(
            "catan",
            category_id="180349",
            min_price=20,
            aspect_filters={"Produktart": ["Eigenständiges Spiel"]},
        )
        _, kwargs = mock_get.call_args
        assert "filter" in kwargs["params"]
        flt = kwargs["params"]["filter"]
        assert "categoryIds:180349" in flt
        assert "price:[20..]" in flt
        assert "buyingOptions:{FIXED_PRICE}" in flt
        assert "itemLocationCountry:{DE}" in flt
        assert kwargs["params"].get("aspect_filter") == "Produktart:Eigenständiges Spiel"


def test_fetch_for_game_returns_business_sellers():
    mod = load_module()
    game = {"slug": "catan", "search_terms": ["Catan"]}
    with patch("scripts.fetch_offers_ebay_enhanced.search_once") as mock_search:
        mock_search.return_value = [
            {
                "itemId": "1",
                "title": "Catan",
                "price": {"currency": "EUR", "value": "10"},
                "conditionId": "1000",
                "seller": {"username": "other", "accountType": "BUSINESS"},
                "itemWebUrl": "http://example.com",
            }
        ]
        offers = mod.fetch_for_game(game)
        assert offers and offers[0]["shop"] == "other"


def test_fetch_for_game_passes_min_price():
    mod = load_module()
    game = {"slug": "catan", "search_terms": ["Catan"], "price_filter": {"min": 5}}
    with patch("scripts.fetch_offers_ebay_enhanced.search_once") as mock_search:
        mock_search.return_value = []
        mod.fetch_for_game(game)
        _, kwargs = mock_search.call_args
        assert kwargs["min_price"] == 5


def test_fetch_for_game_uses_default_category_id():
    mod = load_module()
    mod.DEFAULT_CATEGORY_ID = "99999"
    game = {"slug": "catan", "search_terms": ["Catan"]}
    with patch("scripts.fetch_offers_ebay_enhanced.search_once") as mock_search:
        mock_search.return_value = []
        mod.fetch_for_game(game)
        _, kwargs = mock_search.call_args
        assert kwargs["category_id"] == "99999"


def test_fetch_for_game_filters_wrong_category():
    mod = load_module()
    game = {"slug": "catan", "search_terms": ["Catan"], "ebay_category_id": "180349"}
    with patch("scripts.fetch_offers_ebay_enhanced.search_once") as mock_search:
        mock_search.return_value = [
            {
                "itemId": "1",
                "title": "Catan",
                "categoryId": "123",
                "price": {"currency": "EUR", "value": "10"},
                "conditionId": "1000",
                "seller": {"username": "other", "accountType": "BUSINESS"},
                "itemWebUrl": "http://example.com",
            }
        ]
        offers = mod.fetch_for_game(game)
        assert offers == []

def test_fetch_for_game_passes_aspect_filters():
    mod = load_module()
    game = {
        "slug": "catan",
        "search_terms": ["Catan"],
        "aspect_filters": {"Produktart": ["Eigenständiges Spiel"]},
    }
    with patch("scripts.fetch_offers_ebay_enhanced.search_once") as mock_search:
        mock_search.return_value = []
        mod.fetch_for_game(game)
        _, kwargs = mock_search.call_args
        assert kwargs["aspect_filters"] == {"Produktart": ["Eigenständiges Spiel"]}


def test_fetch_for_game_filters_game_specific_keywords():
    mod = load_module()
    game = {"slug": "catan", "search_terms": ["Catan"], "exclude_keywords": ["seefahrer"]}
    with patch("scripts.fetch_offers_ebay_enhanced.search_once") as mock_search:
        mock_search.return_value = [
            {
                "itemId": "1",
                "title": "Catan Seefahrer Erweiterung",
                "price": {"currency": "EUR", "value": "10"},
                "conditionId": "1000",
                "seller": {"username": "other", "accountType": "BUSINESS"},
                "itemWebUrl": "http://example.com",
            }
        ]
        offers = mod.fetch_for_game(game)
        assert offers == []
