import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scripts.backfill_rankmath_focus_keywords import STATUSES, derive_keyword, save_and_verify


def test_all_wordpress_post_statuses_are_covered_without_status_writes():
    assert STATUSES == ("publish", "future", "draft", "pending", "private")
    source = (Path(__file__).resolve().parents[1] / "scripts" / "backfill_rankmath_focus_keywords.py").read_text(encoding="utf-8")
    assert 'json={"meta": {"rank_math_focus_keyword": keyword}}' in source
    assert '"status": status' in source


def test_keyword_is_human_readable_and_bounded():
    assert derive_keyword("Find Your Way Through Korea: A Public-Interest Checklist") == "Find Your Way Through Korea"
    assert len(derive_keyword("x" * 200)) == 80


def test_write_is_counted_only_after_verified_readback():
    write = Mock(status_code=200)
    verify = Mock(status_code=200)
    verify.json.return_value = {"meta": {"rank_math_focus_keyword": "Korea support"}}
    with patch("scripts.backfill_rankmath_focus_keywords.requests.post", return_value=write), patch("scripts.backfill_rankmath_focus_keywords.requests.get", return_value=verify):
        assert save_and_verify("https://example.com", "pw", 1, "Korea support") == (True, "")
