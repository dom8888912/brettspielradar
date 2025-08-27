import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from scripts.build import is_relevant


def test_is_relevant_respects_negative_label():
    offer = {"itemId": "1", "title": "foo"}
    labels = {"1": False}
    assert is_relevant(offer, labels) is False
