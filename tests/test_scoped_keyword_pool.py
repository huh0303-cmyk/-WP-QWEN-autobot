"""Regression: keywords_*.txt lines are 'keyword<TAB>category'.

Incident 2026-11-13..24 (jobkoreaglobal.com): choose_scoped_keyword() returned the raw
line, so the category word was glued onto the keyword ("...quota changes Hiring") and
the first fitting line was chosen on every run, giving four near-identical E-9 posts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from editorial_topic_scope import choose_scoped_keyword

SITE = "https://jobkoreaglobal.com"
OFF_TOPIC = "Seoul K-pop concert"
POOL = [
    "E-8 seasonal worker quota increase\tHiring",
    "Rolling recruitment strategies Korea\tHiring",
    "# comment line",
    "",
]


def test_category_column_is_not_part_of_the_keyword():
    got = choose_scoped_keyword(SITE, OFF_TOPIC, POOL)
    assert "\t" not in got and not got.endswith("Hiring")


def test_pool_choice_is_not_always_the_first_line():
    seen = {choose_scoped_keyword(SITE, OFF_TOPIC, POOL) for _ in range(60)}
    assert len(seen) == 2
