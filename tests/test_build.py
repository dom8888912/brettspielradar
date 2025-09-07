import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.build import is_relevant, build_epn_search_url, DEFAULT_EBAY_CATEGORY_ID


def test_is_relevant_respects_negative_label():
    offer = {"itemId": "1", "title": "foo"}
    labels = {"1": False}
    assert is_relevant(offer, labels) is False


def test_build_epn_search_url_adds_category():
    game = {"slug": "catan", "search_terms": ["Catan"]}
    url = build_epn_search_url(game)
    assert f"_sacat={DEFAULT_EBAY_CATEGORY_ID}" in url
