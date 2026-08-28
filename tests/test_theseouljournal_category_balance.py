"""The Seoul Journal category-balancing tests.

pick_best_category() must still only choose a category that's genuinely
relevant to the article (no forced classification), but when more than one
relevant category is a real candidate, it should prefer whichever already
has the fewest posts — only for theseouljournal.com; the other 26 WordPress
sites keep their original single-best-match behavior untouched.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import autopost_mega as am

SITE = "https://theseouljournal.com"
OTHER_SITE = "https://k-health365.com"

# politics / economy / society all score >=3 on a story that mentions all three
# words; society has the fewest live posts, so balancing should pick it.
CATEGORIES = [
    {"id": 19, "name": "Politics", "count": 20},
    {"id": 20, "name": "Economy", "count": 25},
    {"id": 21, "name": "Society", "count": 0},
    {"id": 22, "name": "Culture", "count": 47},
]


def _fake_categories_response(*args, **kwargs):
    resp = Mock()
    resp.status_code = 200
    resp.json.return_value = CATEGORIES if kwargs.get("params", {}).get("page", 1) == 1 else []
    return resp


class FakeGet:
    """requests.get() stand-in shared by load_site_categories and
    _get_category_counts — both hit the same /categories endpoint."""

    def __call__(self, url, **kwargs):
        return _fake_categories_response(url, **kwargs)


def setup_function(_fn):
    am._wp_category_cache.clear()
    am._wp_category_count_cache.clear()


def test_balances_toward_the_least_populated_relevant_category():
    keyword = "politics economy society reform debate"
    with patch("autopost_mega.requests.get", new=FakeGet()):
        chosen_id = am.pick_best_category(SITE, "fake-pass", keyword, title=keyword)
    assert chosen_id == 21  # Society: 0 posts, still a genuine keyword match


def test_single_clear_match_is_never_overridden_by_balancing():
    # Only "Culture" matches at all — balancing must not force it to the
    # emptiest category (Society) just because Society needs more posts.
    keyword = "culture heritage festival tradition"
    with patch("autopost_mega.requests.get", new=FakeGet()):
        chosen_id = am.pick_best_category(SITE, "fake-pass", keyword, title=keyword)
    assert chosen_id == 22  # Culture — the only real match, despite 47 posts


def test_balancing_is_scoped_to_theseouljournal_only():
    keyword = "politics economy society reform debate"
    with patch("autopost_mega.requests.get", new=FakeGet()):
        chosen_id = am.pick_best_category(OTHER_SITE, "fake-pass", keyword, title=keyword)
    # Without balancing, ties/near-ties go to whichever the scoring loop saw
    # first (Politics, id 19) rather than the emptiest (Society, id 21).
    assert chosen_id != 21
